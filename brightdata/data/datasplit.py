import json
import random
import os
import shutil

# load all image paths from both folders into separate lists
ae_images = []
gulf_images = []

for img_file in os.listdir('images/imagesAE'):
    ae_images.append(f'images/imagesAE/{img_file}')

for img_file in os.listdir('images/imagesgulf'):
    gulf_images.append(f'images/imagesgulf/{img_file}')

print(f'AE images: {len(ae_images)} | Gulf images: {len(gulf_images)}')

# shuffle each list separately
random.shuffle(ae_images)
random.shuffle(gulf_images)

# take 5000 from each for test set
test_set = ae_images[:5000] + gulf_images[:5000]

# rest goes to train set
train_set = ae_images[5000:] + gulf_images[5000:]

print(f'Test: {len(test_set)} | Train: {len(train_set)}')


test_dir = './test_set'
train_dir = './train_set'

for folder in [
    os.path.join(test_dir, 'imagesAE'),
    os.path.join(test_dir, 'imagesgulf'),
    os.path.join(train_dir, 'imagesAE'),
    os.path.join(train_dir, 'imagesgulf'),
]:
    os.makedirs(folder, exist_ok=True)

def copy_images(image_paths, output_root):
    for image_path in image_paths:
        region = 'imagesAE' if 'imagesAE' in image_path else 'imagesgulf'
        destination = os.path.join(output_root, region, os.path.basename(image_path))
        shutil.copy2(image_path, destination)


copy_images(test_set, test_dir)
copy_images(train_set, train_dir)

print(f'Saved test images to {test_dir}')
print(f'Saved train images to {train_dir}')