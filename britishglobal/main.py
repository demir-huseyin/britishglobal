from flask import Flask, request, jsonify
import json
import os
import logging
from datetime import datetime

# Import fix - try-catch ile güvenli import
try:
    from email_services.education_email import EducationEmailService
    from email_services.legal_email import LegalEmailService
    from email_services.business_email import BusinessEmailService
    from services.hubspot_service import HubSpotService
    from utils.form_processor import FormProcessor
    from config.settings import Config
    IMPORTS_SUCCESS = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_SUCCESS = False
    
    # Fallback config
    class Config:
        HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY', '')
        EMAIL_CONFIG = {
            'user': os.environ.get('EMAIL_USER', ''),
            'password': os.environ.get('EMAIL_PASSWORD', ''),
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'from_name': 'British Global'
        }
        ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')
        EDUCATION_PARTNER_EMAIL = os.environ.get('EDUCATION_PARTNER_EMAIL', '')
        LEGAL_PARTNER_EMAIL = os.environ.get('LEGAL_PARTNER_EMAIL', '')
        BUSINESS_MEETING_LINK = 'https://calendly.com/britishglobal/business-consultation'
        
        @classmethod
        def validate_config(cls):
            missing = []
            if not cls.HUBSPOT_API_KEY:
                missing.append('HUBSPOT_API_KEY')
            if not cls.EMAIL_CONFIG['user']:
                missing.append('EMAIL_USER')
            if not cls.EMAIL_CONFIG['password']:
                missing.append('EMAIL_PASSWORD')
            if not cls.ADMIN_EMAIL:
                missing.append('ADMIN_EMAIL')
            return missing

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
        try:
            if IMPORTS_SUCCESS:
                hubspot_service = HubSpotService(Config.HUBSPOT_API_KEY)
                form_processor = FormProcessor()
                
                # Email servisleri
                email_services = {
                    'education': EducationEmailService(Config.EMAIL_CONFIG),
                    'legal': LegalEmailService(Config.EMAIL_CONFIG),
                    'business': BusinessEmailService(Config.EMAIL_CONFIG)
                }
                logger.info("Services initialized successfully")
            else:
                logger.warning("Services could not be initialized due to import errors")
        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}")

# Global state management
processed_submissions = set()

@app.route("/tally", methods=["POST"])
def tally_webhook():
    """Ana Tally webhook endpoint"""
    
    try:
        # Servisleri başlat
        initialize_services()
        
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
        
        # Basit response eğer servisler çalışmıyorsa
        if not IMPORTS_SUCCESS or not form_processor:
            logger.warning("Services not available, returning basic response")
            return jsonify({
                "success": True,
                "message": "Webhook received (limited mode)",
                "timestamp": datetime.now().isoformat()
            }), 200
        
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
        if hubspot_service:
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
        if email_services:
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
    
    # Servis durumları
    services_status = {
        "imports": "✅ Success" if IMPORTS_SUCCESS else "❌ Failed",
        "hubspot": "✅ Ready" if Config.HUBSPOT_API_KEY else "❌ Not configured",
        "email": "✅ Ready" if Config.EMAIL_CONFIG.get('user') else "❌ Not configured",
        "education_partner": "✅ Ready" if Config.EDUCATION_PARTNER_EMAIL else "❌ Not configured",
        "legal_partner": "✅ Ready" if Config.LEGAL_PARTNER_EMAIL else "❌ Not configured"
    }
    
    return jsonify({
        "status": "OK",
        "service": "British Global Webhook System",
        "version": "6.1 - Import Safe",
        "imports_successful": IMPORTS_SUCCESS,
        "services": services_status,
        "endpoints": {
            "/tally": "Main Tally webhook (POST)",
            "/config": "Configuration check (GET)",
            "/debug": "Debug webhook data (POST)"
        },
        "processed_submissions": len(processed_submissions),
        "timestamp": datetime.now().isoformat()
    })

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
        "imports_successful": IMPORTS_SUCCESS,
        "configuration_status": config_status,
        "missing_required": missing_configs,
        "ready_for_production": len(missing_configs) == 0 and IMPORTS_SUCCESS,
        "environment_variables": {
            "total_configured": len([k for k, v in config_status.items() if "✅" in v]),
            "required_missing": len(missing_configs),
            "optional_missing": len([k for k, v in config_status.items() if "⚠️" in v])
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route("/debug", methods=["POST"])
def debug_webhook():
    """Webhook veri analizi"""
    
    try:
        data = request.get_json(force=True)
        
        debug_info = {
            "request_analysis": {
                "content_type": request.content_type,
                "method": request.method,
                "data_keys": list(data.keys()) if isinstance(data, dict) else "Not a dict",
                "has_data_section": "data" in data if isinstance(data, dict) else False
            },
            "system_status": {
                "imports_successful": IMPORTS_SUCCESS,
                "services_initialized": hubspot_service is not None
            },
            "raw_data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Form processing (eğer mümkünse)
        if IMPORTS_SUCCESS and form_processor:
            try:
                initialize_services()
                extracted = form_processor.extract_form_data(data)
                category = form_processor.determine_category(extracted)
                contact = form_processor.get_contact_info(extracted)
                
                debug_info["form_analysis"] = {
                    "extracted_fields": len(extracted),
                    "category": category,
                    "has_email": bool(contact.get('email')),
                    "has_name": bool(contact.get('firstname')),
                    "contact_valid": contact.get('valid', False)
                }
                debug_info["extracted_data"] = extracted
                debug_info["contact_info"] = contact
                
            except Exception as e:
                debug_info["form_processing_error"] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        return jsonify({
            "status": "DEBUG_ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "/": "Health check (GET)",
            "/tally": "Main webhook (POST)",
            "/config": "Configuration check (GET)",
            "/debug": "Debug webhook data (POST)"
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

if __name__ == "__main__":
    # Environment check
    try:
        missing_configs = Config.validate_config()
        if missing_configs:
            logger.warning(f"Missing configurations: {missing_configs}")
        else:
            logger.info("All required configurations are present")
    except Exception as e:
        logger.error(f"Config validation error: {str(e)}")
    
    logger.info(f"British Global Webhook System starting... (Imports: {'✅' if IMPORTS_SUCCESS else '❌'})")
    
    # Port configuration
    port = int(os.environ.get('PORT', 8080))
    
    app.run(host="0.0.0.0", port=port, debug=False)