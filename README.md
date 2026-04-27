# GeoLocation for Indoor Images

This project focuses on improving image geolocation for indoor scenes. Most geolocation models perform well on outdoor landmarks but are weaker on indoor or semi-indoor images (hotel rooms, restaurants, malls, etc.). We use GeoCLIP as the baseline model and build a scraping pipeline to collect place-linked image data for evaluation and future fine-tuning.

Original GeoCLIP paper: [https://arxiv.org/abs/2103.00020](https://arxiv.org/abs/2103.00020)

## Current Data Collection Approach (Bright Data)

The older Selenium/Scrapy scraping flow has been replaced with a Bright Data dataset pipeline.

The Bright Data workflow is designed to:
1. Cover UAE regions using a geographic grid.
2. Query place categories (restaurant, cafe, hotel, etc.) around each grid point.
3. Save rich place metadata and image URLs.
4. Download image assets for later GeoCLIP evaluation.

### What the scraping looks like

Each API input is a location-centered query in this shape:
- country
- lat / long
- zoom_level
- keyword (example: hotel, restaurant, clinic)

For each input, Bright Data returns place records including fields such as:
- place_id, fid_location
- name, address, country
- lat, lon
- main_image
- photos_and_videos (used for image download)

The scraper runs as snapshot jobs:
1. Trigger snapshot for one grid-point/keyword input.
2. Poll until status is ready (or failed).
3. Download JSON result.
4. Deduplicate by place_id and append to results file.

## Directory Overview

### brightdata/

Main folder for the new scraping pipeline.

- `generate_grid.py`
	- Builds `input_grid.json` from UAE bounding boxes and a keyword list.
	- Applies spacing and deduplication to reduce overlapping requests.
	- Prints and saves a cost summary (`grid_summary.txt`).

- `visualize_grid.py`
	- Loads `input_grid.json`.
	- Generates an interactive map (`grid_map.html`) to inspect coverage by emirate.

- `BDscraper.py`
	- Reads `input_grid.json`.
	- Triggers Bright Data dataset snapshots and polls progress.
	- Downloads records and appends deduplicated output to `data/resultsAE.json`.
	- Logs run details to `data/scraper.log`.
	- Enforces budget safety using `RATE_PER_1K`, `BUDGET_LIMIT`, and `initial_cost`.

- `download_images.py`
	- Reads scraped records and extracts URLs from `photos_and_videos`.
	- Downloads images concurrently to `data/images/`.
	- Skips files that already exist (resumable behavior).

- `.env`
	- Stores `BRIGHTDATA_API_KEY`.

### geoclip_eval/

Contains evaluation scripts for pre-trained GeoCLIP. The evaluator reads image paths and outputs predicted coordinates plus distance error metrics.

### image_clustering/

Contains exploratory clustering work to separate image groups (for example food vs non-food), helping with downstream labeling and analysis.

### review_scraper(outdated)/

Legacy Selenium/Scrapy implementation kept for reference only. Active scraping now uses Bright Data.

## Updated Run Instructions (Bright Data)

Run commands from `brightdata/`.

### 1) Setup environment

```bash
cd brightdata
python -m venv .venv
```

Activate venv:

- Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

- Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` in `brightdata/` with:

```env
BRIGHTDATA_API_KEY=your_api_key_here
```

### 2) Generate location grid

```bash
python generate_grid.py
```

This creates:
- `input_grid.json`
- `grid_summary.txt`

### 3) (Optional) Visualize grid coverage

```bash
python visualize_grid.py
```

This creates:
- `grid_map.html`

### 4) Scrape places via Bright Data

```bash
python BDscraper.py
```

Outputs:
- `data/resultsAE.json` (deduplicated place records)
- `data/scraper.log` (run log)

Important settings in `BDscraper.py`:
- `RATE_PER_1K`
- `BUDGET_LIMIT`
- `initial_cost` (set to prior spend so budget checks reflect all-time usage)

### 5) Download images from scraped records

```bash
python download_images.py
```

By default, this script expects an input JSON path defined by `INPUT_FILE`. If your scrape output is `data/resultsAE.json`, set `INPUT_FILE` accordingly before running.

Images are saved to:
- `data/images/`

## Notes

- The scraper is robust to partial runs: results are appended and deduplicated.
- Image downloading is resumable because existing files are skipped.
- Cost control is built in, but you should still monitor Bright Data usage from your account dashboard.

## Next Phase

After data collection, the dataset is used to:
1. Evaluate baseline GeoCLIP performance on indoor-heavy imagery.
2. Compare performance across image categories.
3. Prepare training/evaluation data for future indoor-focused fine-tuning.
