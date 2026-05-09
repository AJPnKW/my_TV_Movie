# FILE: scripts/validate_media_renamer.py
# VERSION: v0.4.0
# PURPOSE: Validate media cleanup pipeline code, rules, references, and representative parsing.

from __future__ import annotations

import json
import py_compile
import sys
import warnings
from pathlib import Path


FORBIDDEN_GUI_TOKEN_LOWER = "tk" + "inter"
REQUIRED_FILES = [
    "tools/media_renamer/media_cleanup_pipeline.py",
    "tools/media_renamer/media_catalog_builder.py",
    "tools/media_renamer/media_matcher.py",
    "tools/media_renamer/media_validator.py",
    "tools/media_renamer/media_rules.json",
    "tools/media_renamer/media_cleanup_launcher.py",
    "scripts/run_media_cleanup_plan.ps1",
    "scripts/apply_media_cleanup_plan.ps1",
    "scripts/validate_media_cleanup_pipeline.ps1",
    "docs/media_renamer/README.html",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_required_files(root: Path) -> None:
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
    if missing:
        fail(f"Missing required files: {missing}")


def validate_python_compile(root: Path) -> None:
    warnings.simplefilter("error", DeprecationWarning)
    for rel in REQUIRED_FILES:
        if rel.endswith(".py"):
            py_compile.compile(str(root / rel), doraise=True)


def validate_no_forbidden_gui(root: Path) -> None:
    for path in (root / "tools" / "media_renamer").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        if FORBIDDEN_GUI_TOKEN_LOWER in text:
            fail(f"Forbidden GUI toolkit token found in {path}")


def validate_rules(root: Path) -> None:
    rules = json.loads((root / "tools" / "media_renamer" / "media_rules.json").read_text(encoding="utf-8"))
    if rules.get("final_media_folders") != ["TV", "Movies"]:
        fail("Final folders must be exactly TV and Movies")
    serialized = json.dumps(rules).lower()
    if "shows" in serialized and "forbidden_output_folders" not in rules:
        fail("Rules must not use Shows as output")


def validate_reference_build(root: Path) -> None:
    sys.path.insert(0, str(root))
    from tools.media_renamer.media_catalog_builder import load_or_build_media_reference
    reference = load_or_build_media_reference(root, force=True)
    if not reference.get("shows") and not reference.get("movies"):
        fail("media_reference.json did not build useful data")


def validate_representative_parse(root: Path) -> None:
    sys.path.insert(0, str(root))
    from tools.media_renamer.media_cleanup_pipeline import run_self_test
    run_self_test()


def validate_no_shows_destination(root: Path) -> None:
    text_paths = [
        root / "tools" / "media_renamer" / "media_cleanup_pipeline.py",
        root / "tools" / "media_renamer" / "media_matcher.py",
        root / "tools" / "media_renamer" / "media_rules.json",
    ]
    for path in text_paths:
        text = path.read_text(encoding="utf-8")
        if " / \"Shows\"" in text or "\\Shows" in text:
            fail(f"Forbidden Shows destination reference in {path}")


def main() -> int:
    root = repo_root()
    validate_required_files(root)
    validate_python_compile(root)
    validate_no_forbidden_gui(root)
    validate_rules(root)
    validate_reference_build(root)
    validate_representative_parse(root)
    validate_no_shows_destination(root)
    print("media cleanup pipeline validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
