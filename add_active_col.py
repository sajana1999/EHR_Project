import pymysql

# Database Configuration (Matching app.py)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KINGsajana*',  
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def add_active_column():
    try:
        conn = pymysql.connect(**db_config)
        cur = conn.cursor()
        
        # Check if column exists first
        cur.execute("SHOW COLUMNS FROM patients LIKE 'is_active'")
        result = cur.fetchone()
        
        if not result:
            print("Adding is_active column...")
            # Default to 1 (True/Active)
            cur.execute("ALTER TABLE patients ADD COLUMN is_active TINYINT(1) DEFAULT 1")
            conn.commit()
            print("Successfully added is_active column.")
        else:
            print("is_active column already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_active_column()
