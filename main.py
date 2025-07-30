from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY")


@app.route("/tally", methods=["POST"])
def tally_webhook():
    data = request.json
    print("Gelen Tally verisi:", data)

    # Tally formundaki alan isimlerine göre güncelle
    email = data.get("data", {}).get("email")
    firstname = data.get("data", {}).get("firstname", "")
    lastname = data.get("data", {}).get("lastname", "")

    if not email:
        return jsonify({"error": "Email bulunamadı"}), 400

    # HubSpot API çağrısı
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "properties": {
            "email": email,
            "firstname": firstname,
            "lastname": lastname
        }
    }

    hubspot_response = requests.post(
        "https://api.hubapi.com/crm/v3/objects/contacts",
        headers=headers,
        json=payload
    )

    if hubspot_response.status_code in [200, 201]:
        return jsonify({"message": "Başarıyla HubSpot'a gönderildi"}), 200
    else:
        return jsonify({"error": "HubSpot API hatası", "details": hubspot_response.text}), 500

@app.route("/", methods=["GET"])
def hello():
    return "Tally webhook listener aktif!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)