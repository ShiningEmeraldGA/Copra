import sqlite3

# Connect to or create the database
conn = sqlite3.connect('database/copra_data.db')
cursor = conn.cursor()

# Create User table
cursor.execute('''
CREATE TABLE IF NOT EXISTS User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    password TEXT
)
''')

# Create Batch table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Batch (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    classification_result TEXT,
    image_path TEXT,
    receipt_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (receipt_id) REFERENCES Receipt(receipt_id)
)
''')

# Create SensorData table
cursor.execute('''
CREATE TABLE IF NOT EXISTS SensorData (
    sensor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    sensor_type TEXT,
    value REAL,
    unit TEXT,
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
)
''')

# Create Receipt table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Receipt (
    receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    date_issued DATETIME DEFAULT CURRENT_TIMESTAMP,
    weight REAL,
    moisture_level REAL,
    quality_result TEXT,
    total_value REAL,
    printed_status BOOLEAN,
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
)
''')

# C
