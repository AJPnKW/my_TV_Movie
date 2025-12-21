import json
import os
from collections import defaultdict

# === CONFIG ===
INPUT_FILE = r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\data\archived\data__data.json.txt"
OUTPUT_FILE = r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\data\archived\schema_report.txt"

# === HELPERS ===

def detect_type(value):
    """Return a normalized type name."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def walk_schema(obj, path="", schema=None, counts=None):
    """Recursively walk the JSON and build a schema."""
    if schema is None:
        schema = {}
    if counts is None:
        counts = defaultdict(int)

    t = detect_type(obj)
    counts[path] += 1

    if path not in schema:
        schema[path] = set()
    schema[path].add(t)

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            walk_schema(v, new_path, schema, counts)

    elif isinstance(obj, list):
        if len(obj) == 0:
            schema[path].add("list(empty)")
        else:
            for i, item in enumerate(obj):
                new_path = f"{path}[*]"
                walk_schema(item, new_path, schema, counts)

    return schema, counts


def format_schema(schema, counts):
    """Format schema into readable text."""
    lines = []
    lines.append("=== FULL DATA SCHEMA ===\n")

    for field in sorted(schema.keys()):
        types = ", ".join(sorted(schema[field]))
        lines.append(f"{field}: {types}")

    lines.append("\n=== FIELD OCCURRENCE COUNTS ===\n")
    for field in sorted(counts.keys()):
        lines.append(f"{field}: {counts[field]} occurrences")

    return "\n".join(lines)


# === MAIN ===

def main():
    print("Loading JSON...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Extracting schema...")
    schema, counts = walk_schema(data)

    print("Formatting output...")
    report = format_schema(schema, counts)

    print(f"Writing schema to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print("Done. Schema extracted successfully.")


if __name__ == "__main__":
    main()
