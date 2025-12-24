import json
import os
from collections import defaultdict

REPORT_DIR = r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\reports"
os.makedirs(REPORT_DIR, exist_ok=True)
REPORT_FILE = os.path.join(REPORT_DIR, "data_schema_archived_report.txt")

def summarize_schema(obj, prefix=""):
    schema = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            schema[prefix + k] = type(v).__name__
            if isinstance(v, (dict, list)):
                schema.update(summarize_schema(v, prefix + k + "."))
    elif isinstance(obj, list) and obj:
        schema[prefix + "[*]"] = type(obj[0]).__name__
        schema.update(summarize_schema(obj[0], prefix + "[*]."))
    return schema

def find_empty(obj, path="", results=None):
    if results is None:
        results = []
    if obj is None or obj == "" or obj == [] or obj == {}:
        results.append(f"EMPTY: {path}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_empty(v, f"{path}.{k}" if path else k, results)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_empty(v, f"{path}[{i}]", results)
    return results

with open("data/archived/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

lines = []

lines.append("=== TOP LEVEL KEYS ===")
for k in data.keys():
    lines.append(f" - {k}")

lines.append("\n=== SCHEMA SUMMARY ===")
schema = summarize_schema(data)
for k in sorted(schema.keys()):
    lines.append(f"{k}: {schema[k]}")

lines.append("\n=== EMPTY / NULL FIELDS ===")
empty_fields = find_empty(data)
lines.extend(empty_fields)

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Schema report written to:\n{REPORT_FILE}")
