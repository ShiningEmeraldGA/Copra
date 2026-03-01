import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
import os

# === SETTINGS ===
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 10
DATASET_PATH = "images\Copra_Pic"

TRAIN_DIR = os.path.join(DATASET_PATH, "Train")     
VAL_DIR   = os.path.join(DATASET_PATH, "Valid")
AUTOTUNE = tf.data.AUTOTUNE

# === LOAD DATASETS ===
train_ds = tf.keras.utils.image_dataset_from_directory(
    TRAIN_DIR,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=True
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    VAL_DIR,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False
)

NUM_CLASSES = len(train_ds.class_names)
print("Classes:", train_ds.class_names)

# === DATA AUGMENTATION (TRAINING ONLY) ===
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.05),
    layers.RandomZoom(0.1),
    layers.RandomBrightness(0.1)
])

# === PREPROCESSING FUNCTION FOR MOBILENETV2 ===
preprocess = tf.keras.applications.mobilenet_v2.preprocess_input

# === APPLY PIPELINE ===
train_ds = train_ds.map(
    lambda x, y: (preprocess(data_augmentation(x)), y),
    num_parallel_calls=AUTOTUNE
)

val_ds = val_ds.map(
    lambda x, y: (preprocess(x), y),
    num_parallel_calls=AUTOTUNE
)

train_ds = train_ds.cache().prefetch(AUTOTUNE)
val_ds = val_ds.cache().prefetch(AUTOTUNE)

# === LOAD PRETRAINED MODEL ===
base_model = MobileNetV2(
    input_shape=IMAGE_SIZE + (3,),
    include_top=False,
    weights="imagenet"
)

base_model.trainable = False

# === BUILD MODEL ===
model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(0.3),
    layers.Dense(NUM_CLASSES, activation="softmax")
])

# === COMPILE ===
model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

# === TRAIN ===
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS
)
 
# === SAVE MODEL ===
model.save("Copra_Test_UpdateV2.h5")
print("🎉 Model saved as TensorFlow SavedModel")

# === CONVERT TO TFLITE ===
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open("Copra_Test_UpdateV2.tflite", "wb") as f:
    f.write(tflite_model)

print("✅ TFLite model saved as 'Copra_Test_UpdateV2.tflite'")
