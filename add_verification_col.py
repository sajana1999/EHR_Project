import pymysql

# Database Configuration (Matches your app.py)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KINGsajana*', # Ensure this matches your MySQL password
    'database': 'ehr_system'
}

def update_schema():
    connection = None
    try:
        # 1. Connect to the MySQL server
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # 2. Check if the column already exists to prevent "Duplicate column" errors
        check_query = """
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = 'ehr_system' 
        AND TABLE_NAME = 'doctors' 
        AND COLUMN_NAME = 'is_verified';
        """
        cursor.execute(check_query)
        exists = cursor.fetchone()[0]

        if not exists:
            # 3. Safely add the column after the password field
            # DEFAULT 0 means False (unverified) by default
            alter_query = "ALTER TABLE doctors ADD COLUMN is_verified BOOLEAN DEFAULT FALSE AFTER password;"
            cursor.execute(alter_query)
            connection.commit()
            print("Successfully added 'is_verified' column to the doctors table.")
        else:
            print("The 'is_verified' column already exists. No changes needed.")

    except Exception as e:
        print(f"Error updating database: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    update_schema()