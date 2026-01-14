import pymysql

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root*', 
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

try:
    conn = pymysql.connect(**db_config)
    cur = conn.cursor()

    sql = """
    CREATE TABLE IF NOT EXISTS appointments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        patient_id INT NOT NULL,
        doctor_id INT NOT NULL,
        appointment_date DATE,
        weight FLOAT,
        diagnosis TEXT,
        clinical_notes TEXT,
        prescription TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """
    cur.execute(sql)
    conn.commit()
    print("Appointments table created successfully.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
