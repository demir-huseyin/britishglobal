from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/tally-webhook', methods=['POST'])
def receive_data():
    data = request.json
    print("Gelen veri:", data)
    
    # Örnek işlem: sadece email'i al ve dön
    email = data.get("email")
    return jsonify({"message": f"Veri alındı: {email}"}), 200

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)