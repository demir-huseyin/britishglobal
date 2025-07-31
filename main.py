from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

@app.route("/tally", methods=["POST"])
def tally_webhook():
    """Tally webhook endpoint - Adım 1: Sadece veriyi al ve yazdır"""
    try:
        # Gelen veriyi al
        data = request.json
        
        # Console'a yazdır (Cloud Run logs'da görünür)
        print("=" * 50)
        print(f"YENİ WEBHOOK - {datetime.now()}")
        print("Gelen veri:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("=" * 50)
        
        # Temel alanları kontrol et
        if not data:
            return jsonify({"error": "Veri bulunamadı"}), 400
            
        # Başarılı response
        return jsonify({
            "status": "success",
            "message": "Webhook alındı",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"HATA: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    """Sağlık kontrolü"""
    return jsonify({
        "status": "OK",
        "service": "British Global Webhook",
        "version": "1.0 - Adım 1",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/test", methods=["POST"])
def test_endpoint():
    """Test için endpoint"""
    return jsonify({
        "message": "Test başarılı!",
        "received": request.json,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)