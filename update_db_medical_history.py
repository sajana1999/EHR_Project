
import pymysql

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root*',
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def migrate_db():
    try:
        conn = pymysql.connect(**db_config)
        cur = conn.cursor()

        # Add medical_history to patients
        col_name = "medical_history"
        col_def = "TEXT NULL"

        try:
            cur.execute(f"SHOW COLUMNS FROM patients LIKE '{col_name}'")
            result = cur.fetchone()
            if not result:
                print(f"Adding column {col_name}...")
                cur.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}")
            else:
                print(f"Column {col_name} already exists.")
        except Exception as e:
            print(f"Error checking/adding column {col_name}: {e}")

        conn.commit()
        print("Database migration for Medical History completed successfully.")
        conn.close()

    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    migrate_db()
