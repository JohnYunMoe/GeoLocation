import json
import math
import os


def generate_grid(min_lat, min_lon, max_lat, max_lon, cell_size_km, keywords, country, zoom=14.5):
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
# Gulf region bounding boxes with country tags
# ---------------------------------------------------------------------------
LOCATIONS = {
    # Oman - Muscat
    "Muscat": {
        "bbox": (23.5321, 58.4785, 23.6239, 58.6062),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Bawshar 1": {
        "bbox": (23.5314, 58.3645, 23.6034, 58.4652),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Bawshar 2": {
        "bbox": (23.5253, 58.2352, 23.6124, 58.3538),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Bawshar 3": {
        "bbox": (23.5158, 58.0325, 23.7079, 58.1573),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Bawshar 4": {
        "bbox": (23.5210, 58.1685, 23.6826, 58.2213),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Bawshar 5": {
        "bbox": (23.6186, 57.7906, 23.7169, 58.0172),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Bawshar 6": {
        "bbox": (23.6574, 57.5428, 23.7804, 57.7763),
        "cell_size_km": 5.0,
        "country": "Oman",
    },

    # Oman - Sohar
    "Sohar 1": {
        "bbox": (24.3168, 56.7025, 24.3747, 56.7736),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Sohar 2": {
        "bbox": (24.2766, 56.7587, 24.3072, 56.7944),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Sohar 3": {
        "bbox": (24.3669, 56.6077, 24.4547, 56.6626),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Sohar 4": {
        "bbox": (24.3793, 56.6683, 24.4248, 56.7358),
        "cell_size_km": 5.0,
        "country": "Oman",
    },

    # Oman - Salalah
    "Salalah 1": {
        "bbox": (17.0105, 54.1378, 17.1123, 54.2284),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Salalah 2": {
        "bbox": (16.9998, 54.0705, 17.0961, 54.1333),
        "cell_size_km": 5.0,
        "country": "Oman",
    },
    "Salalah 3": {
        "bbox": (16.9923, 53.9956, 17.0575, 54.0638),
        "cell_size_km": 5.0,
        "country": "Oman",
    },

    # Qatar - Doha
    "Doha 1": {
        "bbox": (24.9411, 51.3530, 25.2907, 51.6217),
        "cell_size_km": 5.0,
        "country": "Qatar",
    },
    "Doha 2": {
        "bbox": (25.3011, 51.3416, 25.4869, 51.5699),
        "cell_size_km": 5.0,
        "country": "Qatar",
    },

    # Bahrain
    "Bahrain 1": {
        "bbox": (26.1967, 50.5286, 26.2437, 50.6203),
        "cell_size_km": 5.0,
        "country": "Bahrain",
    },
    "Bahrain 2": {
        "bbox": (26.2484, 50.5839, 26.2941, 50.6887),
        "cell_size_km": 5.0,
        "country": "Bahrain",
    },
    "Bahrain 3": {
        "bbox": (26.0772, 50.4536, 26.1768, 50.6559),
        "cell_size_km": 5.0,
        "country": "Bahrain",
    },

    # Saudi Arabia - Riyadh
    "Riyadh": {
        "bbox": (24.4492, 46.5052, 24.9884, 46.9602),
        "cell_size_km": 5.0,
        "country": "Saudi Arabia",
    },

    # Saudi Arabia - Dammam
    "Dammam": {
        "bbox": (26.1549, 49.9658, 26.5825, 50.2255),
        "cell_size_km": 5.0,
        "country": "Saudi Arabia",
    },

    # Kuwait
    "Kuwait 1": {
        "bbox": (29.0746, 47.9731, 29.3790, 48.1427),
        "cell_size_km": 5.0,
        "country": "Kuwait",
    },
    "Kuwait 2": {
        "bbox": (29.2033, 47.6624, 29.3516, 47.9619),
        "cell_size_km": 5.0,
        "country": "Kuwait",
    },
}

KEYWORDS = [
    "restaurant", "cafe", "hotel", "mall", "gym",
    "hospital", "mosque", "spa", "cinema", "bakery", "clothes",
    "library", "bar", "dry cleaning", "museum", "convenience store"
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
        "Gulf Region Google Maps Grid Summary",
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

    for emirate, cfg in LOCATIONS.items():
        min_lat, min_lon, max_lat, max_lon = cfg["bbox"]
        cell_size_km = cfg["cell_size_km"]
        zoom = cfg.get("zoom", 14.5)
        country = cfg["country"]

        entries = generate_grid(
            min_lat, min_lon, max_lat, max_lon,
            cell_size_km, KEYWORDS, country, zoom=zoom,
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
