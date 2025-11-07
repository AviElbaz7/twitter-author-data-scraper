import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_twitter_profile(username: str):
    url = f"https://twitter.com/{username}"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)

    # scroll a few times to let Twitter load dynamic sections
    for _ in range(4):
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)

    data = {
        "user_name": username,
        "name": "",
        "bio": "",
        "location": "",
        "url": "",
        "joined_date": "",
        "followers": "",
        "following": "",
        "verified": False,
        "profile_url": url,
    }

    # --- name ---
    try:
        name_el = driver.find_element(By.XPATH, '//div[@data-testid="UserName"]//span[1]')
        data["name"] = name_el.text.strip()
    except:
        pass

    # --- bio ---
    try:
        bio_el = driver.find_element(By.XPATH, "//div[@data-testid='UserDescription']")
        data["bio"] = bio_el.text.strip()
    except:
        pass

    # --- location ---
    try:
        loc_el = driver.find_element(By.XPATH, "//span[@data-testid='UserLocation']")
        data["location"] = loc_el.text.strip()
    except:
        pass

    # --- external URL ---
    try:
        url_el = driver.find_element(By.XPATH, "//a[@data-testid='UserUrl']")
        data["url"] = url_el.get_attribute("href").strip()
    except:
        pass

    # --- joined date ---
    try:
        join_el = driver.find_element(By.XPATH, "//span[contains(text(),'Joined')]")
        data["joined_date"] = join_el.text.replace("Joined", "").strip()
    except:
        pass

    # --- Profile image ---
    try:
        img_el = driver.find_element(By.XPATH, "//img[contains(@alt,'Image') or contains(@src,'profile_images')]")
        data["profile_image"] = img_el.get_attribute("src")
    except:
        pass

    # --- followers & following (robust JS extraction) ---
    for _ in range(6):
        counts = driver.execute_script("""
            let result = {};
            let fwing = document.querySelector("a[href$='/following'] span span");
            let fwers = document.querySelector("a[href$='/followers'] span span");
            result.following = fwing ? fwing.textContent.trim() : '';
            result.followers = fwers ? fwers.textContent.trim() : '';
            return result;
        """)
        if counts.get("followers") or counts.get("following"):
            data["followers"] = counts.get("followers", "")
            data["following"] = counts.get("following", "")
            break
        time.sleep(1)

    # --- backup regex if JS didn’t catch ---
    if not data["followers"] or not data["following"]:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        m_followers = re.search(r'(\d[\d,]*) Followers', body_text)
        m_following = re.search(r'(\d[\d,]*) Following', body_text)
        if m_followers:
            data["followers"] = m_followers.group(1)
        if m_following:
            data["following"] = m_following.group(1)

    # --- verified ---
    data["verified"] = "Verified account" in driver.page_source

    driver.quit()
    return data


if __name__ == "__main__":
    result1 = scrape_twitter_profile("Margarita100313")
    result2 = scrape_twitter_profile("oksanatserkovna")
    print(result1)
    print(result2)
