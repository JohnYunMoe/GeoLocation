import os
import sys
import json
import torch
import faiss
import numpy as np
import re
import math
import datetime

sys.path.insert(0, '/scratch/jy4017/Geolocation/models/Qwen3-VL-Embedding')
from src.models.qwen3_vl_embedding import Qwen3VLEmbedder
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

# ---- CONFIG ----
INDEX_PATH    = '/scratch/jy4017/Geolocation/faiss_index/vector_db_test.index'
METADATA_PATH = '/scratch/jy4017/Geolocation/faiss_index/metadata_test.json'
EMBEDDER_PATH = '/scratch/jy4017/Geolocation/models/Model-Qwen3-VL-Embedding-2B'
VLM_PATH      = '/scratch/jy4017/Geolocation/models/Qwen3-VL-8B-Thinking'
TEST_DIR      = '/scratch/jy4017/Geolocation/data/test_set'
LOG_PATH      = '/scratch/jy4017/Geolocation/logs/output_log.txt'
EMBEDDING_DIM = 2048
TOP_K         = 5

# ---- LOGGING HELPER ----
def log(msg, also_print=True):
    """Write a message to both the log file and stdout."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}'
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    if also_print:
        print(line)

# ---- LOAD INDEX ----
log('Loading FAISS index...')
index = faiss.read_index(INDEX_PATH)
with open(METADATA_PATH) as f:
    metadata = json.load(f)
log(f'Index loaded: {index.ntotal} vectors')

# ---- LOAD 2B EMBEDDING MODEL ----
log('Loading Qwen3-VL-Embedding-2B (retrieval)...')
device   = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
log(f'Device: {device}')
embedder = Qwen3VLEmbedder(
    model_name_or_path=EMBEDDER_PATH,
    dtype=torch.bfloat16 if device.type == 'cuda' else torch.float32,
)

# ---- LOAD 8B THINKING VLM ----
log('Loading Qwen3-VL-8B-Thinking (reasoning)...')
vlm       = Qwen3VLForConditionalGeneration.from_pretrained(
    VLM_PATH,
    dtype='auto',
    device_map='auto',
)
processor = AutoProcessor.from_pretrained(VLM_PATH)
log('Both models loaded successfully.')


def retrieve_similar(query_image_path, top_k=TOP_K):
    """
    Use the 2B embedding model to embed the query image
    and retrieve the top-k most similar images from the FAISS index.
    """
    with torch.no_grad():
        embedding = embedder.process([{"image": query_image_path}])

    query_vec = embedding.cpu().float().numpy().astype('float32')
    faiss.normalize_L2(query_vec)

    distances, indices = index.search(query_vec, k=top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        match = metadata[idx]
        results.append({
            'similarity': float(dist),
            'lat':        match['lat'],
            'lon':        match['lon'],
            'image_path': match['image_path'],
            'place_id':   match['place_id'],
            'region':     match['region'],
        })
    return results


def reason_about_location(query_image_path, retrieved):
    """
    Use the 8B thinking model to reason about location.
    Returns the chain-of-thought thinking block and the final answer separately.
    """
    context_lines = []
    for i, r in enumerate(retrieved):
        context_lines.append(
            f"  Match {i+1}: similarity={r['similarity']:.3f} | "
            f"GPS=({r['lat']:.4f}, {r['lon']:.4f}) | "
            f"region={r['region']}"
        )
    context = '\n'.join(context_lines)

    prompt = f"""You are a geolocation expert specializing in indoor spaces across the UAE and Arab countries.

I have an indoor photo. I searched a database of geo-tagged indoor images using a 
visual embedding model and found these visually similar matches:

{context}

Carefully examine the image and reason step by step:
1. What type of venue is this? (restaurant, cafe, hotel, mall, mosque, hospital, etc.)
2. What visual cues suggest a specific country or city? Consider:
   - Interior design style and materials
   - Arabic/English signage language and style
   - Architectural elements characteristic of specific UAE emirates or Arab countries
   - Lighting, furniture, decor patterns
3. How do the retrieved GPS coordinates cluster? Do they agree or disagree?
4. What is your final predicted location?

Provide your answer in this format:
- Predicted GPS: (lat, lon)
- Country: 
- City/Emirate:
- Venue type:
- Confidence: high / medium / low
- Key evidence:"""

    messages = [
        {
            'role': 'user',
            'content': [
                {'type': 'image', 'image': query_image_path},
                {'type': 'text',  'text': prompt}
            ]
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors='pt'
    )
    inputs = inputs.to(vlm.device)

    with torch.no_grad():
        generated_ids = vlm.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=True,
            temperature=1.0,
            top_p=0.95,
            top_k=20,
            repetition_penalty=1.0,
        )

    generated_ids_trimmed = [
        out_ids[len(in_ids):]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]

    full_output = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]

    thinking_match = re.search(r'<think>(.*?)</think>', full_output, re.DOTALL)
    thinking     = thinking_match.group(1).strip() if thinking_match else ''
    final_answer = re.sub(r'<think>.*?</think>', '', full_output, flags=re.DOTALL).strip()

    return thinking, final_answer


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def extract_place_id(filename):
    """Extract place_id from filename pattern: {place_id}_{number}.jpg"""
    name = os.path.splitext(filename)[0]
    parts = name.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return name


# ---- MAIN ----
if __name__ == '__main__':

    # write a header to the log file
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        f.write(f'=== Reasoning Pipeline Output Log ===\n')
        f.write(f'Started: {datetime.datetime.now()}\n')
        f.write(f'Test folder: {TEST_DIR}\n')
        f.write(f'Index: {INDEX_PATH}\n')
        f.write(f'{"="*60}\n\n')

    # scan test folder for all jpg images
    test_images = sorted([
        f for f in os.listdir(TEST_DIR)
        if f.lower().endswith(('.jpg', '.jpeg'))
    ])

    log(f'Found {len(test_images)} images in test folder')

    errors_km = []

    for i, filename in enumerate(test_images):
        image_path = os.path.join(TEST_DIR, filename)

        log(f'\n{"="*60}')
        log(f'[{i+1}/{len(test_images)}] {filename}')

        try:
            # Step 1+2 — retrieve similar images
            retrieved = retrieve_similar(image_path)

            log('Retrieved matches:')
            for r in retrieved:
                log(f"  sim={r['similarity']:.4f} | GPS=({r['lat']:.4f}, {r['lon']:.4f}) | region={r['region']}")

            # Step 3 — VLM reasoning
            log('Reasoning with Qwen3-VL-8B-Thinking...')
            thinking, answer = reason_about_location(image_path, retrieved)

            # log chain of thought (truncated to 500 chars to keep log readable)
            log('\n--- CHAIN OF THOUGHT (first 500 chars) ---')
            log(thinking[:500] + '...' if len(thinking) > 500 else thinking)

            log('\n--- FINAL PREDICTION ---')
            log(answer)

        except Exception as e:
            log(f'ERROR processing {filename}: {e}')
            continue

    # write summary footer
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'\n{"="*60}\n')
        f.write(f'Finished: {datetime.datetime.now()}\n')
        f.write(f'Total images processed: {len(test_images)}\n')

    log(f'\nDone. Results saved to {LOG_PATH}')