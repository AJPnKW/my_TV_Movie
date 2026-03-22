#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_availability_ui.py
# [PROJECT] my_TV_Movie
# [ROLE]    Browser-level QA for availability badge visibility and upper-right
#           placement on shared image surfaces.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.02
# ==============================================================================

from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from availability_status_lib import REPO_ROOT, write_json_atomic

REPORT_DIR = REPO_ROOT / "reports" / "availability_status"


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _make_driver() -> webdriver.Edge:
    options = EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Edge(options=options)


def _rect(driver: webdriver.Edge, element) -> Dict[str, float]:
    return driver.execute_script(
        "const r = arguments[0].getBoundingClientRect();"
        "return {left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height};",
        element,
    )


def _badge_in_top_right(driver: webdriver.Edge, surface, badge) -> bool:
    s = _rect(driver, surface)
    b = _rect(driver, badge)
    if s["width"] <= 0 or s["height"] <= 0 or b["width"] <= 0 or b["height"] <= 0:
        return False
    return (
        b["right"] <= s["right"] + 4
        and b["right"] >= s["right"] - max(28, s["width"] * 0.4)
        and b["top"] >= s["top"] - 2
        and b["top"] <= s["top"] + max(60, s["height"] * 0.33)
    )


def _wait_for_badge(driver: webdriver.Edge, badge_selector: str, timeout: int = 30) -> None:
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script(f"return document.readyState === 'complete' && document.querySelectorAll({json.dumps(badge_selector)}).length > 0;"))


def _check_page(driver: webdriver.Edge, url: str, surface_selector: str, badge_selector: str, results: List[Dict[str, Any]], issues: List[str]) -> None:
    driver.get(url)
    _wait_for_badge(driver, badge_selector)
    surfaces = driver.find_elements(By.CSS_SELECTOR, surface_selector)
    badges = driver.find_elements(By.CSS_SELECTOR, badge_selector)
    if not surfaces or not badges:
        issues.append(f"{url} missing surfaces or badges")
        return
    surface = surfaces[0]
    badge = badges[0]
    ok = _badge_in_top_right(driver, surface, badge)
    if not ok:
        issues.append(f"{url} first card badge not in upper-right image corner")
    results.append({"url": url, "selector": surface_selector, "badge_top_right": ok})


def _check_popups(driver: webdriver.Edge, base_url: str, results: List[Dict[str, Any]], issues: List[str]) -> None:
    driver.get(f"{base_url}/movies.html")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-movie-open]")))
    driver.find_elements(By.CSS_SELECTOR, "[data-movie-open]")[0].click()
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".popup-hero__poster .popup-surface-badge .availability-badge")))
    movie_surface = driver.find_element(By.CSS_SELECTOR, ".popup-hero__poster")
    movie_badge = driver.find_element(By.CSS_SELECTOR, ".popup-hero__poster .popup-surface-badge .availability-badge")
    movie_ok = _badge_in_top_right(driver, movie_surface, movie_badge)
    if not movie_ok:
        issues.append("movie popup badge not in upper-right image corner")
    results.append({"url": f"{base_url}/movies.html", "selector": ".popup-hero__poster", "badge_top_right": movie_ok})

    driver.get(f"{base_url}/shows.html")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-show-open]")))
    driver.find_elements(By.CSS_SELECTOR, "[data-show-open]")[0].click()
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".popup-hero__poster .popup-surface-badge .availability-badge")))
    show_surface = driver.find_element(By.CSS_SELECTOR, ".popup-hero__poster")
    show_badge = driver.find_element(By.CSS_SELECTOR, ".popup-hero__poster .popup-surface-badge .availability-badge")
    show_ok = _badge_in_top_right(driver, show_surface, show_badge)
    if not show_ok:
        issues.append("show popup badge not in upper-right image corner")
    results.append({"url": f"{base_url}/shows.html", "selector": ".popup-hero__poster", "badge_top_right": show_ok})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/web")
    parser.add_argument("--report-json", default="")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    issues: List[str] = []
    driver = _make_driver()
    try:
        _check_page(driver, f"{args.base_url}/index.html", ".media-card__poster", ".media-card__surface-badge .availability-badge", results, issues)
        _check_page(driver, f"{args.base_url}/shows.html", ".media-card--show .media-card__poster", ".media-card--show .media-card__surface-badge .availability-badge", results, issues)
        _check_page(driver, f"{args.base_url}/movies.html", ".media-card--movie .media-card__poster", ".media-card--movie .media-card__surface-badge .availability-badge", results, issues)
        _check_page(driver, f"{args.base_url}/calendar.html", ".calendar-item .media-card__poster", ".calendar-item .media-card__surface-badge .availability-badge", results, issues)
        _check_page(driver, f"{args.base_url}/watch_me/watch_me.html", ".media-card__poster", ".media-card__surface-badge .availability-badge", results, issues)
        _check_popups(driver, args.base_url, results, issues)
    except TimeoutException as exc:
        issues.append(f"ui qa timeout: {exc}")
    finally:
        driver.quit()

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "OK" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
        "checks": results,
    }
    report_path = Path(args.report_json) if args.report_json else (REPORT_DIR / f"availability_ui_{_stamp()}.json")
    write_json_atomic(report_path, report)
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
