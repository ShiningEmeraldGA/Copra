import sqlite3

# Connect to the database
conn = sqlite3.connect('database/copra_data.db')
cursor = conn.cursor()

# View all users
print("\n👤 Users:")
cursor.execute("SELECT * FROM User")
users = cursor.fetchall()
for user in users:
    print(user)

# View all batches
print("\n📦 Batches:")
cursor.execute("SELECT * FROM Batch")
batches = cursor.fetchall()
for batch in batches:
    print(batch)

# View all receipts
print("\n🧾 Receipts:")
cursor.execute("SELECT * FROM Receipt")
receipts = cursor.fetchall()
for receipt in receipts:
    print(receipt)

# View all sensor data
print("\n🌡️ Sensor Readings:")
cursor.execute("SELECT * FROM SensorData")
sensors = cursor.fetchall()
for sensor in sensors:
    print(sensor)

# Optional: Display joined info (user + batch + receipt)
print("\n🔗 Full Batch Details:")
cursor.execute('''
SELECT 
    u.name, 
    b.batch_id, 
    b.timestamp, 
    b.classification_result, 
    r.total_value, 
    r.quality_result
FROM Batch b
JOIN User u ON b.user_id = u.user_id
JOIN Receipt r ON b.receipt_id = r.receipt_id
''')
results = cursor.fetchall()
for row in results:
    print(f"User: {row[0]} | Batch ID: {row[1]} | Time: {row[2]} | Result: {row[3]} | Quality: {row[5]} | Value: ₱{row[4]}")

# Close connection
conn.close()
