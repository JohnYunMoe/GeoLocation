import requests
import os
import time
import json

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

API_KEY = os.getenv("BRIGHTDATA_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

with open("./input.json", encoding="utf-8") as f:
    SEARCH_PAIRS = [(entry["country"], entry["keyword"]) for entry in json.load(f)]

ENDPOINT = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_m8ebnr0q2qlklc02fz&notify=false&include_errors=true&type=discover_new&discover_by=location"
CUSTOM_FIELDS = "place_id|url|country|name|address|main_image|lat|lon|photos_and_videos|fid_location"

RATE_PER_1K = 1.50  # USD per 1000 records
BUDGET_LIMIT = 100.00  # USD — stop run if all-time cost exceeds this

def cost(record_count):
    return (record_count / 1000) * RATE_PER_1K


def trigger_snapshot(country, keyword):
    payload = {
        "input": [{"country": country, "keyword": keyword}],
        "custom_output_fields": CUSTOM_FIELDS
    }
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    snapshot_id = response.json()["snapshot_id"]
    print(f"  Triggered snapshot {snapshot_id} for ({country!r}, {keyword!r})")
    return snapshot_id


def wait_for_snapshot(snapshot_id):
    while True:
        progress = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers=headers
        ).json()
        status = progress["status"]
        print(f"  [{snapshot_id}] Status: {status}")
        if status == "ready":
            return True
        elif status == "failed":
            print(f"  [{snapshot_id}] Job failed")
            return False
        time.sleep(5)


def download_snapshot(snapshot_id):
    response = requests.get(
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
        headers=headers,
        params={"format": "json"}
    )
    response.raise_for_status()
    return response.json()


os.makedirs("./data", exist_ok=True)
output_path = "./data/resultsAE.json"

# Load existing results if file already has data
if os.path.exists(output_path):
    with open(output_path, encoding="utf-8") as f:
        try:
            existing = json.load(f)
            total_saved = len(existing) if isinstance(existing, list) else 0
        except json.JSONDecodeError:
            existing = []
            total_saved = 0
else:
    existing = []
    total_saved = 0

new_records_this_run = 0
prior_records = total_saved
print(f"Existing records in file: {prior_records} (prior cost: ${cost(prior_records):.4f})")


def append_results(new_records):
    global existing, total_saved, new_records_this_run
    if not isinstance(new_records, list):
        new_records = [new_records]

    existing_ids = {r.get("place_id") for r in existing if r.get("place_id")}

    unique = []
    skipped = 0
    for record in new_records:
        pid = record.get("place_id")
        if pid and pid in existing_ids:
            skipped += 1
        else:
            unique.append(record)
            if pid:
                existing_ids.add(pid)

    if skipped:
        print(f"  Skipped {skipped} duplicate(s)")

    existing.extend(unique)
    total_saved = len(existing)
    new_records_this_run += len(unique)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=4)
    return len(unique)


for country, keyword in SEARCH_PAIRS:
    if cost(total_saved) >= BUDGET_LIMIT:
        print(f"\nBudget limit of ${BUDGET_LIMIT:.2f} reached (${cost(total_saved):.4f} all-time). Stopping.")
        break

    print(f"\nProcessing: ({country!r}, {keyword!r})")
    try:
        snapshot_id = trigger_snapshot(country, keyword)
        success = wait_for_snapshot(snapshot_id)
        if success:
            data = download_snapshot(snapshot_id)
            count = append_results(data)
            print(f"  Retrieved {count} record(s) — {total_saved} total in file")
            print(f"  This run: {new_records_this_run} records / ${cost(new_records_this_run):.4f} | All-time: {total_saved} records / ${cost(total_saved):.4f}")
            if cost(total_saved) >= BUDGET_LIMIT:
                print(f"\nBudget limit of ${BUDGET_LIMIT:.2f} reached after this snapshot. Stopping.")
                break
        else:
            print(f"  Skipping download for failed snapshot {snapshot_id}")
    except Exception as e:
        print(f"  Error for ({country!r}, {keyword!r}): {e}")

print(f"\n--- Run Summary ---")
print(f"New records this run : {new_records_this_run} (${cost(new_records_this_run):.4f})")
print(f"Total records in file: {total_saved} (${cost(total_saved):.4f} all-time)")
