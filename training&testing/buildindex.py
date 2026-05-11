import os
import sys
import json
import numpy as np
import faiss
import torch
from tqdm import tqdm

# import the official embedder from the cloned repo
sys.path.append('/scratch/jy4017/Geolocation/Qwen3-VL-Embedding')
from src.models.qwen3_vl_embedding import Qwen3VLEmbedder

# ---- CONFIG ----
GALLERY_JSON   = '/scratch/jy4017/Geolocation/data/gallery_set.json'
MODEL_PATH     = '/scratch/jy4017/Geolocation/models/Qwen3-VL-Embedding-2B'
OUTPUT_DIR     = '/scratch/jy4017/Geolocation/faiss_index'
BATCH_SIZE     = 32   # reduce to 8 if out of memory
EMBEDDING_DIM  = 2048 # Qwen3-VL-Embedding-2B outputs 2048-dimensional vectors

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- LOAD DATA ----
print('Loading gallery set...')
with open(GALLERY_JSON, 'r') as f:
    gallery = json.load(f)

gallery = gallery[:100]  # for testing — remove this line to process the full dataset of 428,985 images
# filter to images that actually exist on disk
gallery = [g for g in gallery if os.path.exists(g['image_path'])]
print(f'Valid gallery images: {len(gallery)}')

# ---- LOAD MODEL ----
print('Loading Qwen3-VL-Embedding-2B...')
model = Qwen3VLEmbedder(
    model_name_or_path=MODEL_PATH,
    torch_dtype=torch.bfloat16,
    attn_implementation='flash_attention_2'
)

# ---- GENERATE EMBEDDINGS IN BATCHES ----
print('Generating embeddings...')
all_embeddings = []

for i in tqdm(range(0, len(gallery), BATCH_SIZE), desc='Embedding batches'):
    batch = gallery[i:i+BATCH_SIZE]

    # format each image for the model
    inputs = [{"image": item['image_path']} for item in batch]

    # get embeddings — returns a tensor of shape (batch_size, 2048)
    with torch.no_grad():
        embeddings = model.process(inputs)

    # convert to numpy and store
    all_embeddings.append(embeddings.cpu().numpy().astype('float32'))

    # save progress every 1000 batches in case of crashes
    if i % (BATCH_SIZE * 1000) == 0 and i > 0:
        partial = np.vstack(all_embeddings)
        np.save(f'{OUTPUT_DIR}/embeddings_partial_{i}.npy', partial)
        print(f'Saved partial embeddings at batch {i}')

# stack all batches into one big array
# shape will be (428985, 2048)
all_embeddings = np.vstack(all_embeddings)
print(f'All embeddings shape: {all_embeddings.shape}')

# ---- SAVE EMBEDDINGS AND METADATA ----
print('Saving embeddings and metadata...')

# save raw embeddings as numpy file (backup)
np.save(f'{OUTPUT_DIR}/embeddings.npy', all_embeddings)

# save metadata — maps each index position back to image path and GPS
metadata = [
    {
        'index': i,
        'image_path': gallery[i]['image_path'],
        'lat': gallery[i].get('lat'),
        'lon': gallery[i].get('lon'),
        'region': gallery[i].get('region', '')
    }
    for i in range(len(gallery))
]
with open(f'{OUTPUT_DIR}/metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

# ---- BUILD FAISS INDEX ----
print('Building FAISS index...')

# normalize embeddings to unit length
# this makes cosine similarity equivalent to dot product
faiss.normalize_L2(all_embeddings)

# IndexFlatIP = Inner Product (cosine similarity after normalization)
# this is the most accurate index type — no approximation
index = faiss.IndexFlatIP(EMBEDDING_DIM)

# add all embeddings to the index
index.add(all_embeddings)

print(f'FAISS index contains {index.ntotal} vectors')

# save the index to disk
faiss.write_index(index, f'{OUTPUT_DIR}/vector_db.index')

print(f'Done. Files saved to {OUTPUT_DIR}/')
print(f'  - vector_db.index  ({index.ntotal} vectors)')
print(f'  - metadata.json    ({len(metadata)} entries)')
print(f'  - embeddings.npy   (backup)')