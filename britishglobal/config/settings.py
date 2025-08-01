import os
from typing import Dict, List, Optional

class Config:
    """Merkezi konfigürasyon sınıfı - Google Cloud Environment Variables ile"""
    
    # HubSpot API
    HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY', '')
    
    # Email Configuration - Google Cloud'dan
    EMAIL_CONFIG = {
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
        'user': os.environ.get('EMAIL_USER', ''),  # info@britishglobal.com.tr
        'password': os.environ.get('EMAIL_PASSWORD', ''),  # Google Cloud'dan
        'from_name': 'British Global'
    }
    
    # Email Recipients - Google Cloud'dan
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')
    EDUCATION_PARTNER_EMAIL = os.environ.get('EDUCATION_PARTNER_EMAIL', '')
    LEGAL_PARTNER_EMAIL = os.environ.get('LEGAL_PARTNER_EMAIL', '')
    
    # Business specific settings
    BUSINESS_MEETING_LINK = os.environ.get('BUSINESS_MEETING_LINK', 'https://calendly.com/britishglobal/business-consultation')
    
    # System settings
    DUPLICATE_PREVENTION = True
    WEBHOOK_TIMEOUT = 30  # seconds
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Eksik konfigürasyonları kontrol et"""
        missing = []
        
        # Zorunlu alanlar
        if not cls.HUBSPOT_API_KEY:
            missing.append('HUBSPOT_API_KEY')
        
        if not cls.EMAIL_CONFIG['user']:
            missing.append('EMAIL_USER')
            
        if not cls.EMAIL_CONFIG['password']:
            missing.append('EMAIL_PASSWORD')
            
        if not cls.ADMIN_EMAIL:
            missing.append('ADMIN_EMAIL')
        
        return missing
    
    @classmethod 
    def get_email_recipients(cls, category: str) -> List[str]:
        """Kategori bazlı email alıcıları"""
        recipients = []
        
        # Admin her zaman alır
        if cls.ADMIN_EMAIL:
            recipients.append(cls.ADMIN_EMAIL)
        
        # Kategori bazlı partnerler
        if category == 'education' and cls.EDUCATION_PARTNER_EMAIL:
            recipients.append(cls.EDUCATION_PARTNER_EMAIL)
        elif category == 'legal' and cls.LEGAL_PARTNER_EMAIL:
            recipients.append(cls.LEGAL_PARTNER_EMAIL)
        # Business sadece admin'e gider
        
        return recipients
    
    @classmethod
    def get_category_config(cls, category: str) -> Dict:
        """Kategori özel konfigürasyonlar"""
        configs = {
            'education': {
                'priority': 'high',
                'auto_respond': True,
                'partners': [cls.EDUCATION_PARTNER_EMAIL] if cls.EDUCATION_PARTNER_EMAIL else [],
                'follow_up_hours': 24,
                'confirmation_email': True
            },
            'legal': {
                'priority': 'urgent',
                'auto_respond': True,
                'partners': [cls.LEGAL_PARTNER_EMAIL] if cls.LEGAL_PARTNER_EMAIL else [],
                'follow_up_hours': 12,
                'confirmation_email': True,
                'urgent_threshold': 4  # hours
            },
            'business': {
                'priority': 'medium',
                'auto_respond': True,
                'partners': [],
                'follow_up_hours': 24,
                'meeting_link': cls.BUSINESS_MEETING_LINK,
                'requires_meeting_booking': True,
                'confirmation_email': True,
                'deal_creation': True
            }
        }
        
        return configs.get(category, {
            'priority': 'normal',
            'auto_respond': False,
            'partners': [],
            'follow_up_hours': 48,
            'confirmation_email': False
        })
    
    @classmethod
    def is_production(cls) -> bool:
        """Production environment kontrolü"""
        return os.environ.get('FLASK_ENV', 'production') == 'production'
    
    @classmethod
    def get_debug_info(cls) -> Dict:
        """Debug bilgileri (password'ları gizli)"""
        return {
            "hubspot_configured": bool(cls.HUBSPOT_API_KEY),
            "email_user": cls.EMAIL_CONFIG['user'] or "Not configured",
            "email_password_length": len(cls.EMAIL_CONFIG['password']) if cls.EMAIL_CONFIG['password'] else 0,
            "smtp_server": cls.EMAIL_CONFIG['smtp_server'],
            "smtp_port": cls.EMAIL_CONFIG['smtp_port'],
            "admin_email": cls.ADMIN_EMAIL or "Not configured",
            "education_partner": cls.EDUCATION_PARTNER_EMAIL or "Not configured",
            "legal_partner": cls.LEGAL_PARTNER_EMAIL or "Not configured",
            "business_meeting_link": bool(cls.BUSINESS_MEETING_LINK),
            "environment": os.environ.get('FLASK_ENV', 'production')
        }