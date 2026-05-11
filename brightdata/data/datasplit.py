import random
import os
import shutil

BASE_DIR = '/scratch/jy4017/Geolocation/data'
AE_DIR = os.path.join(BASE_DIR, 'HPCimagesAE/imagesAE')
GULF_DIR = os.path.join(BASE_DIR, 'HPCimagesgulf/imagesgulf')
TEST_DIR = os.path.join(BASE_DIR, 'test_set')
TRAIN_DIR = os.path.join(BASE_DIR, 'train_set')

# load all image paths from both folders into separate lists
ae_images = []
gulf_images = []

for img_file in os.listdir(AE_DIR):
    ae_images.append(os.path.join(AE_DIR, img_file))

for img_file in os.listdir(GULF_DIR):
    gulf_images.append(os.path.join(GULF_DIR, img_file))

print(f'AE images: {len(ae_images)} | Gulf images: {len(gulf_images)}')

# shuffle each list separately
random.shuffle(ae_images)
random.shuffle(gulf_images)

# take 5000 from each for test set
test_set = ae_images[:5000] + gulf_images[:5000]

# rest goes to train set
train_set = ae_images[5000:] + gulf_images[5000:]

print(f'Test: {len(test_set)} | Train: {len(train_set)}')

os.makedirs(TEST_DIR, exist_ok=True)
os.makedirs(TRAIN_DIR, exist_ok=True)

def copy_images(image_paths, output_root):
    for image_path in image_paths:
        destination = os.path.join(output_root, os.path.basename(image_path))
        shutil.copy2(image_path, destination)


copy_images(test_set, TEST_DIR)
copy_images(train_set, TRAIN_DIR)

print(f'Saved test images to {TEST_DIR}')
print(f'Saved train images to {TRAIN_DIR}')