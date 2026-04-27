import requests
import os
import time
import json
import logging

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

API_KEY = os.getenv("BRIGHTDATA_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

with open("./input_grid.json", encoding="utf-8") as f:
    SEARCH_INPUTS = json.load(f)

ENDPOINT = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_m8ebnr0q2qlklc02fz&notify=false&include_errors=true&type=discover_new&discover_by=location"
CUSTOM_FIELDS = "place_id|url|country|name|address|main_image|lat|lon|photos_and_videos|fid_location"

RATE_PER_1K = 1.50  # USD per 1000 records
BUDGET_LIMIT = 500.00  # USD — stop run if all-time cost exceeds this
initial_cost = 44.04  # USD — if you have prior costs from previous runs, set that here to account for it in the budget limit

def cost(record_count):
    return (record_count / 1000) * RATE_PER_1K


def trigger_snapshot(entry):
    payload = {
        "input": [entry],
        "custom_output_fields": CUSTOM_FIELDS
    }
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    snapshot_id = response.json()["snapshot_id"]
    print(f"  Triggered snapshot {snapshot_id} for ({entry['keyword']!r} @ {entry['lat']},{entry['long']})")
    log.info("Triggered %s  (%r @ %s,%s)", snapshot_id, entry["keyword"], entry["lat"], entry["long"])
    return snapshot_id


def wait_for_snapshot(snapshot_id):
    last_status = None
    while True:
        progress = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers=headers
        ).json()
        status = progress["status"]
        print(f"  [{snapshot_id}] Status: {status}")
        if status != last_status:
            log.info("[%s] Status: %s", snapshot_id, status)
            last_status = status
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

# File-only logger — terminal output is handled by the existing print() calls
_file_handler = logging.FileHandler("./data/scraper.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
log = logging.getLogger("scraper")
log.setLevel(logging.INFO)
log.addHandler(_file_handler)
log.propagate = False

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
received_this_run = 0
prior_records = total_saved
print(f"Existing records in file: {prior_records} (prior cost: ${initial_cost:.4f})")
log.info("=== Run started — existing records: %d (prior cost: $%.4f) ===", prior_records, initial_cost)


def append_results(new_records):
    global existing, total_saved, new_records_this_run, received_this_run
    if not isinstance(new_records, list):
        new_records = [new_records]

    received_this_run += len(new_records)
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
        log.info("Skipped %d duplicate(s)", skipped)

    existing.extend(unique)
    total_saved = len(existing)
    new_records_this_run += len(unique)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=4)
    return len(unique)


total_inputs = len(SEARCH_INPUTS)
for idx, entry in enumerate(SEARCH_INPUTS, start=1):
    if initial_cost + cost(received_this_run) >= BUDGET_LIMIT:
        print(f"\nBudget limit of ${BUDGET_LIMIT:.2f} reached (${initial_cost + cost(received_this_run):.4f} all-time). Stopping.")
        log.warning("Budget limit of $%.2f reached. Stopping at input %d/%d.", BUDGET_LIMIT, idx, total_inputs)
        break

    print(f"\nProcessing: ({entry['keyword']!r} @ {entry['lat']},{entry['long']})")
    log.info("[%d/%d] Processing: %r @ %s,%s", idx, total_inputs, entry["keyword"], entry["lat"], entry["long"])
    try:
        snapshot_id = trigger_snapshot(entry)
        success = wait_for_snapshot(snapshot_id)
        if success:
            data = download_snapshot(snapshot_id)
            count = append_results(data)
            print(f"  Retrieved {count} record(s) — {total_saved} total in file")
            print(f"  This run: {new_records_this_run} records / ${cost(received_this_run):.4f} | All-time: {total_saved} records / ${initial_cost + cost(received_this_run):.4f}")
            log.info("Retrieved %d record(s) — %d total | This run: %d / $%.4f | All-time: $%.4f",
                     count, total_saved, new_records_this_run, cost(received_this_run), initial_cost + cost(received_this_run))
            if initial_cost + cost(received_this_run) >= BUDGET_LIMIT:
                print(f"\nBudget limit of ${BUDGET_LIMIT:.2f} reached after this snapshot. Stopping.")
                log.warning("Budget limit of $%.2f reached after snapshot %s. Stopping.", BUDGET_LIMIT, snapshot_id)
                break
        else:
            print(f"  Skipping download for failed snapshot {snapshot_id}")
            log.warning("Skipping download for failed snapshot %s", snapshot_id)
    except Exception as e:
        print(f"  Error for ({entry['keyword']!r} @ {entry['lat']},{entry['long']}): {e}")
        log.error("Error at input %d/%d (%r @ %s,%s): %s", idx, total_inputs, entry["keyword"], entry["lat"], entry["long"], e)

print(f"\n--- Run Summary ---")
print(f"New records this run : {new_records_this_run} (${cost(received_this_run):.4f})")
print(f"Total records in file: {total_saved} (${initial_cost + cost(received_this_run):.4f} all-time)")
log.info("=== Run Summary — new: %d ($%.4f) | total: %d ($%.4f) ===",
         new_records_this_run, cost(received_this_run), total_saved, initial_cost + cost(received_this_run))
