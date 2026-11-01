"""Capture authentic full-page screenshots of all redesigned Streamlit views.

Run after launching `python -m streamlit run dashboard/app.py`.
Requires Playwright and a locally installed Microsoft Edge browser.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "live_data_screenshots"
URL = "http://127.0.0.1:8501"
PAGES = [
    ("Start Here", "01-start-here.png"),
    ("Technology Explorer", "02-technology-explorer.png"),
    ("Technology Rankings", "03-technology-rankings.png"),
    ("Community Health", "04-community-health.png"),
    ("Prediction Explorer", "05-prediction-explorer.png"),
    ("Model Performance & Validation", "06-model-performance.png"),
    ("Methodology & Data", "07-methodology-data.png"),
    ("Live Technology Intelligence", "08-live-technology-intelligence-final-4.png"),
    ("About & User Guide", "09-about-user-guide.png"),
]
PAGE_MARKERS = {
    "Start Here": "What is TechPulse?",
    "Technology Explorer": "Find a technology, then compare its saved model row with observed community activity.",
    "Technology Rankings": "Filter saved technology records and compare the indicators available in this snapshot.",
    "Community Health": "Inspect activity and unanswered-question signals from the observed community file.",
    "Prediction Explorer": "Inspect the saved class, probabilities and input signals for one technology.",
    "Model Performance & Validation": "Compare the metric artifact with the evidence needed to interpret it.",
    "Methodology & Data": "Trace the local source files through labels, model artifacts and SQL analysis.",
    "Live Technology Intelligence": "Inspect timestamped public API observations alongside TechPulse's existing research catalogue.",
    "About & User Guide": "Help for navigating the research prototype and interpreting its saved results.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="replace existing screenshot files")
    parser.add_argument("--page", action="append", choices=[title for title, _ in PAGES], help="capture selected page(s) only")
    args = parser.parse_args()
    selected_pages = [(title, filename) for title, filename in PAGES if not args.page or title in args.page]
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1600}, device_scale_factor=1)
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        page.get_by_text("What is TechPulse?", exact=True).wait_for(timeout=60_000)
        for title, filename in selected_pages:
            if title != "Start Here":
                nav = page.get_by_role("link", name=title, exact=True)
                nav.click(timeout=15_000)
                page.get_by_text(PAGE_MARKERS[title], exact=True).wait_for(timeout=30_000)
            if title == "Technology Explorer":
                search = page.get_by_label("Search technology names")
                search.fill("actionscript")
                page.keyboard.press("Enter")
                page.get_by_text("actionscript", exact=True).wait_for(timeout=10_000)
            target = OUT / filename
            if target.exists() and target.stat().st_size > 0 and not args.overwrite:
                print(f"kept existing {filename}")
                continue
            if title == "Live Technology Intelligence":
                page.set_viewport_size({"width": 1440, "height": 2300})
            page.wait_for_timeout(1800)
            page.screenshot(path=str(target), full_page=True, animations="disabled")
            print(f"captured {filename}")
        browser.close()
    create_contact_sheet()


def create_contact_sheet() -> None:
    """Create a compact contact sheet and index for all nine captured routes."""
    thumbnails = []
    thumb_w, thumb_h, label_h = 360, 400, 34
    for title, filename in PAGES:
        path = OUT / filename
        with Image.open(path).convert("RGB") as source:
            thumbnail = ImageOps.contain(source, (thumb_w, thumb_h))
            tile = Image.new("RGB", (thumb_w, thumb_h + label_h), "#F3EEE7")
            tile.paste(thumbnail, ((thumb_w - thumbnail.width) // 2, 0))
            ImageDraw.Draw(tile).text((10, thumb_h + 8), title, fill="#3A3734")
            thumbnails.append(tile)
    columns = 3
    rows = (len(thumbnails) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), "#E8DFD2")
    for index, tile in enumerate(thumbnails):
        sheet.paste(tile, ((index % columns) * thumb_w, (index // columns) * (thumb_h + label_h)))
    sheet.save(OUT / "contact_sheet_live_data.png")
    lines = ["# TechPulse live-data dashboard screenshots", "", "Captured from the running Streamlit app in Microsoft Edge at 1440 px wide. The Live Technology Intelligence capture is taller to include its chart.", "", "![Nine-page app contact sheet](contact_sheet_live_data.png)", "", "| Page | Screenshot |", "|---|---|"]
    lines.extend(f"| {title} | `{filename}` |" for title, filename in PAGES)
    (OUT / "index_live_data.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
