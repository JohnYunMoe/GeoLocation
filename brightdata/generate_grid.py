import json
import math
import os


def generate_grid(min_lat, min_lon, max_lat, max_lon, cell_size_km, keywords, country="AE", zoom=14.5):
    """
    Divide a bounding box into a grid of cells and return one BrightData input
    dict per (cell center, keyword) pair.

    Latitude step is constant: 1 degree lat = 111 km.
    Longitude step varies with latitude: 1 degree lon = 111 * cos(lat) km,
    so we fix the step using the bounding box's center latitude.
    """
    center_lat = (min_lat + max_lat) / 2.0
    lat_step = cell_size_km / 111.0
    lon_step = cell_size_km / (111.0 * math.cos(math.radians(center_lat)))

    entries = []
    lat = min_lat + lat_step / 2.0  # start at cell center, not edge
    while lat <= max_lat:
        lon = min_lon + lon_step / 2.0
        while lon <= max_lon:
            for keyword in keywords:
                entries.append({
                    "country": country,
                    "lat": round(lat, 6),
                    "long": round(lon, 6),
                    "zoom_level": zoom,
                    "keyword": keyword,
                })
            lon += (2.5 * lon_step + lon_step)  # add extra 2.5 steps to reduce overlap between adjacent cells
        lat += (2.5 * lat_step + lat_step)  # add extra 2.5 steps to reduce overlap between adjacent cells

    return entries


# ---------------------------------------------------------------------------
# UAE emirate bounding boxes
# ---------------------------------------------------------------------------
EMIRATES = {
    "Fujairah": {
        "bbox": (25.0133, 56.2273, 25.4341, 56.3748),
        "cell_size_km": 5.0,
    },
    "Abu Dhabi 1": {
        "bbox": (24.2072, 54.4324, 24.4285, 54.8095),
        "cell_size_km": 5.0,
    },
    "Abu Dhabi 2": {
        "bbox": (24.4099, 54.3244, 24.5121, 54.4286),
        "cell_size_km": 5.0,
    },
    "Abu Dhabi 3": {
        "bbox": (24.5168, 54.3968, 24.5433, 54.5308),
        "cell_size_km": 5.0,
    },
    "Abu Dhabi 4": {
        "bbox": (24.4295, 54.4295, 24.5148, 54.5973),
        "cell_size_km": 5.0,
    },
    "Abu Dhabi 5": {
        "bbox": (24.4298, 54.5977, 24.5758, 54.7531),
        "cell_size_km": 5.0,
    },
    "Abu Dhabi 6": {
        "bbox": (24.5763, 54.6362, 24.7708, 54.8407),
        "cell_size_km": 5.0,
    },
    "Dubai 1 Jebel Ali": {
        "bbox": (24.8057, 54.9243, 25.0471, 55.2925),
        "cell_size_km": 5.0,
    },
    "Dubai 2 Downtown": {
        "bbox": (25.0490, 55.0993, 25.2625, 55.5682),
        "cell_size_km": 5.0,
    },
    "Dubai 3": {
        "bbox": (24.8446, 55.2933, 25.0483, 55.6135),
        "cell_size_km": 5.0,
    },
    "Sharjah Ajman 1": {
        "bbox": (25.2624, 55.2687, 25.4245, 55.7269),
        "cell_size_km": 5.0,
    },
    "Sharjah Ajman 2": {
        "bbox": (25.4246, 55.4486, 25.6337, 55.8319),
        "cell_size_km": 5.0,
    },
    "RAK 1": {
        "bbox": (25.6483, 55.7926, 25.7567, 56.0434),
        "cell_size_km": 5.0,
    },
    "RAK 2": {
        "bbox": (25.7573, 55.9240, 25.8312, 56.0344),
        "cell_size_km": 5.0,
    },
    "RAK 3": {
        "bbox": (25.8310, 55.9776, 25.9018, 56.0686),
        "cell_size_km": 5.0,
    },
    "Al Ain": {
        "bbox": (24.1197, 55.6291, 24.3320, 55.8850),
        "cell_size_km": 5.0,
    },
}

KEYWORDS = [
    "apparel", "library", "bar", "dry cleaning", "museum", "convenience store"
]

# Cost model: $1.50 per 1000 records, 50 records returned per API request
RECORDS_PER_REQUEST = 50
COST_PER_1000_RECORDS = 1.5


def deduplicate(entries):
    """
    Remove near-duplicate points by rounding lat/long to 4 decimal places
    and keeping only the first occurrence of each (lat4, long4, keyword) triple.
    """
    seen = set()
    unique = []
    for e in entries:
        key = (round(e["lat"], 4), round(e["long"], 4), e["keyword"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def build_summary(emirate_counts, total_points, total_requests, estimated_cost):
    lines = [
        "UAE Google Maps Grid Summary",
        "=" * 40,
    ]
    for emirate, count in emirate_counts.items():
        lines.append(f"  {emirate:<20} {count:>6} grid points")
    lines += [
        "-" * 40,
        f"  {'Total grid points':<20} {total_points:>6}",
        f"  {'Total requests':<20} {total_requests:>6}  (grid points × {len(KEYWORDS)} keywords)",
        f"  {'Est. API records':<20} {total_requests * RECORDS_PER_REQUEST:>6}",
        f"  {'Estimated cost':<20} ${estimated_cost:>7.2f}  (${COST_PER_1000_RECORDS}/1000 records)",
    ]
    return "\n".join(lines)


def main():
    all_entries = []
    emirate_counts = {}

    for emirate, cfg in EMIRATES.items():
        min_lat, min_lon, max_lat, max_lon = cfg["bbox"]
        cell_size_km = cfg["cell_size_km"]
        zoom = cfg.get("zoom", 14.5)

        entries = generate_grid(
            min_lat, min_lon, max_lat, max_lon,
            cell_size_km, KEYWORDS, zoom=zoom,
        )
        # Count unique grid points (before dedup, per emirate)
        unique_points = len(entries) // len(KEYWORDS)
        emirate_counts[emirate] = unique_points
        all_entries.extend(entries)

    # Global deduplication — removes overlap between adjacent emirate boxes
    all_entries = deduplicate(all_entries)

    total_requests = len(all_entries)                             # one request per (point, keyword) dict
    total_points = total_requests // len(KEYWORDS) if total_requests else 0
    total_records = total_requests * RECORDS_PER_REQUEST
    estimated_cost = (total_records / 1000) * COST_PER_1000_RECORDS

    summary = build_summary(emirate_counts, total_points, total_requests, estimated_cost)
    print(summary)

    # Save outputs
    os.makedirs("./data", exist_ok=True)

    with open("input_grid.json", "w", encoding="utf-8") as f:
        json.dump(all_entries, f, indent=2)

    with open("grid_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary + "\n")

    print(f"\nSaved {len(all_entries)} entries to input_grid.json")
    print("Saved summary to grid_summary.txt")


if __name__ == "__main__":
    main()
