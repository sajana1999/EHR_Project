import pymysql

# Database Configuration (Matching app.py)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KINGsajana*',  
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

try:
    conn = pymysql.connect(**db_config)
    cur = conn.cursor()
    cur.execute("DESCRIBE patients")
    columns = cur.fetchall()
    print("Columns in patients table:")
    for col in columns:
        print(f"- {col['Field']} ({col['Type']})")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
