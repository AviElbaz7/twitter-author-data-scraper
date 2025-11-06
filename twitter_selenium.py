"""
Twitter profile scraper using Selenium (free alternative to Scrapfly).
"""

import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger as log

# ---------------------------------
# Browser setup
# ---------------------------------
def _init_driver():
    """Create and return a headless Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")       # fully headless
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--lang=en-US,en")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


# ---------------------------------
# Scrape logic
# ---------------------------------
def scrape_profile(username: str) -> dict:
    """
    Scrape a public Twitter profile using Selenium.
    Returns a dict with basic user info.
    """
    url = f"https://twitter.com/{username}"
    retries = 3
    for attempt in range(retries):
        try:
            driver = _init_driver()
            driver.get(url)

            # wait for profile name or failure message
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='UserName']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='emptyState']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='error-detail']"))
                    )
                )
            except Exception:
                log.warning(f"⚠️ Timeout waiting for profile: {username}")
                driver.quit()
                continue

            # check if account unavailable
            if "account suspended" in driver.page_source.lower() or "doesn’t exist" in driver.page_source.lower():
                log.warning(f"⚠️ Account unavailable or suspended: {username}")
                driver.quit()
                return {"user_name": username, "name": "", "bio": "", "location": "",
                        "followers": "", "following": "", "verified": False, "posts": "", "url": url}

            # --- Extract fields ---
            name_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='UserName'] span")
            bio_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='UserDescription'] span")
            loc_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='UserLocation'] span")
            follower_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='followerCount']")
            following_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='followingCount']")
            verified_el = driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Verified account']")

            profile = {
                "user_name": username,
                "name": name_el[0].text if name_el else "",
                "bio": bio_el[0].text if bio_el else "",
                "location": loc_el[0].text if loc_el else "",
                "followers": follower_el[0].text if follower_el else "",
                "following": following_el[0].text if following_el else "",
                "verified": bool(verified_el),
                "posts": "",  # optional: could be parsed if needed
                "url": url,
            }

            # Random short wait to look human
            time.sleep(random.uniform(1.0, 2.5))
            driver.quit()
            log.info(f"✅ Scraped {username} | {profile['location']}")
            return profile

        except Exception as e:
            log.error(f"❌ Error scraping {username} (attempt {attempt+1}/{retries}): {e}")
            try:
                driver.quit()
            except Exception:
                pass
            time.sleep(random.uniform(1.5, 3.0))

    # failed after retries
    log.warning(f"⚠️ Skipping {username} after {retries} attempts.")
    return {"user_name": username, "name": "", "bio": "", "location": "",
            "followers": "", "following": "", "verified": False, "posts": "", "url": url}
