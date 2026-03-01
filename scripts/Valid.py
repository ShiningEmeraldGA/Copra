import tensorflow as tf
import numpy as np
import random
import os
from PIL import Image

# === Path to the .tflite model ===
MODEL_PATH = "Copra_AI/rock_paper_scissors_model_quantized.tflite"

# === Image settings ===
IMAGE_SIZE = (224, 224)
CLASS_NAMES = ['paper', 'rock', 'scissors']

print("Current working dir:", os.getcwd())
print("Model path:", os.path.abspath(MODEL_PATH))


# === Load the TFLite model ===
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# === Grab a random test image ===
base_dir = "Copra_AI/images/valid"
chosen_class = random.choice(CLASS_NAMES)
img_path = os.path.join(base_dir, chosen_class, random.choice(os.listdir(os.path.join(base_dir, chosen_class))))

print(f"\n🔍 Testing image: {img_path}")

# === Preprocess the image ===
img = Image.open(img_path).convert("RGB")
img = img.resize(IMAGE_SIZE)
img_array = np.array(img, dtype=np.float32) / 255.0  # normalize to 0-1
img_array = np.expand_dims(img_array, axis=0)  # add batch dimension

# === Run the model ===
interpreter.set_tensor(input_details[0]['index'], img_array)
interpreter.invoke()
output_data = interpreter.get_tensor(output_details[0]['index'])

# === Interpret result ===
predicted_index = np.argmax(output_data)
predicted_class = CLASS_NAMES[predicted_index]
confidence = output_data[0][predicted_index]

print(f"🤖 Prediction: {predicted_class} (Confidence: {confidence:.2f})")
