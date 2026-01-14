import pymysql

# Database Configuration (Matches your app.py)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KINGsajana*', # Ensure this matches your MySQL password
    'database': 'ehr_system'
}

def run_migration():
    try:
        # Connect to the MySQL server
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # SQL to check if the column exists first to avoid errors
        check_query = """
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = 'ehr_system' 
        AND TABLE_NAME = 'doctors' 
        AND COLUMN_NAME = 'is_verified';
        """
        
        cursor.execute(check_query)
        column_exists = cursor.fetchone()[0]

        if not column_exists:
            # Safely add the column
            alter_query = "ALTER TABLE doctors ADD COLUMN is_verified BOOLEAN DEFAULT FALSE AFTER password;"
            cursor.execute(alter_query)
            connection.commit()
            print("Successfully added 'is_verified' column to 'doctors' table.")
        else:
            print("Column 'is_verified' already exists. No changes made.")

    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        if 'connection' in locals():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    run_migration()