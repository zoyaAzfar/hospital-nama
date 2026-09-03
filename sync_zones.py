@app.route('/sync-zones')
def trigger_sync():
    provided_key = request.args.get('key')
    if provided_key != "my_secret_password":
        return jsonify({"error": "Unauthorized. Nice try!"}), 401

    PHC_URL = "https://www.phc.org.pk:44339/api/CG/GetZoningInspected"
    payload = {"Zoning": None, "DistrictID": 17}

    try:
        response = requests.post(PHC_URL, json=payload, timeout=15)
        response.raise_for_status()
        phc_data = response.json()
        
        client = get_db_client()
        updated_count = 0
        
        try:
            for hospital in phc_data:
                zone = hospital.get('Coloring_Zone')
                r_no = hospital.get('R-No')
                
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
