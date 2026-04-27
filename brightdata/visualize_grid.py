import json
import folium
from folium.plugins import MarkerCluster


# ---------------------------------------------------------------------------
# Emirate bounding boxes — same as generate_grid.py, used to label each point
# ---------------------------------------------------------------------------
EMIRATES = {
    "Fujairah":          (25.0133, 56.2273, 25.4341, 56.3748),

    "Abu Dhabi 1":       (24.2072, 54.4324, 24.4285, 54.8095),
    "Abu Dhabi 2":       (24.4099, 54.3244, 24.5121, 54.4286),
    "Abu Dhabi 3":       (24.5168, 54.3968, 24.5433, 54.5308),
    "Abu Dhabi 4":       (24.4295, 54.4295, 24.5148, 54.5973),
    "Abu Dhabi 5":       (24.4298, 54.5977, 24.5758, 54.7531),
    "Abu Dhabi 6":       (24.5763, 54.6362, 24.7708, 54.8407),

    "Dubai 1 Jebel Ali": (24.8057, 54.9243, 25.0471, 55.2925),
    "Dubai 2 Downtown":  (25.0490, 55.0993, 25.2625, 55.5682),
    "Dubai 3":           (24.8446, 55.2933, 25.0483, 55.6135),

    "Sharjah Ajman 1":   (25.2624, 55.2687, 25.4245, 55.7269),
    "Sharjah Ajman 2":   (25.4246, 55.4486, 25.6337, 55.8319),

    "RAK 1":             (25.6483, 55.7926, 25.7567, 56.0434),
    "RAK 2":             (25.7573, 55.9240, 25.8312, 56.0344),
    "RAK 3":             (25.8310, 55.9776, 25.9018, 56.0686),

    "Al Ain":            (24.1197, 55.6291, 24.3320, 55.8850),
}

# Maps each sub-region key to a top-level emirate label used for color + grouping
REGION_TO_EMIRATE = {
    "Dubai 1 Jebel Ali": "Dubai",
    "Dubai 2 Downtown":  "Dubai",
    "Dubai 3":           "Dubai",
    "Abu Dhabi 1":       "Abu Dhabi",
    "Abu Dhabi 2":       "Abu Dhabi",
    "Abu Dhabi 3":       "Abu Dhabi",
    "Abu Dhabi 4":       "Abu Dhabi",
    "Abu Dhabi 5":       "Abu Dhabi",
    "Abu Dhabi 6":       "Abu Dhabi",
    "Al Ain":            "Abu Dhabi",
    "Sharjah Ajman 1":   "Sharjah / Ajman",
    "Sharjah Ajman 2":   "Sharjah / Ajman",
    "RAK 1":             "Ras Al Khaimah",
    "RAK 2":             "Ras Al Khaimah",
    "RAK 3":             "Ras Al Khaimah",
    "Fujairah":          "Fujairah",
}

EMIRATE_COLORS = {
    "Dubai":           "#e63946",   # red
    "Abu Dhabi":       "#2a9d8f",   # teal
    "Sharjah / Ajman": "#e9c46a",   # yellow
    "Ras Al Khaimah":  "#457b9d",   # blue
    "Fujairah":        "#6a4c93",   # purple
    "Unknown":         "#aaaaaa",
}


def classify_point(lat, lon):
    """Return the sub-region key for a coordinate, or 'Unknown' if none match."""
    for region, (min_lat, min_lon, max_lat, max_lon) in EMIRATES.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return region
    return "Unknown"


def load_unique_points(path):
    """Load grid JSON and return deduplicated (lat, lon) pairs with their emirate."""
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)

    seen = set()
    points = []
    for e in entries:
        key = (e["lat"], e["long"])
        if key not in seen:
            seen.add(key)
            points.append({
                "lat": e["lat"],
                "lon": e["long"],
                "emirate": classify_point(e["lat"], e["long"]),
            })
    return points


def build_legend_html(colors):
    """Build an HTML block for a fixed legend overlay on the map."""
    items = "".join(
        f'<div style="margin:3px 0">'
        f'<span style="display:inline-block;width:12px;height:12px;'
        f'border-radius:50%;background:{color};margin-right:6px"></span>'
        f'{emirate}</div>'
        for emirate, color in colors.items()
        if emirate != "Unknown"
    )
    return f"""
    <div style="
        position: fixed; bottom: 40px; left: 40px; z-index: 9999;
        background: white; padding: 10px 14px; border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-family: sans-serif;
        font-size: 13px; line-height: 1.6;
    ">
        <b>Emirates</b><br>{items}
    </div>
    """


def main():
    input_path = "input_grid.json"
    output_path = "grid_map.html"

    print(f"Loading points from {input_path} ...")
    points = load_unique_points(input_path)
    print(f"  {len(points)} unique grid points")

    # Resolve each point's top-level emirate and count for summary
    counts = {}
    for p in points:
        top = REGION_TO_EMIRATE.get(p["emirate"], "Unknown")
        p["top_emirate"] = top
        counts[top] = counts.get(top, 0) + 1
    for emirate, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {emirate:<22} {n:>5} points")

    # Centre the map on the UAE
    uae_center = [24.5, 54.5]
    m = folium.Map(location=uae_center, zoom_start=8, tiles="CartoDB positron")

    # One feature group per top-level emirate for layer toggle
    feature_groups = {}
    for emirate in list(EMIRATE_COLORS.keys()):
        fg = folium.FeatureGroup(name=emirate, show=True)
        feature_groups[emirate] = fg
        m.add_child(fg)

    # Plot each unique grid point as a small circle
    for p in points:
        top = p["top_emirate"]
        color = EMIRATE_COLORS.get(top, EMIRATE_COLORS["Unknown"])
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=0,
            tooltip=f"{p['emirate']} ({p['lat']}, {p['lon']})",
        ).add_to(feature_groups.get(top, feature_groups.get("Unknown")))

    # Layer control (lets you toggle emirates on/off)
    folium.LayerControl(collapsed=False).add_to(m)

    # Legend
    m.get_root().html.add_child(folium.Element(build_legend_html(EMIRATE_COLORS)))

    m.save(output_path)
    print(f"\nMap saved to {output_path} — open it in any browser.")


if __name__ == "__main__":
    main()
