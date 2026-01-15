
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

        # Add vitals columns to appointments
        columns_to_add = [
            ("blood_pressure", "VARCHAR(20) NULL"),
            ("temperature", "DECIMAL(5,2) NULL"),
            ("pulse_rate", "INT NULL"),
            ("sp_o2", "INT NULL")
        ]

        for col_name, col_def in columns_to_add:
            try:
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
        print("Database migration for Vitals completed successfully.")
        conn.close()

    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    migrate_db()
