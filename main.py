from flask import Flask, request, jsonify
import json
import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)

# HubSpot API Key - Environment variable'dan al
HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY', '')

# EMAIL AYARLARI - Turhost SMTP
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'mail.britishglobal.com.tr')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
EMAIL_USER = os.environ.get('EMAIL_USER', 'info@britishglobal.com.tr')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '#7U<gIbZ')

# MAIL ADRESLERİ
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'info@britishglobal.com.tr')
EDUCATION_PARTNER_EMAIL = os.environ.get('EDUCATION_PARTNER_EMAIL', 'demirhuseyin@outlook.com')
LEGAL_PARTNER_EMAIL = os.environ.get('LEGAL_PARTNER_EMAIL', 'info@catalcaorganik.com')

def extract_form_data(tally_data):
    """Tally webhook verisinden form alanlarını çıkar - Çok dilli destek"""
    
    # Gerçek Tally webhook formatı - fields array'i kullanıyor
    form_fields = tally_data.get('data', {}).get('fields', [])
    
    # Fields'i label'a göre dictionary'e çevir
    field_dict = {}
    for field in form_fields:
        label = field.get('label', '')
        value = field.get('value')
        # Null değerleri güvenli şekilde handle et
        if value is not None:
            field_dict[label] = value
    
    print(f"🔍 Tally fields: {len(form_fields)} adet")
    print(f"📋 Field labels: {list(field_dict.keys())}")
    print(f"🔍 Field values: {field_dict}")
    
    # ÇOK DİLLİ FIELD MAPPING - Türkçe ve İngilizce
    def get_field_value(turkish_label, english_label=""):
        """Türkçe veya İngilizce label'dan değer al"""
        return (field_dict.get(turkish_label) or 
                field_dict.get(english_label) or 
                field_dict.get(turkish_label.lower()) or
                field_dict.get(english_label.lower()) or
                "")
    
    # Temel bilgiler
    extracted = {
        'submission_id': tally_data.get('data', {}).get('responseId', ''),
        'submitted_at': tally_data.get('createdAt', ''),
        
        # Kişisel bilgiler - Çok dilli
        'name': get_field_value('Adınız Soyadınız', 'Full Name'),
        'email': get_field_value('Mail Adresiniz', 'Email Address') or get_field_value('E-mail Adresiniz', 'Email Address'), 
        'phone': get_field_value('Telefon Numaranız', 'Phone Number'),
        
        # Kategori belirleme alanları - Çok dilli destek
        'ticari': (get_field_value('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Ticari Danışmanlık)', 
                                  'What type of consultation do you need? (Business Consulting)') == True),
        'egitim': (get_field_value('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Eğitim Danışmanlığı)', 
                                  'What type of consultation do you need? (Education Consulting)') == True),
        'hukuk': (get_field_value('Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Vize ve Hukuki Danışmanlık)', 
                                 'What type of consultation do you need? (Visa and Legal Consulting)') == True),
        
        # Eğitim alanları - Çok dilli
        'egitim_seviye': get_field_value('İlgilendiğiniz Eğitim Seviyesi', 'Education Level of Interest'),
        'lise': (get_field_value('İlgilendiğiniz Eğitim Seviyesi (Lise (İngiltere\'de lise eğitimi almak isteyenler için))', 
                                'Education Level (High School in the UK)') == True),
        'lisans': (get_field_value('İlgilendiğiniz Eğitim Seviyesi (Lisans (Üniversite eğitimi))', 
                                  'Education Level (Bachelor\'s Degree)') == True),
        'master': (get_field_value('İlgilendiğiniz Eğitim Seviyesi (Yüksek Lisans (Master programları))', 
                                  'Education Level (Master\'s Programs)') == True),
        'doktora': (get_field_value('İlgilendiğiniz Eğitim Seviyesi (Doktora (Phd programları))', 
                                   'Education Level (PhD Programs)') == True),
        'dil_okulu': (get_field_value('İlgilendiğiniz Eğitim Seviyesi (Dil Okulları (Yetişkinler için genel, IELTS veya mesleki İngilizce) )', 
                                     'Education Level (Language Schools)') == True),
        'yaz_kampi': (get_field_value('İlgilendiğiniz Eğitim Seviyesi (Yaz Kampı (12-18 yaş grubu))', 
                                     'Education Level (Summer Camp 12-18 years)') == True),
        'not_ortalama': get_field_value('Not Ortalamanız', 'Your GPA'),
        'butce': get_field_value('Eğitim ve Konaklama için Düşündüğünüz Bütçe Nedir? (£)', 'Budget for Education and Accommodation (£)'),
        
        # Hukuk alanları - Çok dilli
        'hukuk_konu': get_field_value('Hangi konularda hukuki destek almak istiyorsunuz?', 'What legal services do you need?'),
        'turistik_vize': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Turistik Vize (Visitor Visa))', 
                                         'Legal Services (UK Tourist Visa)') == True),
        'ogrenci_vize': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Öğrenci Vizesi (Tier 4 / Graduate Route))', 
                                        'Legal Services (UK Student Visa)') == True),
        'calisma_vize': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Çalışma Vizesi (Skilled Worker, Health and Care vb.))', 
                                        'Legal Services (UK Work Visa)') == True),
        'aile_vize': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Aile Birleşimi / Partner Vizesi)', 
                                     'Legal Services (UK Family/Partner Visa)') == True),
        'ilr': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere\'de Süresiz Oturum (ILR) Başvurusu)', 
                               'Legal Services (UK Indefinite Leave to Remain)') == True),
        'vatandaslik': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Vatandaşlık Başvurusu)', 
                                       'Legal Services (UK Citizenship Application)') == True),
        'vize_red': (get_field_value('Hangi konularda hukuki destek almak istiyorsunuz? (Vize Reddi İtiraz ve Yeniden Başvuru Danışmanlığı)', 
                                    'Legal Services (Visa Refusal Appeal)') == True),
        
        # Ticari alanları - Çok dilli
        'sirket_adi': get_field_value('Şirketinizin Adı', 'Company Name'),
        'sektor': get_field_value('Sektörünüz', 'Your Industry'),
        
        # Sektör detayları - Boolean kontrolü düzeltildi
        'ambalaj': field_dict.get('Sektörünüz (Ambalaj ve Baskı Ürünleri)', False) == True,
        'tekstil': field_dict.get('Sektörünüz (Tekstil ve Giyim)', False) == True,
        'ayakkabi': field_dict.get('Sektörünüz (Ayakkabı ve Deri Ürünleri)', False) == True,
        'mobilya': field_dict.get('Sektörünüz (Mobilya ve Ev Dekorasyonu)', False) == True,
        'gida': field_dict.get('Sektörünüz (Gıda Ürünleri / Yiyecek-İçecek)', False) == True,
        'taki': field_dict.get('Sektörünüz (Takı, Bijuteri ve Aksesuar)', False) == True,
        'hediye': field_dict.get('Sektörünüz (Hediyelik Eşya)', False) == True,
        'kozmetik': field_dict.get('Sektörünüz (Kozmetik ve Kişisel Bakım)', False) == True,
        'oyuncak': field_dict.get('Sektörünüz (Oyuncak ve Kırtasiye)', False) == True,
        'temizlik': field_dict.get('Sektörünüz (Temizlik ve Hijyen Ürünleri)', False) == True,
        'ev_gereci': field_dict.get('Sektörünüz (Ev Gereçleri ve Mutfak Ürünleri)', False) == True,
        'hirdavat': field_dict.get('Sektörünüz (Hırdavat / Yapı Malzemeleri)', False) == True,
        'otomotiv': field_dict.get('Sektörünüz (Otomotiv Yan Sanayi)', False) == True,
        'bahce': field_dict.get('Sektörünüz (Bahçe ve Outdoor Ürünleri)', False) == True,
        'diger_sektor': field_dict.get('Sektörünüz (Diğer)', False) == True
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
    name_parts = name.split(' ')
    firstname = name_parts[0] if name_parts else ''
    lastname = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
    
    return {
        'firstname': firstname,
        'lastname': lastname,
        'email': email,
        'phone': phone
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

def send_notification_email(contact_info, category, extracted_data):
    """Kategori bazlı bildirim maili gönder"""
    
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("⚠️ Email ayarları bulunamadı")
        return {"success": False, "error": "Email ayarları bulunamadı"}
    
    try:
        # Mail içeriği oluştur
        subject, body, recipients = create_email_content(contact_info, category, extracted_data)
        
        # SMTP bağlantısı
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        # Her alıcıya mail gönder
        results = []
        for recipient in recipients:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            try:
                server.send_message(msg)
                results.append({"recipient": recipient, "status": "success"})
                print(f"✅ Mail gönderildi: {recipient}")
            except Exception as e:
                results.append({"recipient": recipient, "status": "failed", "error": str(e)})
                print(f"❌ Mail gönderilemedi {recipient}: {str(e)}")
        
        server.quit()
        return {"success": True, "results": results}
        
    except Exception as e:
        print(f"❌ Email hatası: {str(e)}")
        return {"success": False, "error": str(e)}

def create_email_content(contact_info, category, extracted_data):
    """Mail içeriği ve alıcıları oluştur"""
    
    # Alıcıları belirle - Kategori bazlı
    recipients = [ADMIN_EMAIL]  # Admin her zaman alır
    
    if category == 'education' and EDUCATION_PARTNER_EMAIL:
        recipients.append(EDUCATION_PARTNER_EMAIL)
    elif category == 'legal' and LEGAL_PARTNER_EMAIL:
        recipients.append(LEGAL_PARTNER_EMAIL)
    # Business sadece admin'e gider
    
    # Subject oluştur
    category_tr = {
        'education': 'Eğitim',
        'legal': 'Hukuk', 
        'business': 'Ticari'
    }
    
    subject = f"🔔 Yeni {category_tr.get(category, 'Genel')} Başvurusu - {contact_info['firstname']} {contact_info['lastname']}"
    
    # HTML Body oluştur
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .info-box {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; }}
            .category-education {{ border-left-color: #28a745; }}
            .category-legal {{ border-left-color: #dc3545; }}
            .category-business {{ border-left-color: #ffc107; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 British Global - Yeni Başvuru</h1>
            <p>{category_tr.get(category, 'Genel')} Danışmanlık Talebi</p>
        </div>
        
        <div class="content">
            <div class="info-box category-{category}">
                <h2>📋 Başvuru Bilgileri</h2>
                <p><strong>Kategori:</strong> {category_tr.get(category, 'Genel')} Danışmanlık</p>
                <p><strong>Tarih:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Submission ID:</strong> {extracted_data.get('submission_id', 'N/A')}</p>
            </div>
            
            <h2>👤 İletişim Bilgileri</h2>
            <table>
                <tr><th>Ad Soyad</th><td>{contact_info['firstname']} {contact_info['lastname']}</td></tr>
                <tr><th>Email</th><td><a href="mailto:{contact_info['email']}">{contact_info['email']}</a></td></tr>
                <tr><th>Telefon</th><td><a href="tel:{contact_info['phone']}">{contact_info['phone']}</a></td></tr>
            </table>
    """
    
    # Kategori özel bilgileri ekle
    if category == 'education':
        education_details = get_education_details(extracted_data)
        body += f"""
            <h2>🎓 Eğitim Detayları</h2>
            <table>
                <tr><th>İlgilenilen Program</th><td>{education_details['education_programs'] or 'Belirtilmemiş'}</td></tr>
                <tr><th>Not Ortalaması</th><td>{education_details['gpa'] or 'Belirtilmemiş'}</td></tr>
                <tr><th>Bütçe</th><td>£{education_details['budget']:,} </td></tr>
            </table>
        """
        
        # Detaylı program bilgisi
        programs = []
        if extracted_data.get('doktora'): programs.append('🎯 Doktora (PhD)')
        if extracted_data.get('master'): programs.append('🎓 Yüksek Lisans (Master)')
        if extracted_data.get('lisans'): programs.append('📚 Lisans')
        if extracted_data.get('lise'): programs.append('🏫 Lise')
        if extracted_data.get('dil_okulu'): programs.append('🗣️ Dil Okulu')
        if extracted_data.get('yaz_kampi'): programs.append('🏕️ Yaz Kampı')
        
        if programs:
            body += f"""
                <div class="info-box">
                    <h3>Seçilen Programlar:</h3>
                    <ul>{''.join(f'<li>{p}</li>' for p in programs)}</ul>
                </div>
            """
    
    elif category == 'legal':
        legal_details = get_legal_details(extracted_data)
        body += f"""
            <h2>⚖️ Hukuk Detayları</h2>
            <table>
                <tr><th>Hukuki Hizmetler</th><td>{legal_details['legal_services'] or 'Belirtilmemiş'}</td></tr>
                <tr><th>Açıklama</th><td>{legal_details['legal_topic'] or 'Belirtilmemiş'}</td></tr>
            </table>
        """
        
        # Detaylı hizmet listesi
        services = []
        if extracted_data.get('turistik_vize'): services.append('🧳 Turistik Vize')
        if extracted_data.get('ogrenci_vize'): services.append('🎓 Öğrenci Vizesi')
        if extracted_data.get('calisma_vize'): services.append('💼 Çalışma Vizesi')
        if extracted_data.get('aile_vize'): services.append('👨‍👩‍👧‍👦 Aile Birleşimi')
        if extracted_data.get('ilr'): services.append('🏠 Süresiz Oturum (ILR)')
        if extracted_data.get('vatandaslik'): services.append('🇬🇧 Vatandaşlık')
        if extracted_data.get('vize_red'): services.append('❌ Vize Red İtiraz')
        
        if services:
            body += f"""
                <div class="info-box">
                    <h3>İhtiyaç Duyulan Hizmetler:</h3>
                    <ul>{''.join(f'<li>{s}</li>' for s in services)}</ul>
                </div>
            """
    
    elif category == 'business':
        business_details = get_business_details(extracted_data)
        body += f"""
            <h2>💼 Ticari Detaylar</h2>
            <table>
                <tr><th>Şirket Adı</th><td>{business_details['company_name'] or 'Belirtilmemiş'}</td></tr>
                <tr><th>Sektör</th><td>{business_details['sector'] or 'Belirtilmemiş'}</td></tr>
                <tr><th>Sektör Detayları</th><td>{business_details['sector_details'] or 'Belirtilmemiş'}</td></tr>
            </table>
        """
    
    # Footer ekle
    body += f"""
            <div class="info-box">
                <h3>🚀 Sonraki Adımlar</h3>
                <p>Bu başvuru HubSpot sistemine kaydedildi. Müşteriyi 24 saat içinde aramayı unutmayın!</p>
                <p><strong>HubSpot Contact ID:</strong> Yakında eklenecek</p>
            </div>
        </div>
        
        <div class="footer">
            <p>Bu mail British Global webhook sistemi tarafından otomatik oluşturulmuştur.</p>
            <p>📧 {', '.join(recipients)} adreslerine gönderildi</p>
        </div>
    </body>
    </html>
    """
    
    return subject, body, recipients
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
    """HubSpot'a contact kaydet - DOĞRU field names ile"""
    
    if not HUBSPOT_API_KEY:
        print("⚠️ HubSpot API Key bulunamadı")
        return {"success": False, "error": "API Key bulunamadı"}
    
    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # DOĞRU HubSpot field names
    properties = {
        "email": contact_info['email'],
        "firstname": contact_info['firstname'] or "",
        "lastname": contact_info['lastname'] or "", 
        "phone": contact_info['phone'],
        "lifecyclestage": "lead",
        "hs_lead_status": "NEW",
        "jobtitle": f"{category.title()} Başvurusu"
    }
    
    # Eğitim kategorisi için özel alanlar ekle
    if category == 'education':
        education_details = get_education_details(extracted_data)
        
        # HubSpot custom properties (bu alanları HubSpot'ta oluşturmanız gerekebilir)
        if education_details['gpa']:
            # GPA'yı number olarak gönder (HubSpot'ta Number field olarak oluşturuldu)
            try:
                properties["gpa"] = float(education_details['gpa'])
            except (ValueError, TypeError):
                properties["gpa"] = education_details['gpa']  # String olarak gönder
        
        if education_details['budget']:
            # Budget'ı number olarak gönder
            try:
                properties["budget"] = float(education_details['budget'])
            except (ValueError, TypeError):
                properties["budget"] = str(education_details['budget'])
            
        if education_details['education_programs']:
            properties["education_level"] = education_details['education_programs']
    
    # Business kategorisi için şirket bilgileri
    elif category == 'business':
        business_details = get_business_details(extracted_data)
        if business_details['sector_details']:
            properties["industry"] = business_details['sector_details']
    
    # Legal kategorisi için hukuk bilgileri  
    elif category == 'legal':
        legal_details = get_legal_details(extracted_data)
        if legal_details['legal_services']:
            properties["legal_service_type"] = legal_details['legal_services']
    
    # Company field - kategori bazlı
    if category == 'business' and extracted_data.get('sirket_adi'):
        properties["company"] = extracted_data.get('sirket_adi')
    else:
        properties["company"] = f"British Global - {category.title()}"
    
    # Temizle - boş değerleri kaldır
    properties = {k: v for k, v in properties.items() if v and v != ""}
    
    # Debug
    print(f"📋 HubSpot Properties:")
    for key, value in properties.items():
        print(f"  {key}: {value}")
    
    payload = {"properties": properties}
    
    try:
        # 1. Contact oluştur
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            contact_id = result.get('id')
            print(f"✅ Contact oluşturuldu - ID: {contact_id}")
            
            # 2. Note ekle (ayrı API call)
            note_result = create_hubspot_note(contact_id, category, extracted_data)
            
            return {
                "success": True,
                "contact_id": contact_id,
                "properties_sent": properties,
                "note_result": note_result
            }
        else:
            print(f"❌ HubSpot hatası: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        return {"success": False, "error": str(e)}

def create_hubspot_note(contact_id, category, extracted_data):
    """HubSpot contact'a note ekle - AYRI API"""
    
    # Detaylı note içeriği oluştur
    note_body = f"🎯 BRITISH GLOBAL - {category.upper()}\n"
    note_body += f"📅 Başvuru: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    
    if category == 'education':
        education_details = get_education_details(extracted_data)
        note_body += "🎓 EĞİTİM DANIŞMANLIĞI\n"
        if education_details['education_programs']:
            note_body += f"📚 Program: {education_details['education_programs']}\n"
        if education_details['gpa']:
            note_body += f"📊 Not Ortalaması: {education_details['gpa']}\n"
        if education_details['budget']:
            note_body += f"💰 Bütçe: £{education_details['budget']:,}\n"
        
        # Detaylı program listesi
        if extracted_data.get('doktora'):
            note_body += "🎯 Seviye: Doktora (PhD programları)\n"
        elif extracted_data.get('master'):
            note_body += "🎯 Seviye: Yüksek Lisans (Master)\n"
        elif extracted_data.get('lisans'):
            note_body += "🎯 Seviye: Lisans (Üniversite)\n"
        elif extracted_data.get('lise'):
            note_body += "🎯 Seviye: Lise\n"
        elif extracted_data.get('dil_okulu'):
            note_body += "🎯 Seviye: Dil Okulu\n"
        elif extracted_data.get('yaz_kampi'):
            note_body += "🎯 Seviye: Yaz Kampı\n"
    
    elif category == 'legal':
        legal_details = get_legal_details(extracted_data)
        note_body += "⚖️ HUKUK DANIŞMANLIĞI\n"
        if legal_details['legal_services']:
            note_body += f"📋 Hukuki Hizmetler: {legal_details['legal_services']}\n"
        if legal_details['legal_topic']:
            note_body += f"📝 Konu: {legal_details['legal_topic']}\n"
    
    elif category == 'business':
        business_details = get_business_details(extracted_data)
        note_body += "💼 TİCARİ DANIŞMANLIK\n"
        if business_details['company_name']:
            note_body += f"🏢 Şirket: {business_details['company_name']}\n"
        if business_details['sector']:
            note_body += f"🏭 Sektör: {business_details['sector']}\n"
        if business_details['sector_details']:
            note_body += f"📈 Sektör Detayları: {business_details['sector_details']}\n"
    
    # Note API call
    note_url = "https://api.hubapi.com/crm/v3/objects/notes"
    note_headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    note_payload = {
        "properties": {
            "hs_note_body": note_body,
            "hs_timestamp": datetime.now().isoformat()
        },
        "associations": [
            {
                "to": {"id": str(contact_id)},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 202  # note_to_contact
                    }
                ]
            }
        ]
    }
    
    try:
        note_response = requests.post(note_url, headers=note_headers, json=note_payload)
        
        if note_response.status_code in [200, 201]:
            note_result = note_response.json()
            note_id = note_result.get('id')
            print(f"✅ Note eklendi - ID: {note_id}")
            return {"success": True, "note_id": note_id}
        else:
            print(f"❌ Note hatası: {note_response.status_code} - {note_response.text}")
            return {"success": False, "error": note_response.text}
            
    except Exception as e:
        print(f"❌ Note hatası: {str(e)}")
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
        
        # Email bildirim gönder
        email_result = send_notification_email(contact, category, extracted)
        
        print("=" * 60)
        
        # Başarılı response
        return jsonify({
            "status": "success",
            "message": "Form verisi başarıyla işlendi ve HubSpot'a kaydedildi",
            "category": category,
            "contact": contact,
            "hubspot": hubspot_result,
            "email": email_result,
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
    """Test için endpoint - Error handling ile"""
    data = request.json
    
    try:
        # Test verisi ile form mapping dene
        extracted = extract_form_data(data)
        category = determine_category(extracted)
        contact = get_contact_info(extracted)
        
        # Debug print
        print(f"Debug - Contact: {contact}")
        print(f"Debug - Category: {category}")
        
        # HubSpot'a test kaydı gönder (email kontrolü ile)
        hubspot_result = {"message": "Email bulunamadı, HubSpot'a gönderilmedi"}
        email_result = {"message": "Test modu - email gönderilmedi"}
        
        if contact and contact.get('email'):
            hubspot_result = save_to_hubspot(contact, category, extracted)
            # Test modunda email göndermeyi aktif etmek isterseniz açın:
            # email_result = send_notification_email(contact, category, extracted)
        
        return jsonify({
            "message": "Test başarılı!",
            "received": data,
            "extracted": extracted,
            "category": category,
            "contact": contact,
            "hubspot": hubspot_result,
            "email": email_result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Test endpoint hatası: {str(e)}")
        return jsonify({
            "error": f"Test failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)