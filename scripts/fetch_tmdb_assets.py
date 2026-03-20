
# v2 asset fetch patch
import json, os
print("[START] fetch_tmdb_assets")
data_path = "data/data.json"
if not os.path.exists(data_path):
    print("No data.json found")
    exit()
with open(data_path) as f:
    data = json.load(f)
updated = 0
for item in data.get("items", []):
    if not item.get("poster"):
        item["poster"] = "assets/default_poster.jpg"
        updated += 1
    if not item.get("still"):
        item["still"] = "assets/default_still.jpg"
with open(data_path, "w") as f:
    json.dump(data, f, indent=2)
print(f"[DONE] assets updated: {updated}")
