import re
import json
import os
import time
import requests
import cloudscraper
from datetime import datetime
import pytz

GIST_TOKEN = os.environ["GIST_TOKEN"]
GIST_ID = os.environ["GIST_ID"]
URL = "https://waymo.codes/"

blacklist = {
    "WAYMO", "LLC", "INC", "LOS", "ANGELES", "PHOENIX",
    "DOCTYPE", "DELETE", "SELECT", "INSERT", "UPDATE",
    "FALSE", "TRUE", "NULL", "NONE", "UTF8",
    "SCRIPT", "STYLE", "CLASS", "INDEX", "HTTPS",
    "HTTP", "HTML", "HEAD", "BODY", "META"
}


def get_time():
    mst = pytz.timezone("US/Mountain")
    return datetime.now(mst).strftime("%Y-%m-%d %I:%M:%S %p MST")


def get_gist():
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    res = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    res.raise_for_status()
    content = res.json()["files"]["waymo_codes.json"]["content"]
    return json.loads(content)


def update_gist(data):
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    payload = {
        "files": {
            "waymo_codes.json": {
                "content": json.dumps(data, indent=2)
            }
        }
    }
    res = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers,
        json=payload
    )
    res.raise_for_status()


def scrape(scraper_client):
    try:
        response = scraper_client.get(URL, timeout=15)
        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            print("Blocked or error, skipping update")
            return

        text = response.text

        # Step 1: Basic regex match
        codes = re.findall(r'\b[A-Z0-9]{6,12}\b', text)

        # Step 2: Strip whitespace / hidden chars
        codes = [c.strip() for c in codes]

        # Step 3: Must contain BOTH letter and digit
        codes = [
            c for c in codes
            if any(ch.isalpha() for ch in c)
            and any(ch.isdigit() for ch in c)
        ]

        # Step 4: Remove blacklist prefixes (DELETE4444 etc.)
        codes = [
            c for c in codes
            if not any(c.startswith(word) for word in blacklist)
        ]

        current_set = set(codes)
        print(f"Codes found: {current_set}")

        data = get_gist()
        live = data.get("live", {})
        archived = data.get("archived", {})

        # Add new codes
        for code in current_set:
            if code not in live and code not in archived:
                live[code] = get_time()

        # Move disappeared codes to archive
        for code in list(live.keys()):
            if code not in current_set:
                archived[code] = get_time()
                live.pop(code)

        update_gist({"live": live, "archived": archived})
        print("Gist updated successfully")

    except Exception as e:
        print(f"Scrape error: {e}")


# Create scraper
scraper_client = cloudscraper.create_scraper()

# Run 20 times (every 20 seconds)
for i in range(20):
    print(f"\n--- Scrape {i+1}/20 ---")
    scrape(scraper_client)
    if i < 19:
        time.sleep(15)
