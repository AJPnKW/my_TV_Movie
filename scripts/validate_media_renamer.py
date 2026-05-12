from __future__ import annotations

import ast
import json
import py_compile
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REQUIRED = [
    "tools/media_renamer/media_cleanup_pipeline.py",
    "tools/media_renamer/media_catalog_builder.py",
    "tools/media_renamer/media_matcher.py",
    "tools/media_renamer/media_validator.py",
    "tools/media_renamer/media_cleanup_launcher.py",
    "tools/media_renamer/requirements.txt",
    "tools/media_renamer/media_rules.json",
    "docs/media_renamer/README.html",
    "docs/media_renamer/implementation_record.html",
    "scripts/run_media_cleanup_plan.ps1",
    "scripts/apply_media_cleanup_plan.ps1",
    "scripts/run_media_cleanup_full_cycle.ps1",
]
PYTHON_FILES = [
    "tools/media_renamer/media_cleanup_pipeline.py",
    "tools/media_renamer/media_catalog_builder.py",
    "tools/media_renamer/media_matcher.py",
    "tools/media_renamer/media_validator.py",
    "tools/media_renamer/media_cleanup_launcher.py",
]

def fail(message: str) -> None:
    print(f"VALIDATION FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)

def main() -> int:
    for rel in REQUIRED:
        if not (REPO / rel).exists():
            fail(f"missing required file: {rel}")
    for rel in PYTHON_FILES:
        path = REPO / rel
        text = path.read_text(encoding="utf-8")
        lowered = text.casefold()
        if "tkinter" in lowered:
            fail(f"forbidden GUI dependency text in {rel}")
        if "utcnow(" in text:
            fail(f"deprecated utcnow usage in {rel}")
        tree = ast.parse(text, filename=str(path))
        first_real = next((node for node in tree.body if not isinstance(node, ast.Expr) or not isinstance(getattr(node, 'value', None), ast.Constant)), None)
        if not isinstance(first_real, ast.ImportFrom) or first_real.module != "__future__":
            fail(f"missing top future annotations import in {rel}")
        py_compile.compile(str(path), doraise=True)
    rules = json.loads((REPO / "tools/media_renamer/media_rules.json").read_text(encoding="utf-8"))
    if rules.get("tv_folder_name") != "TV" or rules.get("movie_folder_name") != "Movies":
        fail("TV/Movies folder names are not locked")
    if "Shows" not in rules.get("forbidden_output_folders", []):
        fail("Shows is not forbidden")
    sys.path.insert(0, str(REPO / "tools" / "media_renamer"))
    from media_matcher import parse_name
    tests = {
        "Abbott_Elementary_Safety_Day_S05E15.mp4": (5, 15),
        "CIA_(2026)_(2026)_S01E010.mp4": (1, 10),
        "Hacks__5x04.mp4": (5, 4),
        "Come_Dine_with_Me_(S2026E01).mp4": (2026, 1),
        "vsembed.ru_embed_tv_126027_5_16.mp4": (5, 16),
        "The_Hunting_Party_(S02E10.mp4": (2, 10),
        "Watson_(S02E20).a.mp4": (2, 20),
    }
    for name, expected in tests.items():
        parsed = parse_name(Path(name))
        actual = (parsed.season, parsed.episode)
        if actual != expected:
            fail(f"parse test failed for {name}: {actual} != {expected}")
    print("media cleanup pipeline validation passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
