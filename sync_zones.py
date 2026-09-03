import requests
import sqlite3

DB_FILE = "hospitals.db"
TABLE_NAME = "NEW_database_of_hospitals (the updated beauty) (1)"
PHC_URL = "https://www.phc.org.pk:44339/api/CG/GetZoningInspected"

def sync_phc_zones():
    payload = {
        "Zoning": None, 
        "DistrictID": 17
    }

    try:
        print("Fetching latest zones from PHC...")
        response = requests.post(PHC_URL, json=payload, timeout=15)
        response.raise_for_status()
        phc_data = response.json()
        print(f"Successfully fetched {len(phc_data)} hospitals from PHC.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch from PHC API: {e}")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        updated_count = 0
        
        for hospital in phc_data:
            zone = hospital.get('Coloring_Zone')
            
            phc_identifier = hospital.get('HCEName') 
            
            update_query = f'''
                UPDATE "{TABLE_NAME}" 
                SET "PHC Zone" = ? 
                WHERE "Name" = ? 
            '''
            
            cursor.execute(update_query, (zone, phc_identifier))
            
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()
        print(f"Success! Updated the PHC Zone for {updated_count} out of your 45 hospitals.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    sync_phc_zones()
