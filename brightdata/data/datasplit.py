import json
import random
import os

# load all image paths from both folders into separate lists
ae_images = []
gulf_images = []

for img_file in os.listdir('images/imagesAE'):
    ae_images.append(f'images/imagesAE/{img_file}')

for img_file in os.listdir('./data/images/imagesgulf'):
    gulf_images.append(f'./data/images/imagesgulf/{img_file}')

print(f'AE images: {len(ae_images)} | Gulf images: {len(gulf_images)}')

# shuffle each list separately
random.shuffle(ae_images)
random.shuffle(gulf_images)

# take 5000 from each for test set
test_set = ae_images[:5000] + gulf_images[:5000]

# rest goes to train set
train_set = ae_images[5000:] + gulf_images[5000:]

print(f'Test: {len(test_set)} | Train: {len(train_set)}')

with open('./data/test_set.json', 'w') as f:
    json.dump(test_set, f, indent=2)

with open('./data/train_set.json', 'w') as f:
    json.dump(train_set, f, indent=2)