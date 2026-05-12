import numpy as np
import faiss
import json
import os

# ---- CONFIG ----
PARTIAL_NPY  = '/scratch/jy4017/Geolocation/faiss_index/embeddings_partial_128000.npy'
IMAGE_DIRS   = [
    '/scratch/jy4017/Geolocation/data/HPCimagesAE/imagesAE',
    '/scratch/jy4017/Geolocation/data/HPCimagesgulf/imagesgulf',
]
JSON_DIR     = '/scratch/jy4017/Geolocation/data/jsonresults'
OUTPUT_DIR   = '/scratch/jy4017/Geolocation/faiss_index'
EMBEDDING_DIM = 2048
TEST_SIZE    = 128000  # how many to use for the test index

# ---- REBUILD GPS LOOKUP ----
print('Building GPS lookup...')
gps_lookup = {}
for json_file in os.listdir(JSON_DIR):
    if not json_file.endswith('.json'):
        continue
    try:
        with open(os.path.join(JSON_DIR, json_file), 'r', encoding='utf-8') as f:
            records = json.load(f)
        if not isinstance(records, list):
            records = [records]
        for record in records:
            place_id = record.get('place_id') or record.get('fid') or record.get('fid_location')
            lat = record.get('lat') or record.get('latitude')
            lon = record.get('lon') or record.get('long') or record.get('longitude')
            if place_id and lat and lon:
                gps_lookup[place_id] = (float(lat), float(lon))
    except Exception as e:
        print(f'Warning: {json_file}: {e}')
print(f'GPS lookup: {len(gps_lookup)} places')

# ---- REBUILD GALLERY LIST IN SAME ORDER AS buildindex.py ----
# this must match the exact same logic as buildindex.py so order is identical
def is_jpeg(filepath):
    try:
        with open(filepath, 'rb') as f:
            return f.read(3) == b'\xff\xd8\xff'
    except Exception:
        return False

def extract_place_id(filename):
    name = os.path.splitext(filename)[0]
    parts = name.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return name

print('Scanning image folders in same order as buildindex.py...')
gallery = []
for folder in IMAGE_DIRS:
    region = 'AE' if 'AE' in folder else 'gulf'
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        has_jpg_ext = filename.lower().endswith(('.jpg', '.jpeg'))
        if not has_jpg_ext and not is_jpeg(filepath):
            continue
        place_id = extract_place_id(filename)
        lat, lon = gps_lookup.get(place_id, (None, None))
        gallery.append({
            'image_path': filepath,
            'place_id':   place_id,
            'region':     region,
            'lat':        lat,
            'lon':        lon,
        })

print(f'Total gallery entries: {len(gallery)}')

# ---- LOAD PARTIAL EMBEDDINGS ----
print('Loading partial embeddings...')
embeddings = np.load(PARTIAL_NPY)
print(f'Partial embeddings shape: {embeddings.shape}')

# make sure we don't request more than what's in the partial file
n = min(embeddings.shape[0], len(gallery))
embeddings = embeddings[:n].copy()
metadata   = gallery[:n]

print(f'Using first {n} entries')

# ---- BUILD FAISS INDEX ----
print('Building FAISS index...')
faiss.normalize_L2(embeddings)
index = faiss.IndexFlatIP(EMBEDDING_DIM)
index.add(embeddings)
print(f'Index contains {index.ntotal} vectors')

# ---- SAVE ----
faiss.write_index(index, f'{OUTPUT_DIR}/vector_db_test.index')
with open(f'{OUTPUT_DIR}/metadata_test.json', 'w') as f:
    json.dump(metadata, f, indent=2)

# quick sanity check
gps_count = sum(1 for m in metadata if m['lat'] is not None)
print(f'GPS coverage: {gps_count}/{n}')
print(f'Saved vector_db_test.index and metadata_test.json')