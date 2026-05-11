import os
import sys
import json
import numpy as np
import faiss
import torch
from tqdm import tqdm

sys.path.insert(0, '/scratch/jy4017/Geolocation/models/Qwen3-VL-Embedding')
from src.models.qwen3_vl_embedding import Qwen3VLEmbedder

# ---- CONFIG ----
IMAGE_DIRS = [
    '/scratch/jy4017/Geolocation/data/HPCimagesAE/imagesAE',
    '/scratch/jy4017/Geolocation/data/HPCimagesgulf/imagesgulf',
]
JSON_RESULTS_DIR = '/scratch/jy4017/Geolocation/data/jsonresults'
MODEL_PATH       = '/scratch/jy4017/Geolocation/models/Model-Qwen3-VL-Embedding-2B'
OUTPUT_DIR       = '/scratch/jy4017/Geolocation/faiss_index'
BATCH_SIZE       = 64
EMBEDDING_DIM    = 2048

os.makedirs(OUTPUT_DIR, exist_ok=True)


def is_jpeg(filepath):
    """
    Check if a file is a JPEG by reading its first 3 bytes.
    JPEG files always start with FF D8 FF regardless of extension.
    This handles the files that have no .jpg extension.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(3)
            return header == b'\xff\xd8\xff'
    except Exception:
        return False


def extract_place_id(filename):
    """
    Extract place_id from filename.
    Filenames follow the pattern: {place_id}_{image_number}.jpg
    or {place_id}_{image_number} (no extension)
    Example: ChIJg5TIvt5pXj4RHq5foQ1SwxU_0.jpg -> ChIJg5TIvt5pXj4RHq5foQ1SwxU
    """
    # remove extension if present
    name = os.path.splitext(filename)[0]
    # split on underscore, place_id is everything except the last part
    parts = name.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return name  # fallback: return full name if pattern doesn't match


# ---- BUILD GPS LOOKUP FROM JSON RESULTS ----
# load all JSON result files and build a place_id -> (lat, lon) lookup
print('Building GPS lookup from JSON results...')
gps_lookup = {}

for json_file in os.listdir(JSON_RESULTS_DIR):
    if not json_file.endswith('.json'):
        continue
    filepath = os.path.join(JSON_RESULTS_DIR, json_file)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            records = json.load(f)
        if not isinstance(records, list):
            records = [records]
        for record in records:
            place_id = record.get('place_id') or record.get('fid') or record.get('fid_location')
            lat      = record.get('lat') 
            lon      = record.get('lon') 
            if place_id and lat and lon:
                gps_lookup[place_id] = (float(lat), float(lon))
    except Exception as e:
        print(f'Warning: could not read {json_file}: {e}')

print(f'GPS lookup built: {len(gps_lookup)} places with coordinates')


# ---- SCAN IMAGE FOLDERS ----
print('Scanning image folders...')
gallery = []

for folder in IMAGE_DIRS:
    region = 'AE' if 'AE' in folder else 'gulf'
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)

        # check if file is a JPEG — either by extension or by file header
        has_jpg_ext = filename.lower().endswith(('.jpg', '.jpeg'))
        if not has_jpg_ext and not is_jpeg(filepath):
            continue  # skip non-JPEG files

        # extract place_id from filename to look up GPS
        place_id = extract_place_id(filename)
        lat, lon = gps_lookup.get(place_id, (None, None))

        gallery.append({
            'image_path': filepath,
            'place_id':   place_id,
            'region':     region,
            'lat':        lat,
            'lon':        lon,
        })

print(f'Total valid images: {len(gallery)}')
matched = sum(1 for g in gallery if g['lat'] is not None)
print(f'Images with GPS coordinates: {matched}/{len(gallery)}')

# ---- TEST MODE ----
# REMOVE THIS LINE for the full run
#gallery = gallery[:100]
print(f'Running on {len(gallery)} images (test mode)')

# ---- LOAD MODEL ----
print('Loading Qwen3-VL-Embedding-2B...')
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

model = Qwen3VLEmbedder(
    model_name_or_path=MODEL_PATH,
    torch_dtype=torch.bfloat16 if device.type == 'cuda' else torch.float32,
    #attn_implementation='flash_attention_2'  # uncomment for GPU run
)

# ---- GENERATE EMBEDDINGS ----
print('Generating embeddings...')
all_embeddings = []

for i in tqdm(range(0, len(gallery), BATCH_SIZE), desc='Embedding batches'):
    batch = gallery[i:i + BATCH_SIZE]
    inputs = [{"image": item['image_path']} for item in batch]

    with torch.no_grad():
        embeddings = model.process(inputs)

    all_embeddings.append(embeddings.cpu().float().numpy().astype('float32'))

    # save partial checkpoint every 1000 batches
    if i % (BATCH_SIZE * 1000) == 0 and i > 0:
        partial = np.vstack(all_embeddings)
        np.save(f'{OUTPUT_DIR}/embeddings_partial_{i}.npy', partial)
        print(f'Checkpoint saved at batch {i}')

all_embeddings = np.vstack(all_embeddings)
print(f'Embeddings shape: {all_embeddings.shape}')

# ---- SAVE ----
print('Saving embeddings and metadata...')
np.save(f'{OUTPUT_DIR}/embeddings.npy', all_embeddings)

metadata = [
    {
        'index':      i,
        'image_path': gallery[i]['image_path'],
        'place_id':   gallery[i]['place_id'],
        'lat':        gallery[i]['lat'],
        'lon':        gallery[i]['lon'],
        'region':     gallery[i]['region'],
    }
    for i in range(len(gallery))
]
with open(f'{OUTPUT_DIR}/metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

# ---- BUILD FAISS INDEX ----
print('Building FAISS index...')
faiss.normalize_L2(all_embeddings)
index = faiss.IndexFlatIP(EMBEDDING_DIM)
index.add(all_embeddings)
faiss.write_index(index, f'{OUTPUT_DIR}/vector_db.index')

print(f'\nDone. Saved to {OUTPUT_DIR}/')
print(f'  vector_db.index — {index.ntotal} vectors')
print(f'  metadata.json   — {len(metadata)} entries')
print(f'  embeddings.npy  — backup')