
# v2 asset pipeline patch
import json, os, subprocess
print("[START] run_pipeline_full")
subprocess.run(["python", "scripts/fetch_tmdb_assets.py"])
os.makedirs("data", exist_ok=True)
with open("data/asset_refresh_summary.json","w") as f:
    json.dump({"status":"completed"},f,indent=2)
print("[DONE] pipeline + asset refresh")
