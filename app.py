from flask import Flask, render_template, jsonify, abort
import sqlite3, os

app = Flask(__name__)
DB_FILE = "hospitals.db"

MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "LOCAL_TEST_KEY")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.context_processor
def inject_maps_key():
    return dict(maps_key=MAPS_API_KEY)
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/about')
def about():
    return render_template('aboutus.html')

@app.route('/hospitals')
def metrics():
    return render_template('hospitals.html')

@app.route('/hospital/<int:hosp_id>')
def hospital_detail(hosp_id):
    # Pass the ID directly to a dedicated template view
    return render_template('detail.html', hosp_id=hosp_id)

@app.route('/api/hospitals')
def get_hospitals():
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        TABLE_NAME = "NEW_database_of_hospitals (the updated beauty) (1)"

        # Get columns
        cursor.execute(f'PRAGMA table_info("{TABLE_NAME}")')
        columns = [row["name"] for row in cursor.fetchall()]

        # Build SELECT
        select_clause = ", ".join([f'"{c}"' for c in columns])

        query = f'''
            SELECT rowid AS id, {select_clause}
            FROM "{TABLE_NAME}"
        '''

        cursor.execute(query)
        rows = cursor.fetchall()

        return jsonify([dict(row) for row in rows])

    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()
        
if __name__ == '__main__':
    app.run()
