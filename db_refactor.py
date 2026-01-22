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

    # 1. Migrate Legacy Data (if exists)
    print("Migrating legacy data...")
    # Map medical_history -> clinical_notes
    migration_sql = """
    INSERT INTO appointments (patient_id, doctor_id, appointment_date, weight, clinical_notes)
    SELECT id, doctor_id, appointment_date, weight, medical_history
    FROM patients
    WHERE appointment_date IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM appointments WHERE patient_id = patients.id AND appointment_date = patients.appointment_date);
    """
    cur.execute(migration_sql)
    conn.commit()

    # 2. Cleanup Patients Table
    print("Cleaning up patients table...")
    # Drop columns if they exist. Using Ignore logic or checking schema is complex in raw SQL, 
    # so we usually just Try/Catch or use IF EXISTS (MariaDB 10.0+).
    # We'll rely on the fact we know the schema.
    
    alter_queries = [
        "ALTER TABLE patients DROP COLUMN appointment_date",
        "ALTER TABLE patients DROP COLUMN weight",
        "ALTER TABLE patients DROP COLUMN medical_history",
        # "diagnosis" and "prescription" were never in patients table based on previous schema viewing
    ]
    
    for q in alter_queries:
        try:
            cur.execute(q)
        except Exception as e:
            print(f"Skipping query (might have run already): {e}")

    conn.commit()
    print("Database refactor complete.")
    conn.close()

except Exception as e:
    print(f"Error: {e}")
