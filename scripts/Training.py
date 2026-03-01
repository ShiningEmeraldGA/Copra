import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import layers, models
import os

# === SETTINGS ===
image_size = (224, 224)
batch_size = 32
epochs = 10
dataset_path = "images"  # <-- change if needed

# === DATA PREPROCESSING ===
datagen = ImageDataGenerator(rescale=1./255)

train_data = datagen.flow_from_directory(
    os.path.join(dataset_path, 'Copra Pics'),
    target_size=image_size,
    batch_size=batch_size,
    class_mode='categorical'
)

val_data = datagen.flow_from_directory(
    os.path.join(dataset_path, 'Cpra Pic Test'),
    target_size=image_size,
    batch_size=batch_size,
    class_mode='categorical'
)

# === LOAD PRETRAINED MODEL ===
base_model = MobileNetV2(
    input_shape=image_size + (3,),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False  # Freeze base model

# === CUSTOM CLASSIFIER ===
model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(train_data.num_classes, activation='softmax')
])

# === COMPILE MODEL ===
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# === TRAIN ===
history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=epochs
)

# === SAVE MODEL ===
model.save("Copra_Test_Model.h5")
print("🎉 Training complete! Model saved as 'Copra_Test_Model.h5'")

# === CONVERT TO TFLITE ===
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Save TFLite model
with open("Copra_Test_Model.tflite", "wb") as f:
    f.write(tflite_model)

print("✅ Model also converted and saved as 'Copra_Test_Model.tflite'")
