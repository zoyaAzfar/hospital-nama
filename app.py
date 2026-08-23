from flask import Flask, render_template, jsonify, abort, send_from_directory, request
import sqlite3, os, requests

app = Flask(__name__)
DB_FILE = "hospitals.db"

MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "LOCAL_TEST_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.0-flash:generateContent"
TABLE_NAME = "NEW_database_of_hospitals (the updated beauty) (1)" 

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def build_prompt(hospitals):
    if len(hospitals) == 1:
        return (
            "You are a helpful assistant embedded on a hospital information page. "
            f"Here is the hospital's data:\n{hospitals[0]}\n\n"
            "Answer the user's questions using only this data. Be concise and factual."
        )
    labels = [f"Hospital {i+1}" for i in range(len(hospitals))]
    blocks = "\n".join(f"{labels[i]}: {hospitals[i]}" for i in range(len(hospitals)))
    return (
        "You are a helpful assistant embedded on a hospital comparison page. "
        f"The user is comparing:\n{blocks}\n\n"
        "Answer using only this data. Be concise and factual."
    )

def get_hospital_by_id(hosp_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT rowid AS id, * FROM "{TABLE_NAME}" WHERE rowid = ?', (hosp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        hospital_ids = data.get('hospital_ids', [])
        message = (data.get('message') or '').strip()
        history = data.get('history', [])[-20:]

        if not hospital_ids or not message:
            return jsonify({"error": "hospital_ids and message are required"}), 400

        hospitals = [h for h in (get_hospital_by_id(hid) for hid in hospital_ids) if h]
        if not hospitals:
            return jsonify({"error": "Couldn't find that hospital."}), 404

        context = build_prompt(hospitals)

        contents = [
            {"role": "user" if t.get("role") == "user" else "model", "parts": [{"text": t.get("text", "")}]}
            for t in history
        ]
        contents.append({"role": "user", "parts": [{"text": message}]})

        resp = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={"system_instruction": {"parts": [{"text": context}]}, "contents": contents},
            timeout=15
        )
        resp.raise_for_status()
        reply = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": reply})

    except requests.exceptions.RequestException:
        return jsonify({"error": "The assistant is temporarily unavailable. Try again in a moment."}), 503
    except Exception as e:
        app.logger.exception("chat route failed")
        return jsonify({"error": f"Server error: {e}"}), 500
    
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

@app.route('/compare')
def compare():
    return render_template('compare.html')

@app.route('/hospital/<int:hosp_id>')
def hospital_detail(hosp_id):
    # Pass the ID directly to a dedicated template view
    return render_template('detail.html', hosp_id=hosp_id)


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")


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
