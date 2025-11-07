"""
Twitter scraping library using Scrapfly.
"""

import json
import os
import asyncio
from typing import Dict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient
from bs4 import BeautifulSoup

# Initialize Scrapfly client
SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,         # Anti Scraping Protection
    "render_js": True,   # Enable JavaScript rendering for Twitter
}


# ---------------- SCRAPE CORE ----------------
async def _scrape_twitter_app(url: str, _retries: int = 0, delay: int = 2, **scrape_config) -> Dict:
    """Internal function to scrape Twitter using Scrapfly with exponential backoff."""
    if _retries > 0:
        log.info(f"Retrying ({_retries}) {url} after {delay}s...")
        await asyncio.sleep(delay)
    else:
        log.info(f"Scraping {url}")

    try:
        result = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                url,
                auto_scroll=True,
                lang=["en-US"],
                **scrape_config,
                **BASE_CONFIG
            )
        )
        if "Something went wrong, but" in result.content:
            raise ValueError("Twitter web app error response")

        return result

    except Exception as e:
        if _retries < 3:
            return await _scrape_twitter_app(url, _retries=_retries + 1, delay=delay * 2, **scrape_config)
        raise e


# ---------------- PARSE HELPERS ----------------
def parse_profile(data: Dict) -> Dict:
    """Parse Twitter profile data from XHR JSON."""
    base = {
        "id": data.get("id"),
        "rest_id": data.get("rest_id"),
        "verified": data.get("is_blue_verified"),
    }
    legacy = data.get("legacy", {})
    if not legacy:
        log.debug("⚠️ No 'legacy' data block found in JSON.")
    return {**base, **legacy}


def parse_html_profile(content: str) -> Dict:
    """Parse visible info (name, bio, location) from HTML when JSON isn't available."""
    soup = BeautifulSoup(content, "html.parser")

    name_tag = soup.select_one("div[data-testid='UserName'] span")
    bio_tag = soup.select_one("div[data-testid='UserDescription'] span")
    loc_tag = soup.select_one("[data-testid='UserLocation'] span")

    profile = {
        "name": name_tag.text.strip() if name_tag else "",
        "bio": bio_tag.text.strip() if bio_tag else "",
        "location": loc_tag.text.strip() if loc_tag else "",
    }

    return profile


# ---------------- MAIN SCRAPER ----------------
async def scrape_profile(url: str) -> Dict:
    """
    Scrape a Twitter profile (XHR + HTML fallback).
    If JSON fails, we still collect visible fields from HTML.
    """
    result = await _scrape_twitter_app(
        url,
        wait_for_selector="[data-testid='UserName'], [data-testid='primaryColumn']"
    )

    profile_data = {}

    # --- 1️⃣ Try to parse XHR JSON data ---
    try:
        user_calls = [
            f for f in result.scrape_result["browser_data"]["xhr_call"]
            if "UserByScreenName" in f["url"] or "UserByRestId" in f["url"]
        ]

        if not user_calls:
            user_calls = [
                f for f in result.scrape_result["browser_data"]["xhr_call"]
                if "UserBy" in f["url"]
            ]

        for xhr in user_calls:
            try:
                data = json.loads(xhr["response"]["body"])
                parsed = parse_profile(data["data"]["user"]["result"])
                profile_data.update(parsed)
                log.debug(f"✅ Extracted JSON data for {url}")
                break
            except Exception as e:
                log.error(f"❌ Failed to parse JSON for {url}: {e}")

    except Exception as e:
        log.warning(f"⚠️ No valid JSON data found for {url}: {e}")

    # --- 2️⃣ Fallback: parse from HTML ---
    try:
        html_profile = parse_html_profile(result.content)
        for k, v in html_profile.items():
            if not profile_data.get(k):  # fill missing only
                profile_data[k] = v
        if html_profile.get("location"):
            log.debug(f"🌍 Extracted location from HTML for {url}: {html_profile['location']}")
    except Exception as e:
        log.warning(f"⚠️ Failed to parse HTML for {url}: {e}")

    # --- 3️⃣ Final check ---
    if not profile_data:
        log.warning(f"⚠️  No valid data extracted for {url}.")

    # Ensure location key always exists
    profile_data.setdefault("location", "")

    return profile_data
