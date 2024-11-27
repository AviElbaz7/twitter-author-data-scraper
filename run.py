from pathlib import Path
import asyncio
import pandas as pd
import twitter

# Directory to save the output file in the same location as the script
output = Path(__file__).parent
output_csv = output / "all_profiles.csv"

# Define the required fields for the output CSV file
fields = [
    "id", "rest_id", "verified", "created_at", "bio", 
    "favourites_count", "followers", "following", 
    "usersAddedHim", "location", "media_count", "name", 
    "user_name", "posts", "url"
]

async def run(usernames):
    """
    Asynchronous function to scrape Twitter profiles for a list of usernames.

    Args:
        usernames (list): A list of Twitter usernames to scrape.

    Returns:
        None: Saves the results to a CSV file.
    """
    twitter.BASE_CONFIG["debug"] = True
    all_profiles = []

    print("Running Twitter profile scrape for multiple users...")
    for username in usernames:
        url = f"https://twitter.com/{username}"  # Construct profile URL
        print(f"Scraping profile: {url}")
        try:
            # Scrape the profile data
            profile = await twitter.scrape_profile(url)

            # Extract relevant fields and add to the results list
            profile_data = {
                "id": profile.get("id"),
                "rest_id": profile.get("rest_id"),
                "verified": profile.get("verified"),
                "created_at": profile.get("created_at"),
                "bio": profile.get("description"),
                "favourites_count": profile.get("favourites_count"),
                "followers": profile.get("followers_count"),
                "following": profile.get("friends_count"),
                "usersAddedHim": profile.get("listed_count"),
                "location": profile.get("location"),
                "media_count": profile.get("media_count"),
                "name": profile.get("name"),
                "user_name": profile.get("screen_name"),
                "posts": profile.get("statuses_count"),
                "url": profile.get("url")
            }
            all_profiles.append(profile_data)
            print(f"Scraped profile for {username}")
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")

    # Convert the data into a DataFrame and save it as a CSV file
    df = pd.DataFrame(all_profiles, columns=fields)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"All profiles saved to {output_csv}")


def scrape_from_file(file_path, column_name):
    """
    Main function to scrape Twitter profiles from usernames provided in a file.

    Args:
        file_path (str): Path to the input CSV or Excel file.
        column_name (str): Name of the column containing Twitter usernames.

    Returns:
        None: Scrapes profiles and saves them to a CSV file.
    """
    # Read the file and extract the usernames
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide a .csv or .xlsx file.")

    # Validate the specified column and clean the usernames
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in the file.")

    df = df.dropna(subset=[column_name])  # Drop rows with missing values in the column
    df[column_name] = df[column_name].astype(str).str.replace("@", "").str.strip()  # Clean usernames

    # Filter valid usernames
    usernames = df[column_name][df[column_name] != ""].tolist()
    if not usernames:
        raise ValueError("No valid usernames found in the specified column.")

    # Run the scraper asynchronously
    asyncio.run(run(usernames))


if __name__ == "__main__":
    # Define your input file path and column name
    input_file = "/path/to/your/input.xlsx"  # Replace with your file path
    column_name = "Twitter_Username"  # Replace with your column name

    scrape_from_file(input_file, column_name)
