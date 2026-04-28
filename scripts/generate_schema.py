import argparse
import json
import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "generate_schema.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.debug("=== Script started ===")
logging.debug(f"Log file: {LOG_FILE}")
logging.debug(f"Current directory: {Path.cwd()}")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
OUTPUT_FILE = REPO_ROOT / "schema.json"


def merge_types(values):
    merged = []
    for value in values:
        if value not in merged:
            merged.append(value)
    if len(merged) == 1:
        return merged[0]
    return merged


def infer_schema(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        item_schemas = [infer_schema(item) for item in value]
        return {
            "type": "array",
            "items": merge_schema_list(item_schemas) if item_schemas else {},
        }
    if isinstance(value, dict):
        properties = {str(key): infer_schema(item) for key, item in sorted(value.items())}
        return {
            "type": "object",
            "properties": properties,
            "required": sorted(str(key) for key in value.keys()),
        }
    return {"type": type(value).__name__}


def merge_schema_list(schemas):
    if not schemas:
        return {}
    if len(schemas) == 1:
        return schemas[0]
    types = []
    object_props = {}
    required_sets = []
    array_items = []
    for schema in schemas:
        schema_type = schema.get("type")
        types.append(schema_type)
        if schema_type == "object":
            required_sets.append(set(schema.get("required", [])))
            for key, prop_schema in schema.get("properties", {}).items():
                object_props.setdefault(key, []).append(prop_schema)
        elif schema_type == "array" and schema.get("items"):
            array_items.append(schema["items"])
    merged = {"type": merge_types(types)}
    if object_props:
        merged["properties"] = {
            key: merge_schema_list(prop_schemas)
            for key, prop_schemas in sorted(object_props.items())
        }
        if required_sets:
            merged["required"] = sorted(set.intersection(*required_sets))
    if array_items:
        merged["items"] = merge_schema_list(array_items)
    return merged


def main():
    parser = argparse.ArgumentParser(description="Generate schema.json from data/data.json.")
    parser.add_argument("--pause", action="store_true", help="Pause for Enter before exiting.")
    args = parser.parse_args()

    input_file = DATA_DIR / "data.json"
    logging.debug(f"Data directory: {DATA_DIR}")
    logging.debug(f"Input file: {input_file}")
    logging.debug(f"Output file: {OUTPUT_FILE}")

    if not input_file.exists():
        raise FileNotFoundError(f"data.json not found at {input_file}")

    logging.info("Loading data.json...")
    with input_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "my_TV_Movie data.json inferred schema",
        **infer_schema(data),
    }

    logging.info("Writing schema.json...")
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")

    logging.info(f"Schema saved to: {OUTPUT_FILE}")
    print(f"Schema saved to: {OUTPUT_FILE}")

    if args.pause:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(f"Script crashed: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    finally:
        logging.debug("=== Script ended ===")
