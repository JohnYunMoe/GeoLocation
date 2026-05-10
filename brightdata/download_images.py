import asyncio
import aiohttp
import aiofiles
import json
import os
from pathlib import Path
from urllib.parse import urlparse

INPUT_FILE = "./data/resultsgulf.json"
OUTPUT_DIR = "./data/images"
CONCURRENCY = 50  # tune this — lower if you get rate-limited


def extract_urls(entry: dict, entry_index: int) -> list[tuple[str, str]]:
    """Returns list of (url, local_filename) pairs from a single entry."""
    items = entry.get("photos_and_videos", [])
    if not items:
        return []

    results = []
    place_id = entry.get("place_id") or entry.get("fid_location") or f"entry_{entry_index}"
    place_id = str(place_id).replace("/", "_").replace(":", "_")  # safe for filenames

    for i, item in enumerate(items):
        # Handle both plain string URLs and {"url": "..."} objects
        url = item if isinstance(item, str) else item.get("url") or item.get("link") or item.get("src")
        if not url:
            continue

        ext = Path(urlparse(url).path).suffix or ".jpg"
        filename = f"{place_id}_{i}{ext}"
        results.append((url, filename))

    return results


async def download_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                       url: str, dest: Path) -> None:
    if dest.exists():
        return  # resumable — skip already downloaded

    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                async with aiofiles.open(dest, "wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        await f.write(chunk)
        except Exception as e:
            print(f"Failed {url}: {e}")


async def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Normalize: some APIs return a list, some wrap in {"results": [...]}
    entries = data if isinstance(data, list) else data.get("results", [data])

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Collect all tasks in one pass
    tasks_args = []
    for i, entry in enumerate(entries):
        for url, filename in extract_urls(entry, i):
            tasks_args.append((url, Path(OUTPUT_DIR) / filename))

    print(f"Total images to download: {len(tasks_args)}")

    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [download_one(session, sem, url, dest) for url, dest in tasks_args]
        await asyncio.gather(*tasks)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
