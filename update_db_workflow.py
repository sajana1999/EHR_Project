
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

        # Add columns if they don't exist
        columns_to_add = [
            ("appointment_time", "TIME NULL"),
            ("status", "VARCHAR(20) DEFAULT 'Scheduled'"),
            ("reason_for_visit", "VARCHAR(255) NULL"),
            ("final_diagnosis", "TEXT NULL")
        ]

        for col_name, col_def in columns_to_add:
            try:
                # Check if column exists
                cur.execute(f"SHOW COLUMNS FROM appointments LIKE '{col_name}'")
                result = cur.fetchone()
                if not result:
                    print(f"Adding column {col_name}...")
                    cur.execute(f"ALTER TABLE appointments ADD COLUMN {col_name} {col_def}")
                else:
                    print(f"Column {col_name} already exists.")
            except Exception as e:
                print(f"Error checking/adding column {col_name}: {e}")

        conn.commit()
        print("Database migration completed successfully.")
        conn.close()

    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    migrate_db()
