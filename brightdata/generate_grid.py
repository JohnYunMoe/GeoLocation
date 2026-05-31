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
            lon += (4 * lon_step + lon_step)  # add extra steps to reduce overlap between adjacent cells
        lat += (4 * lat_step + lat_step)  # add extra steps to reduce overlap between adjacent cells

    return entries


# ---------------------------------------------------------------------------
# Gulf region bounding boxes with country tags
# ---------------------------------------------------------------------------
LOCATIONS = {
    # Yemen - Aden
    "Aden 1": {
        "bbox": (12.7591, 44.9771, 12.7968, 45.0537),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Aden 2": {
        "bbox": (12.8390, 44.9547, 12.9178, 45.0655),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Aden 3": {
        "bbox": (12.7993, 45.0234, 12.8283, 45.0454),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },

    # Saudi Arabia
    "Mecca": {
        "bbox": (21.3084, 39.6733, 21.5314, 39.9905),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",
    },
    "Tabuk": {
        "bbox": (28.2934, 36.4461, 28.5234, 36.8467),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",
    },
    "Abha": {
        "bbox": (18.1953, 42.4631, 18.2566, 42.5690),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",
    },
    "Hail": {
        "bbox": (27.3862, 41.5368, 27.6802, 41.9579),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",
    },

    # Jordan
    "Amman": {
        "bbox": (31.8010, 35.7572, 32.1106, 36.1360),
        "cell_size_km": 4.0,
        "country": "Jordan",
    },

    # Lebanon
    "Beirut": {
        "bbox": (33.8114, 35.4703, 33.9012, 35.5846),
        "cell_size_km": 4.0,
        "country": "Lebanon",
    },
    "Sidon": {
        "bbox": (33.5268, 35.3713, 33.5657, 35.4216),
        "cell_size_km": 4.0,
        "country": "Lebanon",
    },

    # Israel
    "Tel Aviv": {
        "bbox": (31.8481, 34.7494, 32.1905, 35.0295),
        "cell_size_km": 4.0,
        "country": "Israel",
    },
    "Haifa": {
        "bbox": (32.7682, 34.9595, 32.8317, 35.0831),
        "cell_size_km": 4.0,
        "country": "Israel",
    },
    "Jerusalem": {
        "bbox": (31.6562, 35.1121, 31.8955, 35.3594),
        "cell_size_km": 4.0,
        "country": "Israel",
    },

    # Syria
    "Damascus": {
        "bbox": (33.4227, 36.1554, 33.5908, 36.4363),
        "cell_size_km": 4.0,
        "country": "Syria",
    },

    # Turkey
    "Istanbul": {
        "bbox": (40.8915, 28.7343, 41.1422, 29.3178),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Ankara": {
        "bbox": (39.7364, 32.5590, 40.0826, 33.1621),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Izmir": {
        "bbox": (38.3665, 27.0764, 38.4863, 27.2347),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Antalya": {
        "bbox": (36.8342, 30.5847, 36.9716, 30.8389),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Konya": {
        "bbox": (37.7746, 32.3982, 37.9847, 32.6432),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Denizli": {
        "bbox": (37.7322, 28.9927, 37.8576, 29.1785),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Aydin": {
        "bbox": (37.8126, 27.7984, 37.8637, 27.8887),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Manisa": {
        "bbox": (38.6002, 27.3817, 38.6369, 27.4843),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },
    "Isparta": {
        "bbox": (37.7438, 30.5070, 37.7980, 30.6079),
        "cell_size_km": 4.0,
        "country": "Turkey",
    },

    # Cyprus
    "Cyprus": {
        "bbox": (34.9450, 33.1813, 35.2459, 33.7665),
        "cell_size_km": 4.0,
        "country": "Cyprus",
    },

    # Iran
    "Tehran": {
        "bbox": (35.5745, 51.2361, 35.8091, 51.6090),
        "cell_size_km": 4.0,
        "country": "Iran",
    },
    "Isfahan": {
        "bbox": (32.5877, 51.5807, 32.7354, 51.7821),
        "cell_size_km": 4.0,
        "country": "Iran",
    },
    "Mashhad": {
        "bbox": (36.2110, 59.4597, 36.4018, 59.7376),
        "cell_size_km": 4.0,
        "country": "Iran",
    },
    "Tabriz": {
        "bbox": (38.0090, 46.2243, 38.1258, 46.4018),
        "cell_size_km": 4.0,
        "country": "Iran",
    },
    "Karaj": {
        "bbox": (35.7541, 50.9135, 35.8738, 51.0631),
        "cell_size_km": 4.0,
        "country": "Iran",
    },

    # Tunisia
    "Tunis": {
        "bbox": (36.6780, 10.0965, 36.8759, 10.3660),
        "cell_size_km": 4.0,
        "country": "Tunisia",
    },

    # Morocco
    "Casablanca": {
        "bbox": (33.5035, -7.7112, 33.6140, -7.4351),
        "cell_size_km": 4.0,
        "country": "Morocco",
    },
    "Marrakesh": {
        "bbox": (31.5435, -8.1263, 31.7224, -7.8446),
        "cell_size_km": 4.0,
        "country": "Morocco",
    },
    "Fez": {
        "bbox": (33.9823, -5.0575, 34.0690, -4.9332),
        "cell_size_km": 4.0,
        "country": "Morocco",
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
