import json
import random
import os

# load all image paths from both folders
all_images = []

for img_file in os.listdir('./data/images/imagesAE'):
    all_images.append({
        'image_path': f'./data/images/imagesAE/{img_file}',
        'region': 'AE'
    })

for img_file in os.listdir('./data/images/imagesgulf'):
    all_images.append({
        'image_path': f'./data/images/imagesgulf/{img_file}',
        'region': 'gulf'
    })

print(f'Total images: {len(all_images)}')

random.shuffle(all_images)

test_set    = all_images[:10000]
gallery_set = all_images[10000:]

with open('./data/test_set.json', 'w') as f:
    json.dump(test_set, f, indent=2)

with open('./data/gallery_set.json', 'w') as f:
    json.dump(gallery_set, f, indent=2)

print(f'Test: {len(test_set)} | Gallery: {len(gallery_set)}')