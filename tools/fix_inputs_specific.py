# version: v1.0
# purpose: targeted correction for known bad entries

import json

INPUT = "data/inputs.json"

def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- FIX TV ---
    fixed_tv = []
    for item in data.get("tv", []):
        tmdb = item.get("tmdb_id")

        # remove wrong Abbott Elementary
        if tmdb == 125036:
            continue

        # enforce correct Abbott Elementary
        if tmdb == 125935:
            item["title"] = "Abbott Elementary"

        fixed_tv.append(item)

    # --- FIX MOVIES ---
    fixed_movies = []
    for item in data.get("movies", []):
        tmdb = item.get("tmdb_id")

        # convert wrong Amateur → 57 Seconds
        if tmdb == 937249:
            item["title"] = "57 Seconds"

        # enforce correct Amateur
        if tmdb == 1087891:
            item["title"] = "The Amateur"

        fixed_movies.append(item)

    data["tv"] = fixed_tv
    data["movies"] = fixed_movies

    # --- WRITE BACK ---
    with open(INPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("inputs.json fixed successfully")

if __name__ == "__main__":
    main()
