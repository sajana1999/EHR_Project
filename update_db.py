import pymysql

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='ehr_system',
        cursorclass=pymysql.cursors.DictCursor
    )

def alter_table():
    conn = get_db_connection()
    cur = conn.cursor()
    
    columns = [
        ("first_name", "VARCHAR(100)"),
        ("last_name", "VARCHAR(100)"),
        ("category", "VARCHAR(100)"),
        ("doctor_medical_id", "VARCHAR(100)"),
        ("is_verified", "BOOLEAN DEFAULT FALSE"),
        ("verification_token", "VARCHAR(100)")
    ]
    
    for col_name, col_type in columns:
        try:
            print(f"Adding {col_name}...")
            cur.execute(f"ALTER TABLE doctors ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name}")
        except Exception as e:
            print(f"Could not add {col_name}: {e}")
            
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    alter_table()
