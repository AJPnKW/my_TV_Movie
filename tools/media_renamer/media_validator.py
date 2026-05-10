# FILE: tools/media_renamer/media_validator.py
# VERSION: v0.4.4
# UPDATED: 2026-05-09
# CHANGE NOTES:
# - Fixed validator false-positive caused by scanning its own rule text.
# - Uses AST import detection instead of raw text matching for forbidden GUI imports.
# - Validates required pipeline files and Python compile status.
from __future__ import annotations

import ast
import json
import py_compile
from pathlib import Path

BANNED_GUI_MODULE = "tkin" + "ter"

REQUIRED_FILES = [
    "tools/media_renamer/media_cleanup_pipeline.py",
    "tools/media_renamer/media_matcher.py",
    "tools/media_renamer/media_validator.py",
    "tools/media_renamer/media_rules.json",
    "scripts/run_media_cleanup_plan.ps1",
    "scripts/apply_media_cleanup_plan.ps1",
    "scripts/validate_media_cleanup_pipeline.ps1",
    "docs/media_renamer/README.html",
]

REPRESENTATIVE_FILENAMES = [
    "Abbott_Elementary_Safety_Day_S05E15.mp4",
    "CIA_(2026)_(2026)_S01E010.mp4",
    "Hacks__5x04.mp4",
    "Come_Dine_with_Me_(S2026E01).mp4",
    "The_Devil_Wears_Prada_2.mp4",
    "vsembed.ru_embed_tv_126027_5_16.mp4",
    "The_Hunting_Party_(S02E10.mp4",
    "Watson_(S02E20).a.mp4",
]


def _repo_file(repo_root: Path, relative_path: str) -> Path:
    return repo_root / Path(relative_path)


def _compile_python(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)


def _has_forbidden_gui_import(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        raise
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0].lower() == BANNED_GUI_MODULE:
                    return True
        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0].lower()
            if module == BANNED_GUI_MODULE:
                return True
    return False


def _validate_rules(repo_root: Path) -> None:
    rules_path = _repo_file(repo_root, "tools/media_renamer/media_rules.json")
    with rules_path.open("r", encoding="utf-8") as handle:
        rules = json.load(handle)
    forbidden = {str(item).lower() for item in rules.get("forbidden_output_folders", [])}
    if "shows" not in forbidden:
        raise AssertionError("media_rules.json must forbid Shows as an output folder")


def _validate_parser(repo_root: Path) -> None:
    import sys

    sys.path.insert(0, str(repo_root))
    from tools.media_renamer.media_cleanup_pipeline import parse_episode_identity

    failures: list[str] = []
    for filename in REPRESENTATIVE_FILENAMES:
        if filename == "The_Devil_Wears_Prada_2.mp4":
            continue
        _tmdb_id, season, episode = parse_episode_identity(Path(filename))
        if season is None or episode is None:
            failures.append(filename)
    if failures:
        raise AssertionError("episode parser failed for: " + ", ".join(failures))


def validate_repo(repo_root: Path) -> None:
    missing = [item for item in REQUIRED_FILES if not _repo_file(repo_root, item).exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))

    for py_file in sorted((repo_root / "tools" / "media_renamer").glob("*.py")):
        _compile_python(py_file)
        if _has_forbidden_gui_import(py_file):
            raise AssertionError(f"Forbidden GUI import found: {py_file}")

    _compile_python(repo_root / "scripts" / "validate_media_renamer.py")
    _validate_rules(repo_root)
    _validate_parser(repo_root)


def main() -> int:
    validate_repo(Path.cwd())
    print("media cleanup pipeline validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
