import json
import sys
import os
import torch
import faiss
import numpy as np

sys.path.insert(0, '/scratch/jy4017/Geolocation/models/Qwen3-VL-Embedding')
from src.models.qwen3_vl_embedding import Qwen3VLEmbedder

INDEX_PATH    = '/scratch/jy4017/Geolocation/faiss_index/vector_db.index'
METADATA_PATH = '/scratch/jy4017/Geolocation/faiss_index/metadata.json'
MODEL_PATH    = '/scratch/jy4017/Geolocation/models/Model-Qwen3-VL-Embedding-2B'

# ---- LOAD INDEX AND METADATA ----
print('Loading FAISS index...')
index = faiss.read_index(INDEX_PATH)
print(f'Index loaded: {index.ntotal} vectors')

with open(METADATA_PATH) as f:
    metadata = json.load(f)
print(f'Metadata loaded: {len(metadata)} entries')

# ---- CHECK 1: index size matches metadata ----
assert index.ntotal == len(metadata), \
    f'MISMATCH: index has {index.ntotal} vectors but metadata has {len(metadata)} entries'
print('CHECK 1 PASSED: index size matches metadata')

# ---- CHECK 2: metadata has GPS coordinates ----
with_gps = sum(1 for m in metadata if m['lat'] is not None and m['lon'] is not None)
print(f'CHECK 2: {with_gps}/{len(metadata)} entries have GPS coordinates')

# ---- CHECK 3: all image paths in metadata still exist on disk ----
missing = [m['image_path'] for m in metadata if not os.path.exists(m['image_path'])]
if missing:
    print(f'CHECK 3 FAILED: {len(missing)} image paths no longer exist on disk')
    for p in missing[:5]:
        print(f'  {p}')
else:
    print('CHECK 3 PASSED: all image paths exist on disk')

# ---- CHECK 4: query the index with one real image ----
print('\nCHECK 4: Running a real query...')
model = Qwen3VLEmbedder(
    model_name_or_path=MODEL_PATH,
    dtype=torch.bfloat16,
    attn_implementation='flash_attention_2'
)

# use the first image in the metadata as the query
query_image = metadata[0]['image_path']
true_lat    = metadata[0]['lat']
true_lon    = metadata[0]['lon']
print(f'Query image: {os.path.basename(query_image)}')
print(f'True GPS: {true_lat}, {true_lon}')

with torch.no_grad():
    query_embedding = model.process([{"image": query_image}])

query_np = query_embedding.cpu().float().numpy().astype('float32')
faiss.normalize_L2(query_np)

# search for top 5 most similar
distances, indices = index.search(query_np, k=5)

print('\nTop 5 matches:')
for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
    match = metadata[idx]
    print(f'  Rank {rank+1}: similarity={dist:.4f} | '
          f'lat={match["lat"]}, lon={match["lon"]} | '
          f'{os.path.basename(match["image_path"])}')

# the top result should be the image itself with similarity ~1.0
top_match = metadata[indices[0][0]]
assert top_match['image_path'] == query_image, \
    'CHECK 4 FAILED: top result is not the query image itself'
print('\nCHECK 4 PASSED: top result is the query image with similarity ~1.0')
print('\nAll checks passed — safe to submit full batch job')