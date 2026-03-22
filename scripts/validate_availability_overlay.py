#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/validate_availability_overlay.py
# [PROJECT] my_TV_Movie
# [ROLE]    Validate data/watch_source_availability.json against the live catalog.
# [VERSION] v2.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.01
# ==============================================================================

from __future__ import annotations

import argparse
import json
from pathlib import Path

from availability_status_lib import DATA_JSON, SOURCE_JSON, build_catalog_key_index, canonical_source_document, load_json, validate_source_document, write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--source-json", default=str(SOURCE_JSON))
    parser.add_argument("--write-normalized", action="store_true")
    args = parser.parse_args()

    data_path = Path(args.data_json)
    source_path = Path(args.source_json)
    data = load_json(data_path)
    existing = load_json(source_path) if source_path.exists() else {}
    normalized = canonical_source_document(existing)
    known_keys = build_catalog_key_index(data).keys()
    errors = validate_source_document(normalized, known_keys)

    if args.write_normalized:
        write_json_atomic(source_path, normalized)

    summary = {
        "data_json": str(data_path),
        "source_json": str(source_path),
        "record_count": len(normalized.get("records", [])),
        "validation_mode": normalized.get("defaults", {}).get("validation_mode"),
        "network_defaults": normalized.get("defaults", {}).get("network"),
        "errors": errors,
        "result": "OK" if not errors else "FAIL",
    }
    print(json.dumps(summary, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
