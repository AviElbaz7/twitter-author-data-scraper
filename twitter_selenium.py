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
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--lang=en-US,en")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(2)  # 👈 small wait for slow elements
    return driver



# ---------------------------------
# Scrape logic
# ---------------------------------
def scrape_profile(username: str) -> dict:
    """
    Scrape a public Twitter profile using Selenium.
    Returns a dict with user info (location fixed and more robust).
    """
    url = f"https://twitter.com/{username}"
    retries = 3
    for attempt in range(retries):
        driver = None
        try:
            driver = _init_driver()
            driver.get(url)

            # Wait until profile header appears
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='UserName']"))
            )

            # Scroll to trigger lazy elements
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(1, 2))

            # --- Extract profile info ---
            name_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='UserName'] span")
            bio_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='UserDescription'] span")
            follower_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='followerCount']")
            following_el = driver.find_elements(By.CSS_SELECTOR, "[data-testid='followingCount']")
            verified_el = driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Verified account']")

            # --- Robust location extraction ---
            location_text = ""
            try:
                # 1️⃣ Look for location icon + sibling text (most consistent)
                loc_icon = driver.find_elements(
                    By.XPATH, "//svg[@aria-label='Location']/ancestor::div[1]//span"
                )
                if loc_icon:
                    # Filter out empty, emoji-only, or "Joined..." values
                    texts = [el.text.strip() for el in loc_icon if el.text.strip()]
                    for t in texts:
                        if t and not t.lower().startswith("joined") and len(t) > 2:
                            location_text = t
                            break

                # 2️⃣ Fallback: header items block (older layout)
                if not location_text:
                    header_items = driver.find_elements(
                        By.XPATH, "//div[@data-testid='UserProfileHeader_Items']//span"
                    )
                    for el in header_items:
                        txt = el.text.strip()
                        if txt and not txt.lower().startswith("joined"):
                            location_text = txt
                            break

            except Exception as e:
                log.warning(f"⚠️ Location extraction issue for {username}: {e}")


            profile = {
                "user_name": username,
                "name": name_el[0].text if name_el else "",
                "bio": bio_el[0].text if bio_el else "",
                "location": location_text,
                "followers": follower_el[0].text if follower_el else "",
                "following": following_el[0].text if following_el else "",
                "verified": bool(verified_el),
                "posts": "",
                "url": url,
            }

            time.sleep(random.uniform(1.0, 2.5))
            log.info(f"✅ Scraped {username} | Location: {profile['location']}")
            driver.quit()
            return profile

        except Exception as e:
            log.error(f"❌ Error scraping {username} (attempt {attempt+1}/{retries}): {e}")
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            time.sleep(random.uniform(1.5, 3.0))

    log.warning(f"⚠️ Skipping {username} after {retries} attempts.")
    return {
        "user_name": username, "name": "", "bio": "", "location": "",
        "followers": "", "following": "", "verified": False, "posts": "", "url": url
    }



