from pathlib import Path
import asyncio
import pandas as pd
import json
import twitter
import os

# ---------- Configuration ----------
output = Path(__file__).parent
output_csv = output / "all_profiles.csv"

BATCH_SIZE = 50               # number of concurrent scrapes
DELAY_BETWEEN_BATCHES = 2     # seconds between batches
# -----------------------------------

fields = [
    "id", "rest_id", "verified", "created_at", "bio",
    "favourites_count", "followers", "following",
    "usersAddedHim", "location", "media_count", "name",
    "user_name", "posts", "url"
]


# ---------- Scraper for a single user ----------
async def scrape_one(username):
    url = f"https://twitter.com/{username}"
    try:
        profile = await twitter.scrape_profile(url)

        location = (
            profile.get("location")
            or profile.get("profile_location")
            or (profile.get("legacy", {}).get("location") if isinstance(profile.get("legacy"), dict) else None)
            or ""
        )

        return {
            "id": profile.get("id"),
            "rest_id": profile.get("rest_id"),
            "verified": profile.get("verified"),
            "created_at": profile.get("created_at"),
            "bio": profile.get("description"),
            "favourites_count": profile.get("favourites_count"),
            "followers": profile.get("followers_count"),
            "following": profile.get("friends_count"),
            "usersAddedHim": profile.get("listed_count"),
            "location": location.strip() if isinstance(location, str) else "",
            "media_count": profile.get("media_count"),
            "name": profile.get("name"),
            "user_name": profile.get("screen_name"),
            "posts": profile.get("statuses_count"),
            "url": profile.get("url")
        }
    except Exception as e:
        print(f"❌ {username}: {e}")
        return None


# ---------- Main async runner ----------
async def run(usernames):
    twitter.BASE_CONFIG["debug"] = False
    results = []

    # --- Resume support ---
    if os.path.exists(output_csv):
        existing = pd.read_csv(output_csv)
        done_usernames = set(existing["user_name"].astype(str))
        usernames = [u for u in usernames if u not in done_usernames]
        results = existing.to_dict("records")
        print(f"▶️ Resuming... {len(done_usernames)} users already done, {len(usernames)} left.")
    else:
        print(f"▶️ Starting fresh run with {len(usernames)} users.")

    total = len(usernames)
    if total == 0:
        print("✅ Nothing to scrape — all users already processed.")
        return

    # --- Batch processing ---
    for i in range(0, total, BATCH_SIZE):
        batch = usernames[i:i + BATCH_SIZE]
        print(f"\n▶️  Processing batch {i // BATCH_SIZE + 1} "
              f"({len(batch)} users)... ({i + len(batch)}/{total})")

        batch_results = await asyncio.gather(*(scrape_one(u) for u in batch))
        batch_results = [r for r in batch_results if r]

        results.extend(batch_results)

        # --- Save partial progress ---
        pd.DataFrame(results, columns=fields).to_csv(output_csv, index=False, encoding="utf-8-sig")
        print(f"💾 Saved {len(results)} profiles so far.")
        await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    print(f"\n✅ Finished scraping {len(results)} profiles in total.")
    pd.DataFrame(results, columns=fields).to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"📄 Final results saved to {output_csv}")


# ---------- Entry point ----------
def scrape_from_file(file_path, column_name):
    """Read usernames from file and run scraper."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format.")

    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in the file.")

    df = df.dropna(subset=[column_name])
    df[column_name] = df[column_name].astype(str).str.replace("@", "").str.strip()

    usernames = df[column_name][df[column_name] != ""].tolist()
    print(f"\nLoaded {len(usernames)} usernames from file.")

    asyncio.run(run(usernames))


if __name__ == "__main__":
    input_file = "/Users/example/Desktop/twitter-author-data-scraper/all_users.csv"
    column_name = "user_name"
    scrape_from_file(input_file, column_name)
