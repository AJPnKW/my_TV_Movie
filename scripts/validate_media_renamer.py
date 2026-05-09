"""Validate the media renamer source, rules, reference, and parser."""

from __future__ import annotations

import ast
import json
import py_compile
import re
import sys
import warnings
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = REPO_ROOT / "tools" / "media_renamer"
REQUIRED_FILES = [
    TOOL_DIR / "media_renamer_app.py",
    TOOL_DIR / "media_renamer_engine.py",
    TOOL_DIR / "media_catalog_builder.py",
    TOOL_DIR / "media_rules.json",
    TOOL_DIR / "requirements.txt",
    REPO_ROOT / "scripts" / "run_media_renamer.py",
    REPO_ROOT / "docs" / "media_renamer" / "README.html",
]
SOURCE_FILES = [
    TOOL_DIR / "media_renamer_app.py",
    TOOL_DIR / "media_renamer_engine.py",
    TOOL_DIR / "media_catalog_builder.py",
    REPO_ROOT / "scripts" / "run_media_renamer.py",
    REPO_ROOT / "scripts" / "validate_media_renamer.py",
]
DEPRECATED_MARKERS = [
    "datetime." + "utcnow",
    "dist" + "utils",
    "im" + "p.",
    "opt" + "parse",
    "get" + "argspec",
    "collections." + "Mapping",
]


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def validate_import_order(path: Path) -> None:
    tree = ast.parse(read(path), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return
        raise AssertionError(f"Executable statement before imports: {path}:{node.lineno}")


def validate_no_forbidden_gui_word() -> None:
    forbidden = "tk" + "inter"
    for path in SOURCE_FILES + [TOOL_DIR / "media_rules.json"]:
        text = read(path).lower()
        if forbidden in text:
            raise AssertionError(f"Forbidden GUI toolkit reference found in {path}")


def validate_rules() -> None:
    rules = json.loads((TOOL_DIR / "media_rules.json").read_text(encoding="utf-8-sig"))
    tree = rules.get("folder_tree", {})
    if tree.get("tv_root") != "TV" or tree.get("movies_root") != "Movies":
        raise AssertionError("Output roots must be TV and Movies")
    if any(value == "Shows" for value in tree.values()):
        raise AssertionError("Rules must not create a Shows output folder")
    if safe_int(rules.get("minimum_auto_confidence")) != 85:
        raise AssertionError("Safe confidence threshold must be 85")


def safe_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def validate_parser_and_reference() -> None:
    sys.path.insert(0, str(TOOL_DIR))
    from media_catalog_builder import build_media_reference
    from media_renamer_engine import best_catalog_match, parse_episode_identity, title_hint_from_name
    from media_renamer_engine import MediaReference

    reference_path, stats = build_media_reference(REPO_ROOT)
    if not reference_path.exists():
        raise AssertionError("media_reference.json was not built")
    if stats.shows <= 0 or stats.movies <= 0 or stats.episodes <= 0:
        raise AssertionError(f"media_reference.json has weak stats: {stats.as_dict()}")
    payload = json.loads(reference_path.read_text(encoding="utf-8-sig"))
    reference = MediaReference(payload)
    samples = {
        "Abbott_Elementary_Safety_Day_S05E15.mp4": (5, 15, 0),
        "CIA_(2026)_(2026)_S01E010.mp4": (1, 10, 0),
        "Hacks__5x04.mp4": (5, 4, 0),
        "Come_Dine_with_Me_(S2026E01).mp4": (2026, 1, 0),
        "vsembed.ru_embed_tv_126027_5_16.mp4": (5, 16, 126027),
        "The_Hunting_Party_(S02E10.mp4": (2, 10, 0),
        "Watson_(S02E20).a.mp4": (2, 20, 0),
    }
    for name, expected in samples.items():
        actual = parse_episode_identity(name)
        if actual != expected:
            raise AssertionError(f"Parser failed for {name}: expected {expected}, got {actual}")
    if parse_episode_identity("The_Devil_Wears_Prada_2.mp4") != (0, 0, 0):
        raise AssertionError("Movie title number was parsed as an episode")
    movie, score, _ = best_catalog_match([("filename", title_hint_from_name("The_Devil_Wears_Prada_2.mp4"))], reference.movies)
    if not movie or movie.get("title") != "The Devil Wears Prada 2" or score < 85:
        raise AssertionError("Movie matching under-handled The Devil Wears Prada 2")


def main() -> int:
    try:
        missing = [path for path in REQUIRED_FILES if not path.exists()]
        if missing:
            return fail("Missing required files: " + ", ".join(str(path) for path in missing))

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            for path in SOURCE_FILES:
                py_compile.compile(str(path), doraise=True)
                validate_import_order(path)
                print(f"PY OK: {path}")

        validate_no_forbidden_gui_word()
        app_text = read(TOOL_DIR / "media_renamer_app.py")
        if "PySide6" not in app_text:
            return fail("PySide6 is not used by the app")
        if "QTab" + "Widget" in app_text:
            return fail("The old tab workflow is still present")
        if "Fix Safe Changes" not in app_text:
            return fail("Batch safe-fix button is missing")
        requirements = read(TOOL_DIR / "requirements.txt")
        if not re.search(r"^PySide6==6\.10\.3$", requirements, re.MULTILINE):
            return fail("requirements.txt must pin PySide6==6.10.3")
        for path in SOURCE_FILES:
            text = read(path)
            for marker in DEPRECATED_MARKERS:
                if marker in text:
                    return fail(f"Deprecated API marker {marker} found in {path}")

        validate_rules()
        validate_parser_and_reference()
    except Exception as exc:
        return fail(str(exc))

    print("MEDIA RENAMER VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
