"""
Twitter scraping library using Scrapfly.
"""

import json
import os
from typing import Dict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient
from bs4 import BeautifulSoup  # NEW: parse HTML for location

# Initialize Scrapfly client with the API key
SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

# Base configuration for scraping Twitter
BASE_CONFIG = {
    "asp": True,         # Anti Scraping Protection
    "render_js": True,   # Enable JavaScript rendering for Twitter
}


async def _scrape_twitter_app(url: str, _retries: int = 0, **scrape_config) -> Dict:
    """Internal function to scrape Twitter using Scrapfly."""
    if not _retries:
        log.info("Scraping {}", url)
    else:
        log.info("Retrying {}/2 {}", _retries, url)

    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, auto_scroll=True, lang=["en-US"], **scrape_config, **BASE_CONFIG)
    )

    if "Something went wrong, but" in result.content:
        if _retries > 2:
            raise Exception("Twitter web app crashed too many times")
        return await _scrape_twitter_app(url, _retries=_retries + 1, **scrape_config)
    return result


def parse_profile(data: Dict) -> Dict:
    """Parse Twitter profile data from JSON response."""
    base = {
        "id": data.get("id"),
        "rest_id": data.get("rest_id"),
        "verified": data.get("is_blue_verified"),
    }
    legacy = data.get("legacy", {})
    if not legacy:
        log.warning("No legacy data found in profile JSON.")
    return {**base, **legacy}


async def scrape_profile(url: str) -> Dict:
    """
    Scrape a Twitter profile page.
    Combines XHR data (numeric fields) + HTML (for location).
    """
    result = await _scrape_twitter_app(url, wait_for_selector="[data-testid='primaryColumn']")

    # --- Try parsing from JSON XHR calls first ---
    user_calls = [
        f for f in result.scrape_result["browser_data"]["xhr_call"]
        if "UserByScreenName" in f["url"] or "UserByRestId" in f["url"]
    ]

    if not user_calls:
        user_calls = [f for f in result.scrape_result["browser_data"]["xhr_call"] if "UserBy" in f["url"]]

    parsed = {}
    for xhr in user_calls:
        try:
            data = json.loads(xhr["response"]["body"])
            parsed = parse_profile(data["data"]["user"]["result"])
            break
        except Exception as e:
            log.error(f"Failed to parse user data from {xhr.get('url')}: {e}")

    # --- Fallback: parse HTML for location text ---
    try:
        soup = BeautifulSoup(result.content, "html.parser")
        loc_tag = soup.select_one("[data-testid='UserLocation'] span")
        html_location = loc_tag.text.strip() if loc_tag else ""
        if html_location:
            parsed["location"] = html_location
    except Exception as e:
        log.warning(f"Failed to parse location from HTML: {e}")

    return parsed
