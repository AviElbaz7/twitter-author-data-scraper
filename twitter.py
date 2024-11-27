"""
Twitter scraping library using Scrapfly.

This module provides methods to scrape Twitter profiles and tweets.

Requirements:
    - Scrapfly API key set as an environment variable: $SCRAPFLY_KEY

To set up:
    $ export SCRAPFLY_KEY="your_key"

More details: https://scrapfly.io/docs
"""

import json
import os
import jmespath

from typing import Dict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

# Initialize Scrapfly client with the API key
SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

# Base configuration for scraping Twitter
BASE_CONFIG = {
    "asp": True,  # Anti Scraping Protection
    "render_js": True,  # Enable JavaScript rendering for Twitter
}


async def _scrape_twitter_app(url: str, _retries: int = 0, **scrape_config) -> Dict:
    """
    Internal function to scrape Twitter using Scrapfly.

    Args:
        url (str): Twitter page URL to scrape.
        _retries (int): Retry counter for failed attempts.

    Returns:
        Dict: Scraped page content or raises an exception on failure.
    """
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
    """
    Parse Twitter profile data from a JSON response.

    Args:
        data (Dict): JSON data of the profile.

    Returns:
        Dict: Simplified profile data structure.
    """
    return {"id": data["id"], "rest_id": data["rest_id"], "verified": data["is_blue_verified"], **data["legacy"]}


async def scrape_profile(url: str) -> Dict:
    """
    Scrape a Twitter profile page.

    Args:
        url (str): URL of the Twitter profile.

    Returns:
        Dict: Profile data or raises an exception on failure.
    """
    result = await _scrape_twitter_app(url, wait_for_selector="[data-testid='primaryColumn']")
    user_calls = [f for f in result.scrape_result["browser_data"]["xhr_call"] if "UserBy" in f["url"]]

    for xhr in user_calls:
        data = json.loads(xhr["response"]["body"])
        parsed = parse_profile(data["data"]["user"]["result"])
        return parsed

    raise Exception("Failed to scrape user profile - no matching user data background requests")
