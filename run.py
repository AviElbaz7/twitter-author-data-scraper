from pathlib import Path
import asyncio
import pandas as pd
import json
import twitter
import os
import math

# ---------- CONFIGURATION ----------
output = Path(__file__).parent
output_csv = output / "all_profiles.csv"
checkpoint_file = output / "progress.json"

BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES = 10
MAX_RETRIES_ON_429 = 5

FIELDS = [
    "id", "rest_id", "verified", "created_at", "bio",
    "favourites_count", "followers", "following",
    "usersAddedHim", "location", "media_count", "name",
    "user_name", "posts", "url"
]
# -----------------------------------


async def scrape_one(username):
    """Scrape one Twitter user with retry/backoff."""
    url = f"https://twitter.com/{username}"
    for attempt in range(MAX_RETRIES_ON_429):
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
                "user_name": username,
                "posts": profile.get("statuses_count"),
                "url": profile.get("url")
            }
        except Exception as e:
            msg = str(e)
            if "429" in msg or "throttled" in msg.lower():
                wait = (attempt + 1) * 30
                print(f"⚠️  429 for {username}. Sleeping {wait}s before retry ({attempt+1}/{MAX_RETRIES_ON_429})...")
                await asyncio.sleep(wait)
                continue
            else:
                print(f"❌ {username}: {e}")
                return None
    print(f"⛔ Gave up on {username} after {MAX_RETRIES_ON_429} retries.")
    # Log failed user for later reprocessing
    with open("failed_users.txt", "a", encoding="utf-8") as f:
        f.write(username + "\n")

    return None


def load_checkpoint():
    """Load checkpoint to resume."""
    if checkpoint_file.exists():
        try:
            data = json.loads(checkpoint_file.read_text())
            return data.get("last_batch", 0)
        except Exception:
            return 0
    return 0


def save_checkpoint(batch_number):
    """Save checkpoint after each batch."""
    checkpoint_file.write_text(json.dumps({"last_batch": batch_number}, indent=2))


async def run(usernames):
    twitter.BASE_CONFIG["debug"] = False
    results = []

    # Normalize usernames
    usernames = [u.strip().lower() for u in usernames if u.strip()]

    # Resume from CSV
    done_usernames = set()
    if os.path.exists(output_csv):
        existing = pd.read_csv(output_csv)
        if "user_name" in existing.columns:
            done_usernames = set(
                existing["user_name"].dropna().astype(str).str.strip().str.lower().tolist()
            )
            results = existing.to_dict("records")

    # Skip users already done
    usernames = [u for u in usernames if u not in done_usernames]

    # Determine starting batch
    last_batch = load_checkpoint()
    start_index = last_batch * BATCH_SIZE
    total_batches = math.ceil(len(usernames) / BATCH_SIZE)

    print(f"▶️ Total users left: {len(usernames)}")
    print(f"▶️ Resuming from batch {last_batch + 1}/{total_batches} (starting index {start_index})")

    for batch_number, i in enumerate(range(start_index, len(usernames), BATCH_SIZE), start=last_batch + 1):
        batch = usernames[i:i + BATCH_SIZE]
        print(f"\n▶️  Processing batch {batch_number}/{total_batches} ({len(batch)} users)... ({i + len(batch)}/{len(usernames)})")

        batch_results = await asyncio.gather(*(scrape_one(u) for u in batch))
        batch_results = [r for r in batch_results if r]

        results.extend(batch_results)
        pd.DataFrame(results, columns=FIELDS).to_csv(output_csv, index=False, encoding="utf-8-sig")
        save_checkpoint(batch_number)
        print(f"💾 Saved {len(results)} profiles so far. (Checkpoint: batch {batch_number})")

        await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    print(f"\n✅ Finished scraping {len(results)} profiles.")
    checkpoint_file.unlink(missing_ok=True)
    print(f"📄 Final results saved to {output_csv}")


def scrape_from_file(file_path, column_name):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please use .csv or .xlsx")

    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in file.")

    usernames = df[column_name].dropna().astype(str).str.replace("@", "").str.strip().tolist()
    usernames = [u for u in usernames if u]

    total = len(usernames)
    print(f"\nLoaded {total} usernames from file.")
    print(f"▶️  Starting run for {total} users.")

    asyncio.run(run(usernames))




if __name__ == "__main__":
    input_file = "/Users/avielbaz/Desktop/twitter-author-data-scraper/all_users.csv"
    column_name = "user_name"
    scrape_from_file(input_file, column_name)
