#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script Name : download_service_logos.py
Version     : 3.1.0
Purpose     :
    Use tv-logo/tv-logos mosaic index files to deterministically map your
    curated channel list to actual logo image URLs, download them, and
    save normalized assets for the my_TV_Movie project.

Key fix vs 3.0.0:
    - Correctly parses reference-style entries in 0_all_logos_mosaic.md:
        [cbc]:cbc-ca.png
        [ctv]:ctv-ca.png
      instead of only inline image syntax.

Workflow:
    1. Fetch mosaic markdown for:
         - US, CA, UK, AU (0_all_logos_mosaic.md)
    2. Parse:
         - Inline images:      ![Alt](path.png)
         - Reference-style:    [key]:path.png
    3. Build lookup:
         normalize(name) -> {display_name, url, filename}
    4. For each TARGET_CHANNELS entry:
         - Match by normalized label.
         - If found: download & save PNG+SVG wrapper.
         - If not: mark NOT_FOUND_IN_MOSAIC.

Outputs:
    - image/services_logos/<service_id>.png
    - image/services_logos/<service_id>.svg
    - reports/service_logo_report_YYYYMMDD_HHMMSS.csv
"""

import os
import sys
import re
import csv
import logging
from datetime import datetime
from pathlib import Path
from io import BytesIO

import requests
from PIL import Image

# ===== CONFIG ==============================================================

BASE_DIR = Path(r"C:\Users\Lenovo\Documents\Projects\my_TV_Movie\my_TV_Movie")

LOGO_DIR = BASE_DIR / "image" / "services_logos"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

TARGET_HEIGHT = 96          # px
HTTP_TIMEOUT = 20           # seconds

HTTP_HEADERS = {
    "User-Agent": "my_TV_Movie-logo-fetcher/3.1.0"
}

# Use the exact URLs you provided (refs/heads)
MOSAIC_URLS = [
    "https://raw.githubusercontent.com/tv-logo/tv-logos/refs/heads/main/countries/united-states/0_all_logos_mosaic.md",
    "https://raw.githubusercontent.com/tv-logo/tv-logos/refs/heads/main/countries/canada/0_all_logos_mosaic.md",
    "https://raw.githubusercontent.com/tv-logo/tv-logos/refs/heads/main/countries/united-kingdom/0_all_logos_mosaic.md",
    "https://raw.githubusercontent.com/tv-logo/tv-logos/refs/heads/main/countries/australia/0_all_logos_mosaic.md",
]

# ===== TARGET CHANNELS =====================================================

TARGET_CHANNELS = {
    # US
    "abc": "ABC",
    "cbs": "CBS",
    "nbc": "NBC",
    "fox": "Fox",
    "cw": "CW",
    "pbs": "PBS",
    "ion": "Ion",
    "amc": "AMC",
    "tnt": "TNT",
    "tbs": "TBS",
    "usa": "USA Network",
    "fx": "FX",
    "fxx": "FXX",
    "syfy": "Syfy",
    "bravo": "Bravo",
    "e": "E!",
    "lifetime": "Lifetime",
    "ae": "A&E",
    "discovery": "Discovery Channel",
    "tlc": "TLC",
    "history": "History",
    "food_network": "Food Network",
    "hgtv": "HGTV",
    "animal_planet": "Animal Planet",
    "natgeo": "National Geographic",
    "mtv": "MTV",
    "vh1": "VH1",
    "comedy_central": "Comedy Central",
    "paramount_network": "Paramount Network",
    "disney_channel": "Disney Channel",
    "nickelodeon": "Nickelodeon",
    "cartoon_network": "Cartoon Network",
    "adult_swim": "Adult Swim",
    "trutv": "TruTV",
    "investigation_discovery": "Investigation Discovery",
    "own": "OWN",
    "hallmark": "Hallmark Channel",
    "showtime": "Showtime",
    "hbo": "HBO",
    "starz": "Starz",
    "vice_tv": "VICE TV",

    # Canada
    "cbc": "CBC",
    "ctv": "CTV",
    "global": "Global",
    "citytv": "Citytv",
    "much": "Much",
    "slice": "Slice",
    "showcase_ca": "Showcase",
    "ctv_scifi": "CTV Sci-Fi",
    "outtv": "OutTV",
    "hgtv_ca": "HGTV Canada",
    "discovery_ca": "Discovery Channel Canada",
    "mtv_ca": "MTV Canada",

    # UK
    "bbc": "BBC",
    "itv": "ITV",
    "channel4": "Channel 4",
    "e4": "E4",
    "more4": "More4",
    "film4": "Film4",
    "channel5": "Channel 5",
    "fiveusa": "5USA",
    "fivestar": "5Star",
    "sky": "Sky",
    "sky_scifi": "Sky Sci-Fi",

    # Australia
    "abc_au": "ABC (AU)",
    "nitv": "NITV",
    "seven_au": "7 (AU)",
    "nine_au": "9 (AU)",
    "ten_au": "10 (AU)",
    "sky_news_au": "Sky News Australia",

    # Streaming: still included so they show in CSV;
    # tv-logos mosaics may or may not include them.
    "netflix": "Netflix",
    "prime_video": "Prime Video",
    "disney_plus": "Disney+",
    "hulu": "Hulu",
    "max": "Max",
    "peacock": "Peacock",
    "paramount_plus": "Paramount+",
    "apple_tv_plus": "Apple TV+",
    "crave": "Crave",
    "britbox": "BritBox",
    "dazn": "DAZN",
    "stacktv": "StackTV",
    "now": "NOW",
    "itvx": "ITVX",
    "my5": "My5",
    "uktv_play": "UKTV Play",
    "stan": "Stan",
    "ten_play": "10 Play",
    "nine_now": "9Now",
    "seven_plus": "7plus",
}

# ===== LOGGING =============================================================

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"download_service_logos_{ts}.log"

    logger = logging.getLogger("service_logo_downloader")
    if logger.handlers:
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    logger.info("============================================================")
    logger.info(" my_TV_Movie Service Logo Downloader v3.1.0 (mosaic-based)")
    logger.info("============================================================")
    logger.info(f"Log file : {log_path}")
    logger.info(f"Base dir : {BASE_DIR}")
    logger.info(f"Logo dir : {LOGO_DIR}")
    logger.info("")
    return logger

def ensure_directories(logger: logging.Logger):
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"[OK] Ensured directory exists: {LOGO_DIR}")
    logger.info(f"[OK] Ensured directory exists: {REPORT_DIR}")

# ===== UTILITIES ===========================================================

def normalize_name(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())

def http_get(url: str, logger: logging.Logger) -> str:
    resp = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return resp.text

def http_get_bytes(url: str, logger: logging.Logger) -> bytes:
    resp = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return resp.content

# Patterns:
IMG_INLINE_RE = re.compile(r'!\[(.*?)\]\((.*?)\)')
REF_DEF_RE = re.compile(r'^\s*\[([^\]]+)\]\s*:\s*(\S+)\s*$')

# ===== MOSAIC PARSING ======================================================

def parse_mosaic(url: str, logger: logging.Logger):
    """
    Parse a mosaic markdown file.

    Supports:
      - Inline images:
            ![ABC](abc-us.png)
      - Reference-style defs:
            [cbc]:cbc-ca.png

    Returns:
        dict: norm_name -> {display_name, url, filename}
    """
    logger.info(f"[INFO] Loading mosaic: {url}")
    text = http_get(url, logger)
    base_dir = url.rsplit("/", 1)[0]

    mapping = {}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1) Inline image syntax: ![Alt](src)
        m_img = IMG_INLINE_RE.search(line)
        if m_img:
            alt = m_img.group(1).strip()
            src = m_img.group(2).strip()
            if not src:
                continue
            if src.startswith("http://") or src.startswith("https://"):
                full_url = src
            else:
                src_clean = src.lstrip("./")
                full_url = f"{base_dir}/{src_clean}"
            filename = src.split("/")[-1]
            norm = normalize_name(alt)
            if norm and norm not in mapping:
                mapping[norm] = {
                    "display_name": alt,
                    "url": full_url,
                    "filename": filename,
                }
            continue

        # 2) Reference-style: [key]:path.png
        m_ref = REF_DEF_RE.match(line)
        if m_ref:
            key = m_ref.group(1).strip()
            src = m_ref.group(2).strip()
            if not src:
                continue
            if src.startswith("http://") or src.startswith("https://"):
                full_url = src
            else:
                src_clean = src.lstrip("./")
                full_url = f"{base_dir}/{src_clean}"
            filename = src.split("/")[-1]
            norm = normalize_name(key)
            if norm and norm not in mapping:
                mapping[norm] = {
                    "display_name": key,
                    "url": full_url,
                    "filename": filename,
                }

    logger.info(f"[INFO] Parsed {len(mapping)} logo entries from mosaic.")
    return mapping

def build_global_mosaic_index(logger: logging.Logger):
    combined = {}
    for url in MOSAIC_URLS:
        try:
            m = parse_mosaic(url, logger)
        except Exception as e:
            logger.error(f"[ERROR] Failed to parse mosaic {url}: {e}")
            continue
        for norm, data in m.items():
            # first one wins; that's fine for our mapping
            combined.setdefault(norm, data)
    logger.info(f"[INFO] Global mosaic index size: {len(combined)}")
    return combined

# ===== IMAGE SAVE & WRAPPER ===============================================

def save_png_normalized(content: bytes, service_id: str, logger: logging.Logger):
    img = Image.open(BytesIO(content)).convert("RGBA")
    w, h = img.size
    if h != TARGET_HEIGHT:
        new_w = int(TARGET_HEIGHT * (w / float(h)))
        img = img.resize((new_w, TARGET_HEIGHT), Image.LANCZOS)
    out_path = LOGO_DIR / f"{service_id}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    logger.info(f"[PNG] Saved: {out_path}")
    return out_path

def save_svg_wrapper(service_id: str, png_path: Path, logger: logging.Logger):
    svg_path = LOGO_DIR / f"{service_id}.svg"
    img = Image.open(png_path)
    w, h = img.size
    rel_png = png_path.name
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <image href="{rel_png}" width="{w}" height="{h}"/>
</svg>
"""
    svg_path.write_text(svg, encoding="utf-8")
    logger.info(f"[SVG] Wrapper created: {svg_path}")
    return svg_path

def download_and_save_logo(service_id: str, entry: dict, logger: logging.Logger):
    url = entry["url"]
    filename = entry["filename"]
    ext = filename.split(".")[-1].lower()

    content = http_get_bytes(url, logger)

    # tv-logo repo is PNG; but handle jpg defensively
    if ext in ("png", "jpg", "jpeg"):
        png_path = save_png_normalized(content, service_id, logger)
        svg_path = save_svg_wrapper(service_id, png_path, logger)
        status = "OK" if png_path.exists() and svg_path.exists() else "PARTIAL"
        return status, png_path.name, svg_path.name, str(png_path), str(svg_path)

    # Unexpected type: still try to treat as image
    png_path = save_png_normalized(content, service_id, logger)
    svg_path = save_svg_wrapper(service_id, png_path, logger)
    return "PARTIAL", png_path.name, svg_path.name, str(png_path), str(svg_path)

# ===== MAIN ================================================================

def main():
    logger = setup_logging()
    ensure_directories(logger)

    # Log env vars present, for your sanity
    api_vars = ["API_TMDB_KEY", "API_TVMAZE_KEY", "API_OMDB_KEY"]
    detected = [v for v in api_vars if os.getenv(v)]
    if detected:
        logger.info("[INFO] Detected API env vars (values hidden): " + ", ".join(detected))
    else:
        logger.info("[INFO] No related API keys detected in environment.")

    mosaic_index = build_global_mosaic_index(logger)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"service_logo_report_{ts}.csv"

    total = len(TARGET_CHANNELS)
    ok_count = 0
    partial_count = 0
    miss_count = 0

    logger.info("")
    logger.info("Starting channel logo resolution & download...")
    logger.info("")

    with open(report_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "service_id",
            "channel_name",
            "matched_display_name",
            "source_url",
            "png_file",
            "svg_file",
            "png_path",
            "svg_path",
            "status",
            "timestamp",
        ])

        for service_id, label in TARGET_CHANNELS.items():
            ts_row = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            norm = normalize_name(label)

            logger.info(f"--- {label} ({service_id}) ---")

            entry = mosaic_index.get(norm)
            if not entry:
                logger.warning(f"[MISS] No mosaic match for '{label}' (norm='{norm}')")
                status = "NOT_FOUND_IN_MOSAIC"
                miss_count += 1
                writer.writerow([
                    service_id, label, "", "", "", "", "", "", status, ts_row
                ])
                continue

            try:
                status, png_name, svg_name, png_path, svg_path = download_and_save_logo(
                    service_id, entry, logger
                )
            except Exception as e:
                logger.error(f"[ERROR] Failed to process {label}: {e}")
                status = "ERROR"
                writer.writerow([
                    service_id,
                    label,
                    entry.get("display_name", ""),
                    entry.get("url", ""),
                    "", "", "", "",
                    status,
                    ts_row,
                ])
                continue

            if status == "OK":
                ok_count += 1
            else:
                partial_count += 1

            writer.writerow([
                service_id,
                label,
                entry.get("display_name", ""),
                entry.get("url", ""),
                png_name,
                svg_name,
                png_path,
                svg_path,
                status,
                ts_row,
            ])

    logger.info("")
    logger.info("============================================================")
    logger.info(f"Total targets        : {total}")
    logger.info(f"OK (PNG+SVG)         : {ok_count}")
    logger.info(f"PARTIAL              : {partial_count}")
    logger.info(f"Not found in mosaic  : {miss_count}")
    logger.info(f"Logos directory      : {LOGO_DIR}")
    logger.info(f"Report CSV           : {report_path}")
    logger.info("============================================================")
    logger.info("")

if __name__ == "__main__":
    main()
