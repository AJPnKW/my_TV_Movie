import json
from collections import OrderedDict

INPUT = "data/inputs.json"
OUTPUT = "data/inputs.cleaned.json"

def normalize_title(title):
    fixes = {
        "The Hundintg Party": "The Hunting Party",
        "The-inspector-lynley-mysteries": "The Inspector Lynley Mysteries",
        "Abbot Elementary": "Abbott Elementary"
    }
    return fixes.get(title, title)

def dedupe(items):
    seen = {}
    for item in items:
        tmdb = item.get("tmdb_id")
        title = normalize_title(item.get("title", ""))

        if not tmdb:
            continue

        key = tmdb

        # normalize
        item["title"] = title

        if key not in seen:
            seen[key] = item
        else:
            # merge logic (keep richer entry)
            existing = seen[key]
            if len(item.keys()) > len(existing.keys()):
                seen[key] = item

    return list(seen.values())

def clean_section(section):
    cleaned = dedupe(section)

    for item in cleaned:
        if "tags" not in item:
            item["tags"] = []

    return cleaned

def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["tv"] = clean_section(data.get("tv", []))
    data["movies"] = clean_section(data.get("movies", []))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Cleaned file written to {OUTPUT}")

if __name__ == "__main__":
    main()
