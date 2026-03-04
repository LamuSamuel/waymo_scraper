import re
import json
import os
import time
import requests
import cloudscraper

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

def get_gist():
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    res = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    content = res.json()["files"]["waymo_codes.json"]["content"]
    return json.loads(content)

def update_gist(data):
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    payload = {
        "files": {
            "waymo_codes.json": {
                "content": json.dumps(data)
            }
        }
    }
    requests.patch(f"https://api.github.com/gists/{GIST_ID}", headers=headers, json=payload)

def scrape(scraper_client):
    try:
        response = scraper_client.get(URL)
        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            print("Blocked or error, skipping update")
            return

        text = response.text
        codes = re.findall(r'\b[A-Z0-9]{6,12}\b', text)
        codes = [c for c in codes if c not in blacklist and any(char.isdigit() for char in c)]
        current_set = set(codes)
        print(f"Codes found: {current_set}")

        data = get_gist()
        live = data.get("live", {})
        archived = data.get("archived", {})

        for code in current_set:
            if code not in live and code not in archived:
                live[code] = "just now"

        for code in list(live.keys()):
            if code not in current_set:
                archived[code] = live.pop(code)

        update_gist({"live": live, "archived": archived})
        print("Gist updated successfully")

    except Exception as e:
        print(f"Scrape error: {e}")

# Run 10 times, every 30 seconds = 5 minutes total
scraper_client = cloudscraper.create_scraper()

for i in range(10):
    print(f"\n--- Scrape {i+1}/10 ---")
    scrape(scraper_client)
    if i < 9:
        time.sleep(30)
