import sqlite3
import os

SQL_FILE = "hospital_dataset_prices_updated.sql"
DB_FILE = "hospitals.db"

def initialize_database():
    if not os.path.exists(SQL_FILE):
        print(f"Can't find '{SQL_FILE}'")
        return

    print(f"Found {SQL_FILE}")
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Crucial fix: Safely drop the old table before rebuilding it to prevent duplicates
        cursor.execute('DROP TABLE IF EXISTS "hospital_dataset_prices_updated";')        
        cursor.executescript(sql_script)
        conn.commit()
        print("Done")
    except sqlite3.Error as e:
        print(f"Not done {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database()