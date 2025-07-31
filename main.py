from flask import Flask, request, jsonify
import json
import requests
import os
from datetime import datetime

app = Flask(__name__)

# HubSpot API Key - Environment variable'dan al
HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY', '')

def extract_form_data(tally_data):
    """Tally webhook verisinden form alanlarını çıkar"""
    
    # Gerçek Tally webhook formatı - fields array'i kullanıyor
    form_fields = tally_data.get('data', {}).get('fields', [])
    
    # Fields'i label'a göre dictionary'e çevir
    field_dict = {}
    for field in form_fields:
        label = field.get('label', '')
        value = field.get('value')
        field_dict[label] = value
    
    print(f"🔍 Tally fields: {len(form_fields)} adet")
    print(f"📋 Field labels: {list(field_dict.keys())}")
    
    # Temel bilgiler
    extracted = {
        'submission_id': tally_data.get('data', {}).get('responseId', ''),
        'submitted_at': tally_data.get('createdAt', ''),
        
        # Kişisel bilgiler - Tally field labels'a göre
        'name': field_dict.get('Adınız Soyadınız', ''),
        'email': field_dict.get('E-mail Adresiniz', ''),
        'phone': field_dict.get('Telefon Numaranız', ''),
        
        # Kategori belirleme alanları
        'ticari': field_dict.get('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Ticari Danışmanlık)', False),
        'egitim': field_dict.get('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Eğitim Danışmanlığı)', False),
        'hukuk': field_dict.get('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Vize ve Hukuki Danışmanlık)', False),
        
        # Eğitim alanları
        'egitim_seviye': field_dict.get('İlgilendiğiniz Eğitim Seviyesi', ''),
        'lise': field_dict.get('İlgilendiğiniz Eğitim Seviyesi (Lise (İngiltere\'de lise eğitimi almak isteyenler için))', False),
        'lisans': field_dict.get('İlgilendiğiniz Eğitim Seviyesi (Lisans (Üniversite eğitimi))', False),
        'master': field_dict.get('İlgilendiğiniz Eğitim Seviyesi (Yüksek Lisans (Master programları))', False),
        'doktora': field_dict.get('İlgilendiğiniz Eğitim Seviyesi (Doktora (Phd programları))', False),
        'dil_okulu': field_dict.get('İlgilendiğiniz Eğitim Seviyesi (Dil Okulları (Yetişkinler için genel, IELTS veya mesleki İngilizce) )', False),
        'yaz_kampi': field_dict.get('İlgilendiğiniz Eğitim Seviyesi (Yaz Kampı (12-18 yaş grubu))', False),
        'not_ortalama': field_dict.get('Not Ortalamanız', ''),
        'butce': field_dict.get('Eğitim ve Konaklama için Düşündüğünüz Bütçe Nedir? (£)', ''),
        
        # Hukuk alanları
        'hukuk_konu': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz?', ''),
        'turistik_vize': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Turistik Vize (Visitor Visa))', False),
        'ogrenci_vize': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Öğrenci Vizesi (Tier 4 / Graduate Route))', False),
        'calisma_vize': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Çalışma Vizesi (Skilled Worker, Health and Care vb.))', False),
        'aile_vize': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Aile Birleşimi / Partner Vizesi)', False),
        'ilr': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere\'de Süresiz Oturum (ILR) Başvurusu)', False),
        'vatandaslik': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Vatandaşlık Başvurusu)', False),
        'vize_red': field_dict.get('Hangi konularda hukuki destek almak istiyorsunuz? (Vize Reddi İtiraz ve Yeniden Başvuru Danışmanlığı)', False),
        
        # Ticari alanları
        'sirket_adi': field_dict.get('Şirketinizin Adı', ''),
        'sektor': field_dict.get('Sektörünüz', ''),
        
        # Sektör detayları
        'ambalaj': field_dict.get('Sektörünüz (Ambalaj ve Baskı Ürünleri)', False),
        'tekstil': field_dict.get('Sektörünüz (Tekstil ve Giyim)', False),
        'ayakkabi': field_dict.get('Sektörünüz (Ayakkabı ve Deri Ürünleri)', False),
        'mobilya': field_dict.get('Sektörünüz (Mobilya ve Ev Dekorasyonu)', False),
        'gida': field_dict.get('Sektörünüz (Gıda Ürünleri / Yiyecek-İçecek)', False),
        'taki': field_dict.get('Sektörünüz (Takı, Bijuteri ve Aksesuar)', False),
        'hediye': field_dict.get('Sektörünüz (Hediyelik Eşya)', False),
        'kozmetik': field_dict.get('Sektörünüz (Kozmetik ve Kişisel Bakım)', False),
        'oyuncak': field_dict.get('Sektörünüz (Oyuncak ve Kırtasiye)', False),
        'temizlik': field_dict.get('Sektörünüz (Temizlik ve Hijyen Ürünleri)', False),
        'ev_gereci': field_dict.get('Sektörünüz (Ev Gereçleri ve Mutfak Ürünleri)', False),
        'hirdavat': field_dict.get('Sektörünüz (Hırdavat / Yapı Malzemeleri)', False),
        'otomotiv': field_dict.get('Sektörünüz (Otomotiv Yan Sanayi)', False),
        'bahce': field_dict.get('Sektörünüz (Bahçe ve Outdoor Ürünleri)', False),
        'diger_sektor': field_dict.get('Sektörünüz (Diğer)', False)
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
    
    name = extracted_data.get('name', '')
    email = extracted_data.get('email', '')
    phone = extracted_data.get('phone', '')
    
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

def get_education_details(extracted_data):
    """Eğitim detaylarını topla"""
    education_levels = []
    
    if extracted_data.get('lise'):
        education_levels.append('Lise')
    if extracted_data.get('lisans'):
        education_levels.append('Lisans')
    if extracted_data.get('master'):
        education_levels.append('Master')
    if extracted_data.get('doktora'):
        education_levels.append('Doktora')
    if extracted_data.get('dil_okulu'):
        education_levels.append('Dil Okulu')
    if extracted_data.get('yaz_kampi'):
        education_levels.append('Yaz Kampı')
    
    return {
        'education_programs': ', '.join(education_levels),
        'gpa': extracted_data.get('not_ortalama', ''),
        'budget': extracted_data.get('butce', '')
    }

def get_legal_details(extracted_data):
    """Hukuk detaylarını topla"""
    legal_services = []
    
    if extracted_data.get('turistik_vize'):
        legal_services.append('Turistik Vize')
    if extracted_data.get('ogrenci_vize'):
        legal_services.append('Öğrenci Vizesi')
    if extracted_data.get('calisma_vize'):
        legal_services.append('Çalışma Vizesi')
    if extracted_data.get('aile_vize'):
        legal_services.append('Aile Birleşimi')
    if extracted_data.get('ilr'):
        legal_services.append('Süresiz Oturum')
    if extracted_data.get('vatandaslik'):
        legal_services.append('Vatandaşlık')
    if extracted_data.get('vize_red'):
        legal_services.append('Vize Red İtiraz')
    
    return {
        'legal_services': ', '.join(legal_services),
        'legal_topic': extracted_data.get('hukuk_konu', '')
    }

def get_business_details(extracted_data):
    """Ticari detayları topla"""
    sectors = []
    
    # Sektör detaylarını topla
    sector_fields = ['ambalaj', 'tekstil', 'ayakkabi', 'mobilya', 'gida', 
                    'taki', 'hediye', 'kozmetik', 'oyuncak', 'temizlik',
                    'ev_gereci', 'hirdavat', 'otomotiv', 'bahce', 'diger_sektor']
    
    for field in sector_fields:
        if extracted_data.get(field):
            sectors.append(field.title())
    
    return {
        'company_name': extracted_data.get('sirket_adi', ''),
        'sector': extracted_data.get('sektor', ''),
        'sector_details': ', '.join(sectors)
    }

def save_to_hubspot(contact_info, category, extracted_data):
    """HubSpot'a contact kaydet"""
    
    if not HUBSPOT_API_KEY:
        print("⚠️ HubSpot API Key bulunamadı - Environment variable set edilmedi")
        return {"success": False, "error": "API Key bulunamadı"}
    
    # HubSpot API endpoint
    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Base properties - sadece standart HubSpot fields
    properties = {
        "email": contact_info['email'],
        "firstname": contact_info['firstname'],
        "lastname": contact_info['lastname'],
        "phone": contact_info['phone'],
        "lifecyclestage": "lead",
        "hs_lead_status": "NEW"
    }
    
    # Kategori bazlı ek bilgiler - notes alanına yazalım
    notes = f"British Global - Kategori: {category.title()}\n"
    
    if category == 'education':
        edu_details = get_education_details(extracted_data)
        notes += f"Eğitim Programları: {edu_details['education_programs']}\n"
        notes += f"Not Ortalaması: {edu_details['gpa']}\n"
        notes += f"Bütçe: {edu_details['budget']}\n"
        properties["jobtitle"] = "Eğitim Başvurusu"
    
    elif category == 'legal':
        legal_details = get_legal_details(extracted_data)
        notes += f"Hukuk Hizmetleri: {legal_details['legal_services']}\n"
        notes += f"Konu: {legal_details['legal_topic']}\n"
        properties["jobtitle"] = "Hukuk Danışmanlığı"
    
    elif category == 'business':
        business_details = get_business_details(extracted_data)
        notes += f"Şirket: {business_details['company_name']}\n"
        notes += f"Sektör: {business_details['sector']}\n"
        notes += f"Detaylar: {business_details['sector_details']}\n"
        properties["company"] = business_details['company_name']
        properties["jobtitle"] = "Ticari Danışmanlık"
    
    # Notes alanını ekle
    properties["hs_content_membership_notes"] = notes
    
    # Request payload
    payload = {
        "properties": properties
    }
    
    try:
        print(f"🔄 HubSpot'a gönderiliyor: {contact_info['email']}")
        print(f"Properties: {json.dumps(properties, indent=2, ensure_ascii=False)}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            contact_id = result.get('id')
            print(f"✅ HubSpot'a kaydedildi - Contact ID: {contact_id}")
            
            return {
                "success": True,
                "contact_id": contact_id,
                "properties_sent": properties
            }
        
        else:
            error_msg = response.text
            print(f"❌ HubSpot API hatası: {response.status_code} - {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "status_code": response.status_code
            }
    
    except Exception as e:
        print(f"❌ HubSpot kayıt hatası: {str(e)}")
        return {"success": False, "error": str(e)}

@app.route("/tally", methods=["POST"])
def tally_webhook():
    """Tally webhook endpoint - Güncellenmiş Tally format desteği ile"""
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
        
        # HubSpot'a kaydet
        hubspot_result = save_to_hubspot(contact, category, extracted)
        
        print("=" * 60)
        
        # Başarılı response
        return jsonify({
            "status": "success",
            "message": "Form verisi başarıyla işlendi ve HubSpot'a kaydedildi",
            "category": category,
            "contact": contact,
            "hubspot": hubspot_result,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ HATA: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    """Sağlık kontrolü"""
    hubspot_status = "✅ Configured" if HUBSPOT_API_KEY else "❌ Not configured"
    
    return jsonify({
        "status": "OK",
        "service": "British Global Webhook",
        "version": "4.0 - Tally Format Fix",
        "hubspot_api": hubspot_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/test", methods=["POST"])
def test_endpoint():
    """Test için endpoint - Hem eski hem yeni format desteği"""
    data = request.json
    
    # Test verisi ile form mapping dene
    extracted = extract_form_data(data)
    category = determine_category(extracted)
    contact = get_contact_info(extracted)
    
    # HubSpot'a test kaydı gönder (eğer email varsa)
    hubspot_result = {"message": "Email bulunamadı, HubSpot'a gönderilmedi"}
    if contact['email']:
        hubspot_result = save_to_hubspot(contact, category, extracted)
    
    return jsonify({
        "message": "Test başarılı!",
        "received": data,
        "extracted": extracted,
        "category": category,
        "contact": contact,
        "hubspot": hubspot_result,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)