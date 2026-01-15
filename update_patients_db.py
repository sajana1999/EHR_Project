import pymysql

# Database Configuration (Matching app.py)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root*',  
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

def alter_patients_table():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # List of columns to add if they don't exist
    # Note: 'name' might already exist, so we might need to handle first_name/last_name migration or just add them.
    # Assuming we are adding to the existing table.
    
    columns = [
        ("first_name", "VARCHAR(100)"),
        ("last_name", "VARCHAR(100)"),
        ("insurance_number", "VARCHAR(50)"),
        ("age", "INT"),
        ("weight", "DECIMAL(5,2)"),
        ("gender", "VARCHAR(20)"),
        ("allergies", "VARCHAR(255)"),
        ("appt_date", "DATE"),
        ("medical_history", "TEXT"), # user called it 'history' in form, let's call it medical_history in DB or match form?
        # Form has: name="history"
        ("patient_img", "VARCHAR(255)"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for col_name, col_type in columns:
        try:
            print(f"Adding {col_name}...")
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name}")
        except Exception as e:
            print(f"Could not add {col_name}: {e}")
            
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    alter_patients_table()
