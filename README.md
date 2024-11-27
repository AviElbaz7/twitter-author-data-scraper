# Twitter Profile Meta Data Scraper

This repository contains a Python-based tool for scraping public profile data from Twitter using the Scrapfly service. The tool is designed to handle a list of usernames from a file and export the scraped data to a CSV file.

---

## Features

- **Scrape Twitter Profiles**: Extracts public information such as followers, bio, location, and more.
- **Asynchronous Scraping**: Leverages Python's asyncio for efficient scraping.
- **File Input**: Reads usernames from CSV or Excel files.
- **Customizable Output**: Outputs data to a structured CSV file.

---

## Setup

### Prerequisites

1. **Python Version**: Ensure you have Python 3.8 or later installed.
2. **Scrapfly API Key**: Set up an account at [Scrapfly](https://scrapfly.io) and obtain your API key.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/twitter-profile-scraper.git
   cd twitter-profile-scraper

2. Install the required dependencies:
   ```bash
    pip install -r requirements.txt

3. Export your Scrapfly API key as an environment variable:
   export SCRAPFLY_KEY="your_scrapfly_api_key"

## File Explanations

### `run.py`
This is the main script responsible for executing the scraping process. It does the following:
- Reads usernames from an input CSV or Excel file.
- Cleans and validates the usernames.
- Uses the `twitter.py` module to scrape profile data asynchronously.
- Exports the scraped data to a CSV file named `all_profiles.csv`.

**Key Functions**:
- `scrape_from_file(file_path, column_name)`: Handles file input and calls the scraper for each username.
- `run(usernames)`: Asynchronous function to scrape multiple profiles and save the data.

---

### `twitter.py`
This module contains the core logic for interacting with Twitter via Scrapfly. It handles:
- Sending requests to Twitter pages using Scrapfly's JavaScript rendering capabilities.
- Parsing JSON responses to extract relevant profile information.

**Key Functions**:
- `scrape_profile(url)`: Scrapes a Twitter profile page and returns parsed data.
- `parse_profile(data)`: Processes JSON responses into a structured format.


## Usage

### Running the Scraper

1. Prepare an input file (CSV or Excel) containing Twitter usernames.
   - Ensure the usernames are in a single column with a header (e.g., `Twitter_Username`).

2. Modify the `run.py` script:
   ```python
   # File: run.py

   # Define your input file path and column name
   input_file = "/path/to/your/input.xlsx"  # Replace with the path to your input file
   column_name = "Twitter_Username"  # Replace with the name of the column containing usernames

3. Run the scraper:
     python run.py


