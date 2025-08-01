from flask import Flask, request, jsonify
import json
import os
import logging
from datetime import datetime

# Import fix - relative imports kullan
try:
    from email_services.education_email import EducationEmailService
    from email_services.legal_email import LegalEmailService
    from email_services.business_email import BusinessEmailService
    from services.hubspot_service import HubSpotService
    from utils.form_processor import FormProcessor
    from config.settings import Config
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback - local import
    import sys
    sys.path.append(os.path.dirname(__file__))
    
    from email_services.education_email import EducationEmailService
    from email_services.legal_email import LegalEmailService  
    from email_services.business_email import BusinessEmailService
    from services.hubspot_service import HubSpotService
    from utils.form_processor import FormProcessor
    from config.settings import Config

app = Flask(__name__)

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Servisler - Lazy loading ile
hubspot_service = None
form_processor = None
email_services = {}

def initialize_services():
    """Servisleri lazy loading ile başlat"""
    global hubspot_service, form_processor, email_services
    
    if hubspot_service is None:
        hubspot_service = HubSpotService(Config.HUBSPOT_API_KEY)
        form_processor = FormProcessor()
        
        # Email servisleri
        email_services = {
            'education': EducationEmailService(Config.EMAIL_CONFIG),
            'legal': LegalEmailService(Config.EMAIL_CONFIG),
            'business': BusinessEmailService(Config.EMAIL_CONFIG)
        }
        
        logger.info("Services initialized successfully")

# Global state management
processed_submissions = set()

@app.route("/tally", methods=["POST"])
def tally_webhook():
    """Ana Tally webhook endpoint"""
    
    # Servisleri başlat
    initialize_services()
    
    try:
        # Input validation
        if not request.is_json:
            logger.warning(f"Invalid content type: {request.content_type}")
            return jsonify({
                "success": False,
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json(force=True)
        if not data:
            logger.warning("Empty JSON data received")
            return jsonify({
                "success": False,
                "error": "Empty JSON data"
            }), 400
        
        logger.info("=" * 60)
        logger.info(f"NEW TALLY WEBHOOK - {datetime.now()}")
        logger.info(f"Received data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        # Form verilerini işle
        extracted_data = form_processor.extract_form_data(data)
        if not extracted_data:
            logger.error("Could not extract form data")
            return jsonify({
                "success": False,
                "error": "Could not extract form data"
            }), 400
        
        # Kategori belirle
        category = form_processor.determine_category(extracted_data)
        logger.info(f"Category determined: {category}")
        
        # İletişim bilgileri
        contact_info = form_processor.get_contact_info(extracted_data)
        logger.info(f"Contact: {contact_info['firstname']} {contact_info['lastname']} - {contact_info['email']}")
        
        # Email kontrolü
        if not contact_info.get('email'):
            logger.error("No email found in submission")
            return jsonify({
                "success": False,
                "error": "Email address required"
            }), 400
        
        # Duplicate kontrolü
        submission_id = extracted_data.get('submission_id', '')
        if submission_id and submission_id in processed_submissions:
            logger.info(f"Duplicate submission ignored: {submission_id}")
            return jsonify({
                "success": True,
                "message": "Duplicate submission ignored",
                "submission_id": submission_id
            }), 200
        
        # İşlem sonuçları
        results = {
            "submission_id": submission_id,
            "category": category,
            "contact": contact_info,
            "hubspot": {"success": False},
            "email": {"success": False}
        }
        
        # HubSpot'a kaydet
        try:
            logger.info("Processing HubSpot integration...")
            hubspot_result = hubspot_service.save_contact(
                contact_info, category, extracted_data
            )
            results['hubspot'] = hubspot_result
            logger.info(f"HubSpot: {hubspot_result.get('success', False)}")
            
        except Exception as hubspot_error:
            logger.error(f"HubSpot error: {str(hubspot_error)}")
            results['hubspot'] = {"success": False, "error": str(hubspot_error)}
        
        # Email gönder (kategori bazlı)
        try:
            logger.info(f"Processing {category} email notifications...")
            email_service = email_services.get(category)
            
            if email_service:
                email_result = email_service.send_notification(
                    contact_info, extracted_data, results['hubspot']
                )
                results['email'] = email_result
                logger.info(f"Email: {email_result.get('success', False)}")
                
                # Otomatik onay maili gönder (kategori bazlı)
                try:
                    confirmation_result = email_service.send_application_confirmation(
                        contact_info, extracted_data
                    )
                    results['confirmation_email'] = confirmation_result
                    logger.info(f"Confirmation email: {confirmation_result.get('success', False)}")
                except Exception as conf_error:
                    logger.error(f"Confirmation email error: {str(conf_error)}")
                    results['confirmation_email'] = {"success": False, "error": str(conf_error)}
                
            else:
                logger.warning(f"No email service found for category: {category}")
                results['email'] = {"success": False, "error": "No email service for category"}
                
        except Exception as email_error:
            logger.error(f"Email error: {str(email_error)}")
            results['email'] = {"success": False, "error": str(email_error)}
        
        # Başarılı işlem olarak kaydet
        if submission_id:
            processed_submissions.add(submission_id)
        
        logger.info("Webhook processing completed successfully")
        logger.info("=" * 60)
        
        # Tally için standart response
        return jsonify({
            "success": True,
            "message": "Webhook processed successfully",
            "submission_id": submission_id,
            "category": category,
            "results": {
                "hubspot": results['hubspot'].get('success', False),
                "email": results['email'].get('success', False),
                "confirmation": results.get('confirmation_email', {}).get('success', False)
            },
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"CRITICAL WEBHOOK ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Tally için 200 dön (retry prevention)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 200

@app.route("/", methods=["GET"])
def health_check():
    """Sistem sağlık kontrolü"""
    
    # Servisleri başlat
    initialize_services()
    
    # Servis durumları
    services_status = {
        "hubspot": "✅ Ready" if Config.HUBSPOT_API_KEY else "❌ Not configured",
        "email": "✅ Ready" if Config.EMAIL_CONFIG.get('user') else "❌ Not configured",
        "education_partner": "✅ Ready" if Config.EDUCATION_PARTNER_EMAIL else "❌ Not configured",
        "legal_partner": "✅ Ready" if Config.LEGAL_PARTNER_EMAIL else "❌ Not configured"
    }
    
    return jsonify({
        "status": "OK",
        "service": "British Global Webhook System",
        "version": "6.0 - Modular Architecture",
        "services": services_status,
        "endpoints": {
            "/tally": "Main Tally webhook (POST)",
            "/test/<category>": "Test category-specific emails (POST)",
            "/debug": "Debug webhook data (POST)",
            "/health/<service>": "Individual service health checks (GET)"
        },
        "processed_submissions": len(processed_submissions),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/test/<category>", methods=["POST"])
def test_category_email(category):
    """Kategori bazlı email test"""
    
    initialize_services()
    
    if category not in email_services:
        return jsonify({
            "error": f"Invalid category. Available: {list(email_services.keys())}"
        }), 400
    
    try:
        # Test verisi oluştur
        test_contact = {
            "firstname": "Test",
            "lastname": "User",
            "fullname": "Test User",
            "email": "test@example.com",
            "phone": "+90 555 123 4567"
        }
        
        # Kategori bazlı test data
        if category == 'education':
            test_data = {
                "submission_id": f"test_edu_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "submitted_at": datetime.now().isoformat(),
                "education": {
                    "programs": ["Yüksek Lisans (Master)", "Dil Okulu"],
                    "programs_text": "Yüksek Lisans (Master), Dil Okulu",
                    "gpa": "3.2",
                    "budget": "25000",
                    "budget_formatted": "£25,000",
                    "priority_level": "high"
                }
            }
        elif category == 'legal':
            test_data = {
                "submission_id": f"test_legal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "submitted_at": datetime.now().isoformat(),
                "legal": {
                    "selected_services": ["ogrenci_vize", "turistik_vize"],
                    "services_text": "Öğrenci Vizesi (Student), Turistik Vize (Visitor)",
                    "topic": "Üniversite başvurusu için vize gerekli",
                    "urgency_level": "high"
                }
            }
        elif category == 'business':
            test_data = {
                "submission_id": f"test_biz_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "submitted_at": datetime.now().isoformat(),
                "business": {
                    "company_name": "Test Tekstil Ltd",
                    "sector": "Tekstil",
                    "sectors": ["Tekstil ve Giyim", "Ayakkabı ve Deri"],
                    "sectors_text": "Tekstil ve Giyim, Ayakkabı ve Deri",
                    "business_type": "consumer_goods",
                    "requires_meeting": True
                }
            }
        
        # Test email gönder
        email_service = email_services[category]
        result = email_service.send_notification(test_contact, test_data, {"success": True, "contact_id": "test123"})
        
        return jsonify({
            "status": "SUCCESS",
            "category": category,
            "test_result": result,
            "test_data": test_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Test error for {category}: {str(e)}")
        return jsonify({
            "status": "FAILED",
            "category": category,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/health/<service>", methods=["GET"])
def service_health_check(service):
    """Bireysel servis sağlık kontrolü"""
    
    initialize_services()
    
    try:
        if service == "hubspot":
            result = hubspot_service.test_connection()
        elif service == "email":
            # Base email service test
            from email_services.base_email import BaseEmailService
            base_service = BaseEmailService(Config.EMAIL_CONFIG)
            result = base_service.test_smtp_connection()
        elif service in email_services:
            result = email_services[service].test_service()
        else:
            return jsonify({
                "error": f"Unknown service: {service}",
                "available": ["hubspot", "email", "education", "legal", "business"]
            }), 404
        
        return jsonify({
            "service": service,
            "status": "OK" if result.get("success") else "FAILED",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check error for {service}: {str(e)}")
        return jsonify({
            "service": service,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/debug", methods=["POST"])
def debug_webhook():
    """Webhook veri analizi"""
    
    initialize_services()
    
    try:
        data = request.get_json(force=True)
        
        # Form processor ile analiz et
        extracted = form_processor.extract_form_data(data)
        category = form_processor.determine_category(extracted)
        contact = form_processor.get_contact_info(extracted)
        
        debug_info = {
            "request_analysis": {
                "content_type": request.content_type,
                "method": request.method,
                "data_keys": list(data.keys()) if isinstance(data, dict) else "Not a dict",
                "has_data_section": "data" in data if isinstance(data, dict) else False
            },
            "form_analysis": {
                "extracted_fields": len(extracted),
                "category": category,
                "has_email": bool(contact.get('email')),
                "has_name": bool(contact.get('firstname')),
                "contact_valid": contact.get('valid', False)
            },
            "raw_data": data,
            "extracted_data": extracted,
            "contact_info": contact,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        return jsonify({
            "status": "DEBUG_ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/config", methods=["GET"])
def config_check():
    """Konfigürasyon kontrolü"""
    
    missing_configs = Config.validate_config()
    
    config_status = {
        "hubspot_api": "✅ Configured" if Config.HUBSPOT_API_KEY else "❌ Missing HUBSPOT_API_KEY",
        "email_user": "✅ Configured" if Config.EMAIL_CONFIG.get('user') else "❌ Missing EMAIL_USER",
        "email_password": "✅ Configured" if Config.EMAIL_CONFIG.get('password') else "❌ Missing EMAIL_PASSWORD",
        "admin_email": "✅ Configured" if Config.ADMIN_EMAIL else "❌ Missing ADMIN_EMAIL",
        "education_partner": "✅ Configured" if Config.EDUCATION_PARTNER_EMAIL else "⚠️ Optional",
        "legal_partner": "✅ Configured" if Config.LEGAL_PARTNER_EMAIL else "⚠️ Optional",
        "business_meeting_link": "✅ Configured" if Config.BUSINESS_MEETING_LINK else "⚠️ Optional"
    }
    
    return jsonify({
        "configuration_status": config_status,
        "missing_required": missing_configs,
        "ready_for_production": len(missing_configs) == 0,
        "environment_variables": {
            "total_configured": len([k for k, v in config_status.items() if "✅" in v]),
            "required_missing": len(missing_configs),
            "optional_missing": len([k for k, v in config_status.items() if "⚠️" in v])
        },
        "timestamp": datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "/": "Health check (GET)",
            "/tally": "Main webhook (POST)",
            "/test/<category>": "Test category email (POST)",
            "/health/<service>": "Service health check (GET)",
            "/debug": "Debug webhook data (POST)",
            "/config": "Configuration check (GET)"
        }
    }), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "error": "Method not allowed",
        "message": "Check the HTTP method (GET/POST) for this endpoint"
    }), 405

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on the server",
        "timestamp": datetime.now().isoformat()
    }), 500

# Bu kodu mevcut main.py dosyanızın sonuna, if __name__ == "__main__": satırından önce ekleyin

@app.route("/debug", methods=["POST"])
def debug_webhook():
    """Debug webhook data"""
    try:
        data = request.get_json(force=True)
        
        print(f"🔍 DEBUG - Received data: {data}")
        
        # Mevcut extract_form_data fonksiyonunuzu kullanın
        extracted = extract_form_data(data)
        category = determine_category(extracted)
        contact = get_contact_info(extracted)
        
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "received_data": data,
            "extracted_data": extracted,
            "category": category,
            "contact_info": contact,
            "data_analysis": {
                "has_data_section": "data" in data if isinstance(data, dict) else False,
                "fields_count": len(data.get("data", {}).get("fields", [])) if isinstance(data, dict) else 0,
                "has_email": bool(contact.get('email')) if contact else False
            }
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/config-check", methods=["GET"])
def config_check():
    """Environment variables kontrolü"""
    
    # Mevcut environment variable'larınızı kontrol edin
    config_status = {
        "HUBSPOT_API_KEY": "✅ Set" if os.environ.get('HUBSPOT_API_KEY') else "❌ Missing",
        "EMAIL_USER": os.environ.get('EMAIL_USER', '❌ Missing'),
        "EMAIL_PASSWORD": "✅ Set" if os.environ.get('EMAIL_PASSWORD') else "❌ Missing",
        "ADMIN_EMAIL": os.environ.get('ADMIN_EMAIL', '❌ Missing'),
        "EDUCATION_PARTNER_EMAIL": os.environ.get('EDUCATION_PARTNER_EMAIL', '❌ Missing'),
        "LEGAL_PARTNER_EMAIL": os.environ.get('LEGAL_PARTNER_EMAIL', '❌ Missing')
    }
    
    missing_count = len([k for k, v in config_status.items() if "❌" in str(v)])
    
    return jsonify({
        "config_status": config_status,
        "missing_configs": missing_count,
        "ready_for_production": missing_count <= 2,  # Partner email'ler opsiyonel
        "timestamp": datetime.now().isoformat()
    })

@app.route("/test-tally", methods=["POST"])
def test_tally_format():
    """Tally format test"""
    try:
        # Basit test data - mevcut extract fonksiyonunuzu test eder
        test_data = {
            "eventId": f"test_{int(datetime.now().timestamp())}",
            "eventType": "form_response", 
            "createdAt": datetime.now().isoformat(),
            "data": {
                "responseId": f"test_{int(datetime.now().timestamp())}",
                "createdAt": datetime.now().isoformat(),
                "fields": [
                    {"label": "Adınız Soyadınız", "value": "Test User"},
                    {"label": "Mail Adresiniz", "value": "test@britishglobal.com.tr"},
                    {"label": "Telefon Numaranız", "value": "+90 555 123 4567"},
                    {"label": "Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Eğitim Danışmanlığı)", "value": True}
                ]
            }
        }
        
        # Mevcut webhook fonksiyonunuzu çağır (ama gerçek email/hubspot göndermeden)
        extracted = extract_form_data(test_data)
        category = determine_category(extracted)
        contact = get_contact_info(extracted)
        
        return jsonify({
            "status": "SUCCESS",
            "message": "Tally format test completed",
            "test_data": test_data,
            "extracted": extracted,
            "category": category,
            "contact": contact,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "FAILED",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500



if __name__ == "__main__":
    # Environment check
    missing_configs = Config.validate_config()
    if missing_configs:
        logger.warning(f"Missing configurations: {missing_configs}")
        logger.warning("Some features may not work properly")
    else:
        logger.info("All required configurations are present")
    
    # Development mode
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    if debug_mode:
        app.config['DEBUG'] = True
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Running in DEBUG mode")
    
    logger.info("British Global Webhook System starting...")
    
    # Port configuration
    port = int(os.environ.get('PORT', 8080))
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)