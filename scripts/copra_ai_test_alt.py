import time
import sys
import termios
import tty
import sqlite3
import os
import numpy as np
from PIL import Image
import tensorflow as tf
from picamera2 import Picamera2

# === CONFIG ===
DB_PATH = 'Copra_AI/database/copra_data.db'
IMAGE_DIR = 'Copra_AI/images'
MODEL_PATH = 'Copra_AI/rock_paper_scissors_model_quantized.tflite'
CLASS_NAMES = ['paper', 'rock', 'scissors']
IMAGE_SIZE = (224, 224)
COPRA = 0
PHOTO_NUM = 0

os.makedirs(IMAGE_DIR, exist_ok=True)

# === Load TFLite model ===
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# === Init Camera ===
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

# === AI CLASSIFICATION ===
def classify_image(image_array):
    img = Image.fromarray(image_array).convert("RGB")
    img = img.resize(IMAGE_SIZE)
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    interpreter.set_tensor(input_details[0]['index'], img_array)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])

    predicted_index = int(np.argmax(output_data))
    predicted_class = CLASS_NAMES[predicted_index]
    confidence = float(output_data[0][predicted_index])

    print(f"🧠 AI Prediction: {predicted_class} (Confidence: {confidence:.2f})")
    return predicted_class

# === CAMERA CAPTURE ===
def capture_image():
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"batch_{timestamp}_{COPRA}_{PHOTO_NUM}.jpg"
    image_path = os.path.join(IMAGE_DIR, filename)

    print("📸 Capturing image...")
    frame = picam2.capture_array()
    Image.fromarray(frame).save(image_path)

    print(f"📸 Image saved: {image_path}")
    PHOTO_NUM += 1

    if PHOTO_NUM > 20:
        PHOTO_NUM = 0
        COPRA += 1
    return image_path, frame

# === DB INSERT ===
def insert_into_db(image_path, classification_result):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    user_data = ('Solace Tester', 'solace@example.com', 'copralove123')
    weight = 15.5
    moisture = 8.2
    temperature = 32.1
    total_value = 1860.00
    printed_status = False

    # User insert or fetch
    cursor.execute('SELECT user_id FROM User WHERE email = ?', (user_data[1],))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
    else:
        cursor.execute('INSERT INTO User (name, email, password) VALUES (?, ?, ?)', user_data)
        user_id = cursor.lastrowid

    # Insert receipt
    cursor.execute('''
        INSERT INTO Receipt (batch_id, weight, moisture_level, quality_result, total_value, printed_status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (None, weight, moisture, classification_result, total_value, printed_status))
    receipt_id = cursor.lastrowid

    # Insert batch
    cursor.execute('''
        INSERT INTO Batch (user_id, classification_result, image_path, receipt_id)
        VALUES (?, ?, ?, ?)
    ''', (user_id, classification_result, image_path, receipt_id))
    batch_id = cursor.lastrowid

    # Link receipt to batch
    cursor.execute('''
        UPDATE Receipt SET batch_id = ? WHERE receipt_id = ?
    ''', (batch_id, receipt_id))

    # Sensor data
    sensor_data = [
        ('Weight', weight, 'kg'),
        ('Moisture', moisture, '%'),
        ('Temperature', temperature, '°C')
    ]

    for s_type, val, unit in sensor_data:
        cursor.execute('''
            INSERT INTO SensorData (batch_id, sensor_type, value, unit)
            VALUES (?, ?, ?, ?)
        ''', (batch_id, s_type, val, unit))

    conn.commit()
    conn.close()
    print("🗂️ Data stored in DB successfully.")

# === Keyboard Utility ===
def get_char():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# === MAIN LOOP ===
def main():
    print("🎥 Camera ready.")
    print("Press [C] to capture, classify, and store | [Q] to quit")

    try:
        while True:
            ch = get_char().lower()
            if ch == 'c':
                image_path, frame = capture_image()
                classification = classify_image(frame)
                insert_into_db(image_path, classification)
            elif ch == 'q':
                print("👋 Exiting.")
                break
    finally:
        picam2.stop()

if __name__ == "__main__":
    main()
