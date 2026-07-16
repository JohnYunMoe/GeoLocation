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
# African Continental region bounding boxes with country tags
# ---------------------------------------------------------------------------
LOCATIONS = {
    # South Africa
    "Cape Town": {
        "bbox": (-34.3988, 18.3113, -33.5589, 19.0864),
        "cell_size_km": 4.0,
        "country": "South Africa",
    },
    "Gqeberha": {
        "bbox": (-34.0103, 25.4730, -33.7792, 25.6889),
        "cell_size_km": 4.0,
        "country": "South Africa",
    },
    "Durban": {
        "bbox": (-30.0807, 30.7252, -29.5642, 31.1731),
        "cell_size_km": 4.0,
        "country": "South Africa",
    },
    "Johannesburg": {
        "bbox": (-26.5773, 27.7439, -25.6138, 28.5117),
        "cell_size_km": 4.0,
        "country": "South Africa",
    },

    # Lesotho
    "Lesotho": {
        "bbox": (-30.5483, 27.2843, -28.6284, 29.3680),
        "cell_size_km": 4.0,
        "country": "Lesotho",
    },

    # Namibia
    "Windhoek": {
        "bbox": (-22.6573, 16.9705, -22.4745, 17.1754),
        "cell_size_km": 4.0,
        "country": "Namibia",
    },

    # Zimbabwe
    "Harare": {
        "bbox": (-18.1000, 30.7722, -17.5866, 31.3611),
        "cell_size_km": 4.0,
        "country": "Zimbabwe",
    },

    # Botswana
    "Gaborone": {
        "bbox": (-24.7369, 25.7762, -24.5358, 26.0330),
        "cell_size_km": 4.0,
        "country": "Botswana",
    },

    # Angola
    "Huambo": {
        "bbox": (-12.8575, 15.6653, -12.7147, 15.8260),
        "cell_size_km": 4.0,
        "country": "Angola",
    },
    "Catumbela": {
        "bbox": (-12.4853, 13.4958, -12.3383, 13.6193),
        "cell_size_km": 4.0,
        "country": "Angola",
    },
    "Luanda": {
        "bbox": (-9.1413, 13.1100, -8.7519, 13.5899),
        "cell_size_km": 4.0,
        "country": "Angola",
    },

    # Mozambique
    "Inhambane": {
        "bbox": (-24.1063, 35.2519, -23.6563, 35.5798),
        "cell_size_km": 4.0,
        "country": "Mozambique",
    },
    "Beira": {
        "bbox": (-19.8614, 34.7624, -19.6969, 34.9506),
        "cell_size_km": 4.0,
        "country": "Mozambique",
    },

    # Malawi
    "Blantyre": {
        "bbox": (-15.8809, 34.9207, -15.6848, 35.1296),
        "cell_size_km": 4.0,
        "country": "Malawi",
    },
    "Lilongwe": {
        "bbox": (-14.1077, 33.6963, -13.8825, 33.8757),
        "cell_size_km": 4.0,
        "country": "Malawi",
    },

    # Tanzania
    "Dar es Salaam": {
        "bbox": (-7.0871, 39.0040, -6.5475, 39.4579),
        "cell_size_km": 4.0,
        "country": "Tanzania",
    },
    "Zanzibar City": {
        "bbox": (-6.2989, 39.1922, -6.0269, 39.2963),
        "cell_size_km": 4.0,
        "country": "Tanzania",
    },

    # Kenya
    "Nairobi": {
        "bbox": (-1.4674, 36.6339, -1.1189, 37.1438),
        "cell_size_km": 4.0,
        "country": "Kenya",
    },
    "Mombasa": {
        "bbox": (-4.1226, 39.5471, -3.9265, 39.7494),
        "cell_size_km": 4.0,
        "country": "Kenya",
    },

    # Uganda
    "Kampala": {
        "bbox": (0.2015, 32.4778, 0.4227, 32.7046),
        "cell_size_km": 4.0,
        "country": "Uganda",
    },

    # DR Congo
    "Kinshasa": {
        "bbox": (-4.4873, 15.1440, -4.1125, 15.5531),
        "cell_size_km": 4.0,
        "country": "DR Congo",
    },
    "Kananga": {
        "bbox": (-5.9292, 22.3698, -5.8643, 22.4537),
        "cell_size_km": 4.0,
        "country": "DR Congo",
    },

    # Morocco
    "Casablanca": {
        "bbox": (33.4514, -7.6804, 33.6246, -7.3923),
        "cell_size_km": 4.0,
        "country": "Morocco",
    },
    "Rabat": {
        "bbox": (33.9252, -6.8740, 34.0681, -6.7042),
        "cell_size_km": 4.0,
        "country": "Morocco",
    },
    "Fez": {
        "bbox": (33.9918, -5.0654, 34.0715, -4.9468),
        "cell_size_km": 4.0,
        "country": "Morocco",
    },

    # Tunisia
    "Tunis": {
        "bbox": (36.6694, 10.0457, 36.9617, 10.3629),
        "cell_size_km": 4.0,
        "country": "Tunisia",
    },

    # Zambia
    "Lusaka": {
        "bbox": (-15.5933, 28.1473, -15.2947, 28.5075),
        "cell_size_km": 4.0,
        "country": "Zambia",
    },

    # Rwanda
    "Kigali": {
        "bbox": (-2.0114, 30.0395, -1.8875, 30.1739),
        "cell_size_km": 4.0,
        "country": "Rwanda",
    },

    # Somalia
    "Mogadishu": {
        "bbox": (1.9698, 45.0988, 2.1983, 45.4946),
        "cell_size_km": 4.0,
        "country": "Somalia",
    },

    # Ethiopia
    "Hawassa": {
        "bbox": (6.9880, 38.4695, 7.1124, 38.5258),
        "cell_size_km": 4.0,
        "country": "Ethiopia",
    },

    # Madagascar
    "Manakara": {
        "bbox": (-22.1925, 47.9768, -22.0988, 48.0269),
        "cell_size_km": 4.0,
        "country": "Madagascar",
    },
    "Tolanaro": {
        "bbox": (-25.0458, 46.9616, -25.0090, 47.0082),
        "cell_size_km": 4.0,
        "country": "Madagascar",
    },

    # Mauritius
    "Mauritius": {
        "bbox": (-20.5788, 57.3259, -20.0061, 57.8603),
        "cell_size_km": 4.0,
        "country": "Mauritius",
    },

    # Cameroon
    "Yaounde": {
        "bbox": (3.7127, 11.3793, 3.9923, 11.6701),
        "cell_size_km": 4.0,
        "country": "Cameroon",
    },

    # Nigeria
    "Lagos": {
        "bbox": (6.3886, 3.1840, 6.6566, 3.6166),
        "cell_size_km": 4.0,
        "country": "Nigeria",
    },

    # Senegal
    "Dakar": {
        "bbox": (14.6286, -17.5817, 14.8560, -17.1377),
        "cell_size_km": 4.0,
        "country": "Senegal",
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
