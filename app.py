import os, requests
import libsql_client  
from flask import Flask, render_template, jsonify, abort, send_from_directory, request

app = Flask(__name__)
DB_FILE = "hospitals.db"

MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "LOCAL_TEST_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
TABLE_NAME = "NEW_database_of_hospitals (the updated beauty) (1)" 

def get_db_client():
    url = os.environ.get("TURSO_DATABASE_URL", "file:hospitals.db")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    
    if url.startswith("file:"):
        print("DATABASE: Using Local File")
    else:
        print("dATABASE: Using Turso Cloud")
        
    return libsql_client.create_client_sync(url=url, auth_token=token)

def build_prompt(hospitals):
    # Base instructions that apply whether viewing 1 hospital or comparing multiple
    base_instructions = """
    You are an AI assistant for 'Hospital Nama', helping users in Pakistan choose the right hospital. 
    You have been provided with data for the hospital(s) the user is currently viewing.

    STRICT INSTRUCTIONS:
    1. LANGUAGE MATCHING: Detect the language of the user's question (English, Urdu script, or Roman Urdu) and strictly respond in that exact language/script.
    2. TONE & FORMAT: Be conversational and helpful. DO NOT use tables or bold headings—they are too overwhelming. Use short, scannable paragraphs.
    3. SUMMARIZE DATA: Do not spit out raw data or exact decimal percentages. Instead of "48.26% negative reviews", say "mixed reviews, mostly concerning process issues". 
    4. HIGHLIGHT TRADE-OFFS: If comparing multiple hospitals, clearly highlight the pros and cons (e.g., "Hospital A is cheaper, but Hospital B has better patient feedback"). Factor in distance if the user's location is provided.
    5. CURRENCY: Any money mentioned is in Pakistani Rupees (PKR).
    6. DISCLAIMER: Include a brief sentence stating that you provide hospital choice guidance, not medical advice.
    7. LIMIT: Keep answers brief (under 300 words), but explain the 'why' behind the ratings clearly.
    8. BOUNDARIES: Do not answer questions outside the scope of hospital choice or the provided data.
    """
    
    if len(hospitals) == 1:
        data_context = f"Here is the data for the hospital the user is looking at:\n{hospitals[0]}"
    else:
        labels = [f"Hospital {i+1}" for i in range(len(hospitals))]
        blocks = "\n".join(f"{labels[i]}: {hospitals[i]}" for i in range(len(hospitals)))
        data_context = f"The user is comparing the following hospitals:\n{blocks}"
        
    return f"{base_instructions}\n\n{data_context}"

def get_hospital_by_id(hosp_id):
    client = get_db_client()
    try:
        result = client.execute(f'SELECT rowid AS id, * FROM "{TABLE_NAME}" WHERE rowid = ?', [hosp_id])
        
        if result.rows:
            return dict(zip(result.columns, result.rows[0]))
        return None
    finally:
        client.close()

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

        try:
                
                resp = requests.post(
                    GEMINI_URL,
                    headers={"Content-Type": "application/json"},
                    json={"system_instruction": {"parts": [{"text": context}]}, "contents": contents},
                    timeout=15
                )
                resp.raise_for_status()
                reply = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"reply": reply})
        
        except requests.exceptions.RequestException as e:
                status = getattr(e.response, "status_code", None)
                body = getattr(e.response, "text", str(e))
                app.logger.error(f"Gemini call failed (status={status}): {body}")
                return jsonify({"error": f"Gemini error {status}: {body[:200]}"}), 503

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

@app.route('/sync-zones')
def trigger_sync():
    PHC_URL = "https://www.phc.org.pk:44339/api/CG/GetZoningInspected"
    payload = {"Zoning": None, "DistrictID": 17}

    try:
        response = requests.post(PHC_URL, json=payload, timeout=15)
        response.raise_for_status()
        phc_data = response.json()
        
        client = get_db_client()
        updated_count = 0
        
        try:
            # Extract the actual list of hospitals from the dictionary first
            hospitals_list = phc_data.get("Zoninginspect", [])
            
            for hospital in hospitals_list:
                zone = hospital.get('Coloring_Zone')
                
                update_query = f'''
                    UPDATE "{TABLE_NAME}" 
                    SET "PHC Zone" = ? 
                    WHERE "Registration" = ? 
                '''
                
                res = client.execute(update_query, [zone, r_no])
                if res.rows_affected > 0:
                    updated_count += 1
                    
            return jsonify({
                "status": "success",
                "message": f"Updated PHC Zones for {updated_count} hospitals."
            })
        finally:
            client.close()

    except Exception as e:
        app.logger.exception("Sync failed")
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500

@app.route('/api/hospitals')
def get_hospitals():
    client = get_db_client()
    try:
        # Fetch all hospitals
        result = client.execute(f'SELECT rowid AS id, * FROM "{TABLE_NAME}"')
        
        # Convert all rows into dictionaries 
        hospitals = [dict(zip(result.columns, row)) for row in result.rows]
        return jsonify(hospitals)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        client.close()
        
if __name__ == '__main__':
    app.run()
