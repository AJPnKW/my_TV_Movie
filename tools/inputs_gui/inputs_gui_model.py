# ==============================================================================
# [FILE]    inputs_gui_model.py
# [PROJECT] my_TV_Movie
# [ROLE]    inputs.json load/save + validation (GUI model)
# [VERSION] v0.2.3
# [UPDATED] 2026-02-25T00:00:00Z
#
# [CHANGELOG]
# - v0.2.3: movie seasons display uses em dash for consistency
# - v0.2.2: duplicate-safe item ref indexing for exact-row deletes; season None displays as unset
# - v0.2.1: expose poster index lookup for O(1) GUI poster loading
# - v0.2.0: add stable display helpers (status/poster/seasons), optional data.json enrichment
# - v0.1.0: initial GUI model
# ==============================================================================
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class InputsItem:
    kind: str                 # "tv" | "movie"
    tmdb_id: int
    title: str
    in_scope: bool = True
    seasons: Any = None       # tv only: "all" | [] | [1,2] | {"start":N,"future":bool}
    status: Optional[str] = None
    poster_path: Optional[str] = None

    def seasons_display(self) -> str:
        if self.kind != "tv":
            return "—"
        s = self.seasons
        if s in ("all", "*"):
            return "ALL"
        if s is None:
            return "—"
        if isinstance(s, dict):
            start = int(s.get("start") or s.get("nplus") or 1)
            fut = bool(s.get("future", True))
            return f"{start}+ ({'future' if fut else 'no-future'})"
        if isinstance(s, list):
            if len(s) == 0:
                return "—"
            return ",".join(str(int(x)) for x in s)
        return "ALL"


class InputsModel:
    def __init__(self, repo_root: Path, inputs_path: Path) -> None:
        self.repo_root = repo_root
        self.inputs_path = inputs_path
        self.items: List[InputsItem] = []
        self._items_by_key: Dict[Tuple[str, int], InputsItem] = {}
        self._items_by_ref: Dict[int, InputsItem] = {}
        self._tmdb_enrichment: Dict[Tuple[str, int], Dict[str, Any]] = {}  # (kind, tmdb_id) -> data
        self._poster_index: Dict[Tuple[str, int], str] = {}
        self._poster_by_key: Dict[Tuple[str, int], str] = {}
        self._available_seasons_by_key: Dict[Tuple[str, int], List[int]] = {}
        self._providers_by_key: Dict[Tuple[str, int], List[str]] = {}
        self._networks_by_key: Dict[Tuple[str, int], List[str]] = {}

    # ---------------------------
    # load/save inputs.json
    # ---------------------------
    def load_inputs(self) -> None:
        raw = json.loads(self.inputs_path.read_text(encoding="utf-8"))
        self.items = self._decode(raw)
        self.refresh_enrichment()
        self.reindex_items()

    def save_inputs(self) -> None:
        obj = self._encode(self.items)
        tmp = self.inputs_path.with_suffix(self.inputs_path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.inputs_path)

    # ---------------------------
    # optional enrichment (data.json + local assets)
    # ---------------------------
    def refresh_enrichment(self) -> None:
        self._tmdb_enrichment = self._load_data_json_enrichment()
        self._poster_index = self._build_poster_index()
        self._poster_by_key = {}
        self._available_seasons_by_key = {}
        self._providers_by_key = {}
        self._networks_by_key = {}
        for it in self.items:
            meta = self._tmdb_enrichment.get((it.kind, it.tmdb_id), {})
            it.status = meta.get("status") or it.status
            it.poster_path = self._poster_index.get((it.kind, it.tmdb_id)) or meta.get("poster_path") or it.poster_path
            if it.poster_path:
                self._poster_by_key[self.item_key(it.kind, it.tmdb_id)] = it.poster_path
            av = meta.get("available_seasons")
            if isinstance(av, list):
                self._available_seasons_by_key[self.item_key(it.kind, it.tmdb_id)] = av
            pv = meta.get("providers")
            if isinstance(pv, list):
                self._providers_by_key[self.item_key(it.kind, it.tmdb_id)] = pv
            nw = meta.get("networks")
            if isinstance(nw, list):
                self._networks_by_key[self.item_key(it.kind, it.tmdb_id)] = nw

    @staticmethod
    def item_key(kind: str, tmdb_id: int) -> Tuple[str, int]:
        return (str(kind).strip().lower(), int(tmdb_id))

    def reindex_items(self) -> None:
        self._items_by_key = {self.item_key(it.kind, it.tmdb_id): it for it in self.items}
        self._items_by_ref = {self.item_ref(it): it for it in self.items}

    @staticmethod
    def item_ref(item: InputsItem) -> int:
        return id(item)

    def get_by_key(self, key: Tuple[str, int]) -> Optional[InputsItem]:
        return self._items_by_key.get(self.item_key(key[0], key[1]))

    def get_all_by_key(self, key: Tuple[str, int]) -> List[InputsItem]:
        want = self.item_key(key[0], key[1])
        return [it for it in self.items if self.item_key(it.kind, it.tmdb_id) == want]

    def get_by_ref(self, item_ref: int) -> Optional[InputsItem]:
        return self._items_by_ref.get(int(item_ref))

    def delete_by_keys(self, keys: List[Tuple[str, int]]) -> int:
        normalized = {self.item_key(k[0], k[1]) for k in keys}
        before = len(self.items)
        self.items = [it for it in self.items if self.item_key(it.kind, it.tmdb_id) not in normalized]
        self.items.sort(key=lambda it: (it.kind, it.title.lower(), it.tmdb_id))
        self.reindex_items()
        return before - len(self.items)

    def delete_by_refs(self, item_refs: List[int]) -> int:
        normalized = {int(x) for x in item_refs}
        before = len(self.items)
        self.items = [it for it in self.items if self.item_ref(it) not in normalized]
        self.items.sort(key=lambda it: (it.kind, it.title.lower(), it.tmdb_id))
        self.reindex_items()
        return before - len(self.items)

    def poster_path_for_key(self, key: Tuple[str, int]) -> Optional[str]:
        return self._poster_by_key.get(self.item_key(key[0], key[1]))

    def register_local_poster(self, kind: str, tmdb_id: int, local_path: str) -> None:
        key = self.item_key(kind, tmdb_id)
        self._poster_by_key[key] = local_path
        self._poster_index[key] = local_path
        for it in self.get_all_by_key(key):
            it.poster_path = local_path

    def available_seasons_for_key(self, key: Tuple[str, int]) -> List[int]:
        return list(self._available_seasons_by_key.get(self.item_key(key[0], key[1]), []))

    def providers_for_key(self, key: Tuple[str, int]) -> List[str]:
        return list(self._providers_by_key.get(self.item_key(key[0], key[1]), []))

    def networks_for_key(self, key: Tuple[str, int]) -> List[str]:
        return list(self._networks_by_key.get(self.item_key(key[0], key[1]), []))

    def _load_data_json_enrichment(self) -> Dict[Tuple[str, int], Dict[str, Any]]:
        data_path = self.repo_root / "data" / "data.json"
        if not data_path.exists():
            return {}
        try:
            d = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        out: Dict[Tuple[str, int], Dict[str, Any]] = {}

        # data.json uses "shows" for TV
        for s in d.get("shows", []) or []:
            tid = s.get("tmdb_id")
            if isinstance(tid, int):
                seasons = []
                for se in s.get("seasons", []) or []:
                    sn = se.get("season_number")
                    if isinstance(sn, int):
                        seasons.append(sn)
                providers = []
                for p in s.get("providers", []) or []:
                    name = str(p.get("provider_name") or "").strip()
                    if name:
                        providers.append(name)
                networks = []
                for n in s.get("networks", []) or []:
                    name = str(n.get("name") or "").strip()
                    if name:
                        networks.append(name)
                out[("tv", tid)] = {
                    "status": s.get("status"),
                    "title": s.get("title"),
                    "poster_path": self._resolve_local_asset_path(s.get("poster_local")),
                    "available_seasons": sorted(set(seasons)),
                    "providers": sorted(set(providers)),
                    "networks": sorted(set(networks)),
                }

        for m in d.get("movies", []) or []:
            tid = m.get("tmdb_id")
            if isinstance(tid, int):
                providers = []
                for p in m.get("providers", []) or []:
                    name = str(p.get("provider_name") or "").strip()
                    if name:
                        providers.append(name)
                out[("movie", tid)] = {
                    "status": m.get("status"),
                    "title": m.get("title"),
                    "poster_path": self._resolve_local_asset_path(m.get("poster_local")),
                    "providers": sorted(set(providers)),
                }

        return out

    def _resolve_local_asset_path(self, poster_local: Any) -> Optional[str]:
        raw = str(poster_local or "").strip()
        if not raw:
            return None
        rel = raw[1:] if raw.startswith("/") else raw
        p = (self.repo_root / rel).resolve()
        return str(p) if p.exists() else None

    def _build_poster_index(self) -> Dict[Tuple[str, int], str]:
        assets_dir = self.repo_root / "assets"
        if not assets_dir.exists():
            return {}
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        idx: Dict[Tuple[str, int], str] = {}
        try:
            for p in assets_dir.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in exts:
                    continue
                stem = p.stem
                if not stem.isdigit():
                    continue
                tid = int(stem)
                kind = "tv" if "tv" in str(p).lower() else ("movie" if "movie" in str(p).lower() else "tv")
                key = (kind, tid)
                if key not in idx:
                    idx[key] = str(p)
        except Exception:
            return {}
        return idx

    # ---------------------------
    # normalize JSON schema
    # ---------------------------
    @staticmethod
    def _decode(obj: Dict[str, Any]) -> List[InputsItem]:
        tv: List[InputsItem] = []
        movies: List[InputsItem] = []

        for x in obj.get("tv", []) or []:
            seasons = x.get("seasons")
            if seasons is None and x.get("season_spec") is not None:
                seasons = InputsModel._season_spec_to_seasons(x.get("season_spec"))
            tv.append(
                InputsItem(
                    kind="tv",
                    tmdb_id=int(x.get("tmdb_id")),
                    title=str(x.get("title") or ""),
                    in_scope=bool(x.get("in_scope", True)),
                    seasons=seasons,
                )
            )

        for x in obj.get("movies", []) or []:
            movies.append(
                InputsItem(
                    kind="movie",
                    tmdb_id=int(x.get("tmdb_id")),
                    title=str(x.get("title") or ""),
                    in_scope=bool(x.get("in_scope", True)),
                )
            )

        items = tv + movies
        items.sort(key=lambda it: (it.kind, it.title.lower(), it.tmdb_id))
        return items

    @staticmethod
    def _encode(items: List[InputsItem]) -> Dict[str, Any]:
        tv_list: List[Dict[str, Any]] = []
        mv_list: List[Dict[str, Any]] = []

        for it in items:
            if it.kind == "tv":
                row: Dict[str, Any] = {
                    "tmdb_id": int(it.tmdb_id),
                    "title": it.title,
                    "in_scope": bool(it.in_scope),
                }
                row["season_spec"] = InputsModel._seasons_to_season_spec(it.seasons)
                tv_list.append(row)
            else:
                mv_list.append(
                    {
                        "tmdb_id": int(it.tmdb_id),
                        "title": it.title,
                        "in_scope": bool(it.in_scope),
                    }
                )

        tv_list.sort(key=lambda x: (str(x.get("title") or "").lower(), int(x.get("tmdb_id") or 0)))
        mv_list.sort(key=lambda x: (str(x.get("title") or "").lower(), int(x.get("tmdb_id") or 0)))
        return {"tv": tv_list, "movies": mv_list}

    @staticmethod
    def _season_spec_to_seasons(spec: Any) -> Any:
        s = str(spec or "").strip()
        if not s or s == "*":
            return None
        m = re.fullmatch(r"(\d+)\+", s)
        if m:
            return {"start": int(m.group(1)), "future": True}
        if "," in s:
            vals = [int(p.strip()) for p in s.split(",") if p.strip().isdigit()]
            return vals
        if s.isdigit():
            return [int(s)]
        return None

    @staticmethod
    def _seasons_to_season_spec(seasons: Any) -> str:
        if seasons in (None, "all", "*"):
            return "*"
        if isinstance(seasons, dict):
            start = int(seasons.get("start") or seasons.get("nplus") or 1)
            return f"{start}+"
        if isinstance(seasons, list):
            if not seasons:
                return "*"
            vals = [str(int(x)) for x in seasons]
            return ",".join(vals)
        return "*"
