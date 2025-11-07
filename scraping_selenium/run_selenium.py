from pathlib import Path
import asyncio
import pandas as pd
import os
import time
import twitter_selenium as twitter  # ✅ Selenium version

# -----------------------------------
# Config
# -----------------------------------
BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES = 5  # seconds
output = Path(__file__).parent
output_csv = output / "all_profiles.csv"
checkpoint_file = output / "checkpoint.txt"

# ✅ updated to match new scraper fields
fields = [
    "user_name", "name", "bio", "location", "url",
    "joined_date", "followers", "following", "verified",
    "profile_image", "profile_url"
]



# -----------------------------------
# Helper: save checkpoint
# -----------------------------------
def save_checkpoint(batch_index: int):
    with open(checkpoint_file, "w") as f:
        f.write(str(batch_index))


def load_checkpoint():
    if checkpoint_file.exists():
        with open(checkpoint_file, "r") as f:
            return int(f.read().strip())
    return 0


# -----------------------------------
# Async scraping runner
# -----------------------------------
async def run(usernames):
    total_users = len(usernames)
    total_batches = (total_users + BATCH_SIZE - 1) // BATCH_SIZE
    start_batch = load_checkpoint()

    if start_batch > 0:
        print(f"▶️  Resuming from batch {start_batch}/{total_batches}")
    else:
        print(f"▶️  Starting fresh run with {total_users} users.")

    for batch_index in range(start_batch, total_batches):
        start_idx = batch_index * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_users)
        batch = usernames[start_idx:end_idx]

        print(f"\n▶️  Processing batch {batch_index + 1}/{total_batches} ({end_idx}/{total_users})")
        batch_results = []

        for username in batch:
            try:
                profile = twitter.scrape_twitter_profile(username)
                batch_results.append(profile)
            except Exception as e:
                print(f"❌ Failed to scrape {username}: {e}")

        df = pd.DataFrame(batch_results, columns=fields)
        if output_csv.exists() and batch_index > 0:
            df.to_csv(output_csv, mode="a", index=False, header=False, encoding="utf-8-sig")
        else:
            df.to_csv(output_csv, index=False, encoding="utf-8-sig")

        save_checkpoint(batch_index + 1)
        print(f"💾 Saved {end_idx} profiles (Checkpoint: batch {batch_index + 1})")

        if batch_index + 1 < total_batches:
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    print(f"\n✅ All {total_users} profiles scraped and saved to {output_csv}")


# -----------------------------------
# File reader
# -----------------------------------
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

    print(f"\nLoaded {len(usernames)} usernames from file.")
    asyncio.run(run(usernames))


# -----------------------------------
# Main
# -----------------------------------
if __name__ == "__main__":
    input_file = "/Users/avielbaz/Desktop/author-works/all_users.csv"
    column_name = "user_name"
    scrape_from_file(input_file, column_name)

## Testing
#if __name__ == "__main__":
#    test_users = ["severniy76", "oksanatserkovna", "stunnedhare", "mhrtssblck", "kolymus"]
#    asyncio.run(run(test_users))

    
