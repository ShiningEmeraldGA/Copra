import subprocess
import time
import sys
import termios
import tty
import sqlite3
import os

DB_PATH = 'Copra_AI/database/copra_data.db'
IMAGE_DIR = 'images'
os.makedirs(IMAGE_DIR, exist_ok=True)

def start_stream():
    return subprocess.Popen([
        "libcamera-vid",
        "-t", "0",
        "--preview",
        "--framerate", "30",
        "--width", "640", "--height", "480"
    ])

def capture_image(stream_proc):
    print("⏸️ Stopping stream to capture image...")
    stream_proc.terminate()
    stream_proc.wait()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"batch_{timestamp}.jpg"
    image_path = os.path.join(IMAGE_DIR, filename)

    subprocess.run([
        "libcamera-still",
        "-o", image_path,
        "--nopreview",
        "-t", "1"
    ])

    print(f"📸 Image saved as {image_path}")
    return image_path, start_stream()

def insert_into_db(image_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create fake/mock data (you can replace these with actual inputs or sensor readings)
    user_data = ('Solace Tester', 'solace@example.com', 'copralove123')
    weight = 15.5
    moisture = 8.2
    temperature = 32.1
    quality_result = 'Good'
    total_value = 1860.00
    printed_status = False

    # Insert or get user (if you want to avoid duplicates, check by email)
    cursor.execute('SELECT user_id FROM User WHERE email = ?', (user_data[1],))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
    else:
        cursor.execute('''
            INSERT INTO User (name, email, password)
            VALUES (?, ?, ?)
        ''', user_data)
        user_id = cursor.lastrowid

    # Insert receipt
    cursor.execute('''
        INSERT INTO Receipt (batch_id, weight, moisture_level, quality_result, total_value, printed_status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (None, weight, moisture, quality_result, total_value, printed_status))
    receipt_id = cursor.lastrowid

    # Insert batch
    cursor.execute('''
        INSERT INTO Batch (user_id, classification_result, image_path, receipt_id)
        VALUES (?, ?, ?, ?)
    ''', (user_id, quality_result, image_path, receipt_id))
    batch_id = cursor.lastrowid

    # Link receipt to batch
    cursor.execute('''
        UPDATE Receipt SET batch_id = ? WHERE receipt_id = ?
    ''', (batch_id, receipt_id))

    # Insert sensor data
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
    print("🗂️ Data successfully inserted into database.")

def get_char():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def main():
    print("🎥 Starting video stream...")
    stream_proc = start_stream()

    print("Press [C] to capture & save, [Q] to quit.")
    try:
        while True:
            ch = get_char().lower()
            if ch == 'c':
                print("📸 Capturing...")
                image_path, stream_proc = capture_image(stream_proc)
                insert_into_db(image_path)
            elif ch == 'q':
                print("👋 Quitting.")
                break
    finally:
        stream_proc.terminate()
        stream_proc.wait()

if __name__ == "__main__":
    main()
