from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from media_catalog_builder import MediaReference, MovieRef, ShowRef, clean_title, normalize_key

EP_PATTERNS = [
    re.compile(r"s(?P<s>\d{1,4})\s*e(?P<e>\d{1,3})", re.IGNORECASE),
    re.compile(r"(?P<s>\d{1,2})\s*x\s*(?P<e>\d{1,3})", re.IGNORECASE),
    re.compile(r"s(?P<s>\d{1,4})\s*[_\-. ]\s*e(?P<e>\d{1,3})", re.IGNORECASE),
]
EMBED_PATTERN = re.compile(r"embed[_\-. ]tv[_\-. ](?P<id>\d+)[_\-. ](?P<s>\d+)[_\-. ](?P<e>\d+)", re.IGNORECASE)
NUMERIC_EP_PATTERN = re.compile(r"(?:^|[_\-. ])(?P<code>\d{4})(?:[_\-. ]|$)")

@dataclass(slots=True)
class ParsedName:
    season: int | None
    episode: int | None
    tmdb_id: int | None
    candidate_title: str
    episode_title_hint: str
    embedded_tv: bool = False

@dataclass(slots=True)
class MatchResult:
    kind: str
    tmdb_id: int | None
    title: str
    year: str
    season: int | None
    episode: int | None
    episode_name: str
    confidence: int
    reason: str

def strip_suffix_junk(stem: str) -> str:
    text = stem
    text = re.sub(r"\b(?:720|1080|2160|hd|fullhd|f_)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:[_\-. ]+(?:a|b|tmp|copy|alt\d+|\d+))+$", "", text, flags=re.IGNORECASE)
    return text.strip(" _-.()")

def parse_name(path: Path) -> ParsedName:
    original_raw = path.stem
    raw = strip_suffix_junk(original_raw)
    tmdb_id = None
    bracket = re.search(r"\[(\d{2,})\]", original_raw)
    if bracket:
        tmdb_id = int(bracket.group(1))
    embed = EMBED_PATTERN.search(original_raw)
    if embed:
        return ParsedName(
            season=int(embed.group("s")),
            episode=int(embed.group("e")),
            tmdb_id=int(embed.group("id")),
            candidate_title="",
            episode_title_hint="",
            embedded_tv=True,
        )
    season = None
    episode = None
    match = None
    for pattern in EP_PATTERNS:
        match = pattern.search(raw)
        if match:
            season = int(match.group("s"))
            episode = int(match.group("e"))
            break
    if match is None:
        numeric = NUMERIC_EP_PATTERN.search(raw)
        if numeric:
            code = numeric.group("code")
            season = int(code[:2])
            episode = int(code[2:])
            match = numeric
    before = raw[: match.start()] if match else raw
    after = raw[match.end() :] if match else ""
    before = re.sub(r"\(\d{4}\)", " ", before)
    before = re.sub(r"\[\d+\]", " ", before)
    candidate_title = clean_title(before.replace("_", " ").replace(".", " "))
    episode_hint = clean_title(after.replace("_", " ").replace(".", " ").strip(" -()"))
    return ParsedName(season=season, episode=episode, tmdb_id=tmdb_id, candidate_title=candidate_title, episode_title_hint=episode_hint)

def _folder_tmdb_hint(path: Path) -> int | None:
    for part in reversed(path.parts):
        match = re.search(r"\[(\d{2,})\]", part)
        if match:
            return int(match.group(1))
    return None

def _folder_title_hint(path: Path) -> str:
    parts = list(path.parts)
    for part in reversed(parts):
        if part.lower().startswith("season") or part.startswith("_"):
            continue
        if re.search(r"\[(\d{2,})\]", part):
            return clean_title(re.sub(r"\s*\[\d+\]", "", part))
        if part.lower() in {"tv", "movies", "recordings"}:
            break
        return clean_title(part)
    return ""

def score_title(candidate: str, show: ShowRef | MovieRef) -> int:
    norm = normalize_key(candidate)
    if not norm:
        return 0
    best = 0.0
    for token in show.tokens:
        if not token:
            continue
        if norm == token:
            return 100
        if norm in token or token in norm:
            best = max(best, 0.92)
        best = max(best, SequenceMatcher(None, norm, token).ratio())
    return int(round(best * 100))

def _episode_from_title_hint(show: ShowRef, hint: str) -> tuple[int | None, int | None, str, int]:
    norm = normalize_key(hint)
    if not norm:
        return None, None, "", 0
    best: tuple[int | None, int | None, str, int] = (None, None, "", 0)
    for season in show.seasons.values():
        for ep in season.episodes.values():
            if not ep.normalized_name:
                continue
            score = int(round(SequenceMatcher(None, norm, ep.normalized_name).ratio() * 100))
            if norm in ep.normalized_name or ep.normalized_name in norm:
                score = max(score, 92)
            if score > best[3]:
                best = (season.season_number, ep.episode_number, ep.name, score)
    return best

def match_tv(path: Path, ref: MediaReference) -> MatchResult:
    parsed = parse_name(path)
    folder_tmdb = _folder_tmdb_hint(path.parent)
    folder_title = _folder_title_hint(path.parent)
    chosen: ShowRef | None = None
    reason_parts: list[str] = []
    if parsed.tmdb_id and parsed.tmdb_id in ref.shows:
        chosen = ref.shows[parsed.tmdb_id]
        reason_parts.append("tmdb id in file")
    elif folder_tmdb and folder_tmdb in ref.shows:
        chosen = ref.shows[folder_tmdb]
        reason_parts.append("tmdb id in folder")
    elif parsed.embedded_tv and parsed.tmdb_id in ref.shows:
        chosen = ref.shows[parsed.tmdb_id]
        reason_parts.append("embedded tv id")
    else:
        title_candidates = [parsed.candidate_title, folder_title]
        best_score = 0
        for show in ref.shows.values():
            for title in title_candidates:
                score = score_title(title, show)
                if score > best_score:
                    best_score = score
                    chosen = show
        reason_parts.append(f"title score {best_score}")
    if not chosen:
        return MatchResult("problem", None, "", "", parsed.season, parsed.episode, "", 0, "no show candidate")
    title_conf = max(score_title(parsed.candidate_title, chosen), score_title(folder_title, chosen))
    if parsed.tmdb_id == chosen.tmdb_id or folder_tmdb == chosen.tmdb_id:
        title_conf = max(title_conf, 95)
    season = parsed.season
    episode = parsed.episode
    ep_name = ""
    if season is not None and episode is not None:
        ep_ref = chosen.seasons.get(season)
        if ep_ref and episode in ep_ref.episodes:
            ep_name = ep_ref.episodes[episode].name
            confidence = max(title_conf, 90)
        else:
            ep_name = f"Episode {episode:02d}"
            confidence = min(max(title_conf, 86), 90)
    else:
        s, e, found_name, ep_score = _episode_from_title_hint(chosen, parsed.episode_title_hint or parsed.candidate_title)
        if s is not None and e is not None and ep_score >= 88:
            season = s
            episode = e
            ep_name = found_name
            confidence = min(max(title_conf, ep_score), 92)
            reason_parts.append("episode title match")
        else:
            return MatchResult("problem", chosen.tmdb_id, chosen.title, chosen.year, None, None, "", min(title_conf, 70), "missing season/episode")
    return MatchResult("tv", chosen.tmdb_id, chosen.title, chosen.year, season, episode, ep_name, int(confidence), "; ".join(reason_parts))

def match_movie(path: Path, ref: MediaReference) -> MatchResult:
    stem = clean_title(re.sub(r"\(\d{4}\)", " ", path.stem.replace("_", " ")))
    best: MovieRef | None = None
    best_score = 0
    for movie in ref.movies.values():
        score = score_title(stem, movie)
        if score > best_score:
            best_score = score
            best = movie
    if not best:
        return MatchResult("problem", None, "", "", None, None, "", 0, "no movie candidate")
    return MatchResult("movie", best.tmdb_id, best.title, best.year, None, None, "", best_score, f"movie title score {best_score}")
