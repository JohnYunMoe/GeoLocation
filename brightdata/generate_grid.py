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
    # Iraq - Basra region
    "Basra": {
        "bbox": (30.4104, 47.6750, 30.6049, 48.0189),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al-Midaina": {
        "bbox": (30.8959, 47.2265, 30.9683, 47.3320),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al Qurna 1": {
        "bbox": (30.9809, 47.4142, 31.0371, 47.4544),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al Qurna 2": {
        "bbox": (30.9426, 47.4453, 30.9799, 47.4750),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al Howair": {
        "bbox": (30.9704, 47.2991, 30.9936, 47.3592),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Nasiriyah": {
        "bbox": (30.9989, 46.1961, 31.0936, 46.3264),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "As Samawah 1": {
        "bbox": (31.2699, 45.2450, 31.3226, 45.3148),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "As Samawah 2": {
        "bbox": (31.3257, 45.2563, 31.3595, 45.3064),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al-Najaf": {
        "bbox": (31.9880, 44.2641, 32.1154, 44.4283),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al Hillah": {
        "bbox": (32.4321, 44.3902, 32.5174, 44.4804),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Karbala": {
        "bbox": (32.5501, 43.9470, 32.6555, 44.1072),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Hindiya": {
        "bbox": (32.5322, 44.2043, 32.5642, 44.2806),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Al-Kut": {
        "bbox": (32.4681, 45.7768, 32.5513, 45.8861),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Amarah": {
        "bbox": (31.8088, 47.1085, 31.8854, 47.1937),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },

    # Iraq - Baghdad region
    "Baghdad": {
        "bbox": (33.1715, 44.1793, 33.4613, 44.6467),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },
    "Baqubah": {
        "bbox": (33.7083, 44.5788, 33.7695, 44.6862),
        "cell_size_km": 4.0,
        "country": "Iraq",
    },

    # Yemen
    "Sana'a": {
        "bbox": (15.2645, 44.1115, 15.4500, 44.3016),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Dhamar": {
        "bbox": (14.5045, 44.3666, 14.5825, 44.4380),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Hodeidah": {
        "bbox": (14.7678, 42.9270, 14.8346, 43.0021),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Ibb": {
        "bbox": (13.9307, 44.1273, 13.9875, 44.1965),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Ta'izz": {
        "bbox": (13.5540, 43.9857, 13.6004, 44.0593),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Ataq": {
        "bbox": (14.4980, 46.8166, 14.5479, 46.9005),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },
    "Sa'dah": {
        "bbox": (16.9262, 43.7485, 16.9544, 43.7783),
        "cell_size_km": 4.0,
        "country": "Yemen",
    },

    # Saudi Arabia
    "Jizan": {
        "bbox": (16.8441, 42.5450, 16.9414, 42.6230),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",  # ⚠️ mislabeled as Yemen in GeoJSON — Jizan is in Saudi Arabia
    },
    "Salhabah": {
        "bbox": (17.1437, 42.6111, 17.1778, 42.6880),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",  # ⚠️ mislabeled as Yemen in GeoJSON — coordinates place this in Saudi Arabia
    },
    "Khamis Mushayt": {
        "bbox": (18.2473, 42.6700, 18.3852, 42.7995),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",  # ⚠️ mislabeled as Yemen in GeoJSON — Khamis Mushayt is in Saudi Arabia
    },
    "Jeddah": {
        "bbox": (21.4202, 39.0981, 21.7505, 39.3701),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",
    },
    "Medina": {
        "bbox": (24.3730, 39.4501, 24.5590, 39.7495),
        "cell_size_km": 4.0,
        "country": "Saudi Arabia",
    },

    # Egypt
    "Cairo": {
        "bbox": (29.8781, 31.0819, 30.1674, 31.6908),
        "cell_size_km": 4.0,
        "country": "Egypt",
    },
    "Alexandria 1": {
        "bbox": (31.1786, 29.8774, 31.2087, 29.9536),
        "cell_size_km": 4.0,
        "country": "Egypt",
    },
    "Alexandria 2": {
        "bbox": (31.2198, 29.9678, 31.2480, 30.0048),
        "cell_size_km": 4.0,
        "country": "Egypt",
    },
    "Alexandria 3": {
        "bbox": (31.2549, 29.9880, 31.2699, 30.0240),
        "cell_size_km": 4.0,
        "country": "Egypt",
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
