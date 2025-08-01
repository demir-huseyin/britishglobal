import logging
from typing import Dict, List
from .base_email import BaseEmailService
from config.settings import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class BusinessEmailService(BaseEmailService):
    """Ticari danışmanlık email servisi"""
    
    def get_recipients(self, contact_info: Dict) -> List[str]:
        """Business kategorisi alıcıları - Sadece admin"""
        return [Config.ADMIN_EMAIL]  # Business sadece admin'e gider
    
    def create_email_content(self, contact_info: Dict, extracted_data: Dict, hubspot_result: Dict) -> tuple:
        """Business özel email içeriği"""
        
        # Business data al
        business_data = extracted_data.get('business', {})
        
        # Subject oluştur
        company_name = business_data.get('company_name', 'Şirket İsmi Belirtilmemiş')
        subject = f"💼 Yeni Ticari Danışmanlık - {company_name} - {contact_info.get('fullname', 'İsimsiz')}"
        
        # Content sections
        content_sections = []
        
        # Şirket bilgileri
        company_section = f"""
        <h3 style="margin: 24px 0 16px 0; color: #1e293b;">🏢 Şirket Bilgileri</h3>
        <div class="info-card">
        """
        
        if business_data.get('company_name'):
            company_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Şirket Adı</div>
                <div class="value" style="font-weight: 600; color: #f59e0b;">{business_data['company_name']}</div>
            </div>
            """
        
        if business_data.get('sector'):
            company_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Genel Sektör</div>
                <div class="value">{business_data['sector']}</div>
            </div>
            """
        
        if business_data.get('sectors_text'):
            company_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Detay Sektörler</div>
                <div class="value">{business_data['sectors_text']}</div>
            </div>
            """
        
        # Business type analizi
        business_type = business_data.get('business_type', 'general')
        type_descriptions = {
            'multi_sector': '🔄 Çok Sektörlü İşletme',
            'consumer_goods': '🛍️ Tüketici Ürünleri',
            'industrial': '🏭 Endüstriyel Ürünler',
            'general': '📈 Genel Ticaret'
        }
        
        company_section += f"""
        <div style="margin-top: 16px; padding: 12px; background: #f59e0b; border-radius: 6px; 
             color: white; text-align: center; font-weight: 600;">
            {type_descriptions.get(business_type, 'Genel Ticaret')}
        </div>
        </div>
        """
        content_sections.append(company_section)
        
        # Sektör detay listesi
        if business_data.get('sectors'):
            sector_list = """
            <h3 style="margin: 24px 0 16px 0; color: #1e293b;">🏭 Faaliyet Alanları</h3>
            <div style="background: white; border-radius: 8px; border: 1px solid #e2e8f0;">
            """
            
            sector_icons = {
                'Ambalaj ve Baskı': '📦',
                'Tekstil ve Giyim': '👕',
                'Ayakkabı ve Deri': '👞',
                'Mobilya ve Dekorasyon': '🪑',
                'Gıda ve İçecek': '🍽️',
                'Takı ve Aksesuar': '💍',
                'Hediyelik Eşya': '🎁',
                'Kozmetik ve Bakım': '💄',
                'Oyuncak ve Kırtasiye': '🧸',
                'Temizlik Ürünleri': '🧽',
                'Ev Gereçleri': '🏠',
                'Hırdavat': '🔧',
                'Otomotiv': '🚗',
                'Bahçe Ürünleri': '🌱',
                'Diğer Sektör': '📋'
            }
            
            sectors = business_data.get('sectors', [])
            for i, sector in enumerate(sectors):
                icon = sector_icons.get(sector, '📋')
                border_