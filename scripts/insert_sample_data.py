import sqlite3

# Connect to the database (adjust if your path is different)
conn = sqlite3.connect('database/copra_data.db')
cursor = conn.cursor()

# Insert a sample user
cursor.execute('''
INSERT INTO User (name, email, password)
VALUES (?, ?, ?)
''', ('Solace Tester', 'solace@example.com', 'copralove123'))

user_id = cursor.lastrowid  # get inserted user ID

# Insert a sample receipt
cursor.execute('''
INSERT INTO Receipt (batch_id, weight, moisture_level, quality_result, total_value, printed_status)
VALUES (?, ?, ?, ?, ?, ?)
''', (None, 15.5, 8.2, 'Good', 1860.00, False))

receipt_id = cursor.lastrowid  # get inserted receipt ID

# Insert a sample batch (linking to user and receipt)
cursor.execute('''
INSERT INTO Batch (user_id, classification_result, image_path, receipt_id)
VALUES (?, ?, ?, ?)
''', (user_id, 'Good', '/images/batch_001.jpg', receipt_id))

batch_id = cursor.lastrowid

# Update the receipt to link back to batch (circular link!)
cursor.execute('''
UPDATE Receipt SET batch_id = ? WHERE receipt_id = ?
''', (batch_id, receipt_id))

# Insert some sample sensor data
sensor_data = [
    ('Weight', 15.5, 'kg'),
    ('Moisture', 8.2, '%'),
    ('Temperature', 32.1, '°C')
]

for s_type, val, unit in sensor_data:
    cursor.execute('''
    INSERT INTO SensorData (batch_id, sensor_type, value, unit)
    VALUES (?, ?, ?, ?)
    ''', (batch_id, s_type, val, unit))

# Commit changes and close
conn.commit()
conn.close()

print("✅ Sample data inserted successfully.")
