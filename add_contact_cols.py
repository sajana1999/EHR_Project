import pymysql

# Database Configuration (Matching app.py)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KINGsajana*',  
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def add_contact_columns():
    try:
        conn = pymysql.connect(**db_config)
        cur = conn.cursor()
        
        columns = [
            ("email", "VARCHAR(100)"),
            ("address", "TEXT"),
            ("phone", "VARCHAR(20)")
        ]
        
        for col_name, col_type in columns:
            try:
                # Check if column exists
                cur.execute(f"SHOW COLUMNS FROM patients LIKE '{col_name}'")
                if not cur.fetchone():
                    print(f"Adding {col_name} column...")
                    cur.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_type}")
                    print(f"Successfully added {col_name} column.")
                else:
                    print(f"{col_name} column already exists.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
            
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database Connection Error: {e}")

if __name__ == "__main__":
    add_contact_columns()
