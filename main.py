from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

def extract_form_data(tally_data):
    """Tally webhook verisinden form alanlarını çıkar"""
    
    # Tally webhook structure - genelde 'data' içinde form fields
    form_data = tally_data.get('data', {})
    
    # Temel bilgiler - CSV'den gördüğümüz alan isimleri
    extracted = {
        'submission_id': form_data.get('responseId', ''),
        'submitted_at': form_data.get('createdAt', ''),
        
        # Kişisel bilgiler - Tally'den gelen field names
        'name': form_data.get('name', ''),  # Tally formdaki alan adı
        'email': form_data.get('email', ''),
        'phone': form_data.get('phone', ''),
        
        # CSV'deki gerçek alan isimleri için de kontrol
        'name_csv': form_data.get('Adınız Soyadınız', ''),
        'email_csv': form_data.get('E-mail Adresiniz', ''),
        'phone_csv': form_data.get('Telefon Numaranız', ''),
        
        # Kategori belirleme alanları (Boolean değerler)
        'ticari': form_data.get('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Ticari Danışmanlık)', False),
        'egitim': form_data.get('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Eğitim Danışmanlığı)', False),
        'hukuk': form_data.get('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Vize ve Hukuki Danışmanlık)', False),
        
        # Eğitim alanları
        'egitim_seviye': form_data.get('İlgilendiğiniz Eğitim Seviyesi', ''),
        'lise': form_data.get('İlgilendiğiniz Eğitim Seviyesi (Lise (İngiltere\'de lise eğitimi almak isteyenler için))', ''),
        'lisans': form_data.get('İlgilendiğiniz Eğitim Seviyesi (Lisans (Üniversite eğitimi))', ''),
        'master': form_data.get('İlgilendiğiniz Eğitim Seviyesi (Yüksek Lisans (Master programları))', ''),
        'doktora': form_data.get('İlgilendiğiniz Eğitim Seviyesi (Doktora (Phd programları))', ''),
        'dil_okulu': form_data.get('İlgilendiğiniz Eğitim Seviyesi (Dil Okulları (Yetişkinler için genel, IELTS veya mesleki İngilizce) )', ''),
        'yaz_kampi': form_data.get('İlgilendiğiniz Eğitim Seviyesi (Yaz Kampı (12-18 yaş grubu))', ''),
        'not_ortalama': form_data.get('Not Ortalamanız', ''),
        'butce': form_data.get('Eğitim ve Konaklama için Düşündüğünüz Bütçe Nedir? (£)', ''),
        
        # Hukuk alanları
        'hukuk_konu': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz?', ''),
        'turistik_vize': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Turistik Vize (Visitor Visa))', ''),
        'ogrenci_vize': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Öğrenci Vizesi (Tier 4 / Graduate Route))', ''),
        'calisma_vize': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Çalışma Vizesi (Skilled Worker, Health and Care vb.))', ''),
        'aile_vize': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Aile Birleşimi / Partner Vizesi)', ''),
        'ilr': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere\'de Süresiz Oturum (ILR) Başvurusu)', ''),
        'vatandaslik': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Vatandaşlık Başvurusu)', ''),
        'vize_red': form_data.get('Hangi konularda hukuki destek almak istiyorsunuz? (Vize Reddi İtiraz ve Yeniden Başvuru Danışmanlığı)', ''),
        
        # Ticari alanları
        'sirket_adi': form_data.get('Şirketinizin Adı', ''),
        'sektor': form_data.get('Sektörünüz', ''),
        
        # Sektör detayları
        'ambalaj': form_data.get('Sektörünüz (Ambalaj ve Baskı Ürünleri)', ''),
        'tekstil': form_data.get('Sektörünüz (Tekstil ve Giyim)', ''),
        'ayakkabi': form_data.get('Sektörünüz (Ayakkabı ve Deri Ürünleri)', ''),
        'mobilya': form_data.get('Sektörünüz (Mobilya ve Ev Dekorasyonu)', ''),
        'gida': form_data.get('Sektörünüz (Gıda Ürünleri / Yiyecek-İçecek)', ''),
        'taki': form_data.get('Sektörünüz (Takı, Bijuteri ve Aksesuar)', ''),
        'hediye': form_data.get('Sektörünüz (Hediyelik Eşya)', ''),
        'kozmetik': form_data.get('Sektörünüz (Kozmetik ve Kişisel Bakım)', ''),
        'oyuncak': form_data.get('Sektörünüz (Oyuncak ve Kırtasiye)', ''),
        'temizlik': form_data.get('Sektörünüz (Temizlik ve Hijyen Ürünleri)', ''),
        'ev_gereci': form_data.get('Sektörünüz (Ev Gereçleri ve Mutfak Ürünleri)', ''),
        'hirdavat': form_data.get('Sektörünüz (Hırdavat / Yapı Malzemeleri)', ''),
        'otomotiv': form_data.get('Sektörünüz (Otomotiv Yan Sanayi)', ''),
        'bahce': form_data.get('Sektörünüz (Bahçe ve Outdoor Ürünleri)', ''),
        'diger_sektor': form_data.get('Sektörünüz (Diğer)', '')
    }
    
    return extracted

def determine_category(extracted_data):
    """Form verilerine göre kategori belirle"""
    
    # Öncelik sırası: boolean değerleri kontrol et
    if extracted_data.get('ticari'):
        return 'business'
    elif extracted_data.get('egitim'): 
        return 'education'
    elif extracted_data.get('hukuk'):
        return 'legal'
    
    # Boolean değer yoksa, form içeriğine göre tahmin et
    # Şirket adı varsa ticari
    if extracted_data.get('sirket_adi') or extracted_data.get('sektor'):
        return 'business'
    
    # Eğitim seviyesi varsa eğitim
    if (extracted_data.get('egitim_seviye') or 
        extracted_data.get('lise') or extracted_data.get('lisans') or 
        extracted_data.get('master') or extracted_data.get('doktora')):
        return 'education'
    
    # Hukuk konusu varsa hukuk
    if (extracted_data.get('hukuk_konu') or 
        extracted_data.get('turistik_vize') or extracted_data.get('ogrenci_vize')):
        return 'legal'
    
    # Hiçbiri yoksa genel
    return 'general'

def get_contact_info(extracted_data):
    """En güncel iletişim bilgilerini al"""
    
    # Name: Tally field varsa onu, yoksa CSV field'ı kullan
    name = extracted_data.get('name') or extracted_data.get('name_csv', '')
    
    # Email: aynı mantık
    email = extracted_data.get('email') or extracted_data.get('email_csv', '')
    
    # Phone: aynı mantık
    phone = extracted_data.get('phone') or extracted_data.get('phone_csv', '')
    
    # Name'i firstname/lastname'e böl
    name_parts = name.split(' ', 1) if name else ['', '']
    firstname = name_parts[0] if len(name_parts) > 0 else ''
    lastname = name_parts[1] if len(name_parts) > 1 else ''
    
    return {
        'firstname': firstname,
        'lastname': lastname, 
        'fullname': name,
        'email': email,
        'phone': str(phone) if phone else ''
    }

@app.route("/tally", methods=["POST"])
def tally_webhook():
    """Tally webhook endpoint - Adım 2: Form mapping ve kategori belirleme"""
    try:
        # Gelen veriyi al
        data = request.json
        
        print("=" * 60)
        print(f"YENİ WEBHOOK - {datetime.now()}")
        print("Ham Tally verisi:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Form verilerini çıkar
        extracted = extract_form_data(data)
        print("\nÇıkarılan form verileri:")
        print(json.dumps(extracted, indent=2, ensure_ascii=False))
        
        # Kategori belirle
        category = determine_category(extracted)
        print(f"\nBelirlenen kategori: {category}")
        
        # İletişim bilgilerini al
        contact = get_contact_info(extracted)
        print(f"\nİletişim bilgileri: {contact}")
        
        # Email kontrolü
        if not contact['email']:
            print("❌ EMAIL BULUNAMADI!")
            return jsonify({"error": "Email adresi bulunamadı"}), 400
        
        print("=" * 60)
        
        # Başarılı response
        return jsonify({
            "status": "success",
            "message": "Form verisi başarıyla işlendi",
            "category": category,
            "contact": contact,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ HATA: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    """Sağlık kontrolü"""
    return jsonify({
        "status": "OK",
        "service": "British Global Webhook",
        "version": "2.0 - Adım 2: Form Mapping",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/test", methods=["POST"])
def test_endpoint():
    """Test için endpoint - form mapping test"""
    data = request.json
    
    # Test verisi ile form mapping dene
    extracted = extract_form_data(data)
    category = determine_category(extracted)
    contact = get_contact_info(extracted)
    
    return jsonify({
        "message": "Test başarılı!",
        "received": data,
        "extracted": extracted,
        "category": category,
        "contact": contact,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)