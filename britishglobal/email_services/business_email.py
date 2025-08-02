import logging
from typing import Dict, List
from .base_email import BaseEmailService
from datetime import datetime

logger = logging.getLogger(__name__)

class BusinessEmailService(BaseEmailService):
    """Ticari danışmanlık email servisi"""
    
    def __init__(self, email_config: Dict):
        super().__init__(email_config)
        
        # Config import'u güvenli hale getir
        try:
            from config.settings import Config
            self.config_class = Config
        except ImportError:
            logger.warning("Config import failed, using fallback")
            self.config_class = None
    
    def get_recipients(self, contact_info: Dict) -> List[str]:
        """Business kategorisi alıcıları - Sadece admin"""
        recipients = []
        
        if self.config_class and self.config_class.ADMIN_EMAIL:
            recipients.append(self.config_class.ADMIN_EMAIL)
        
        # Fallback
        if not recipients:
            recipients = ['info@britishglobal.com.tr']
            
        return recipients
    
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
                border_style = "" if i == len(sectors) - 1 else "border-bottom: 1px solid #f1f5f9;"
                
                sector_list += f"""
                <div style="padding: 12px 20px; display: flex; align-items: center; {border_style}">
                    <span style="font-size: 20px; margin-right: 12px;">{icon}</span>
                    <span style="font-weight: 500; color: #1e293b;">{sector}</span>
                </div>
                """
            
            sector_list += "</div>"
            content_sections.append(sector_list)
        
        # Meeting requirement
        meeting_section = """
        <div class="info-card" style="background: #fef3c7; border-left-color: #f59e0b;">
            <h4 style="color: #92400e; margin-bottom: 8px;">📅 Meeting Gereksinimi</h4>
            <p style="color: #92400e; font-weight: 600;">
                Ticari danışmanlık için detaylı görüşme gereklidir.
            </p>
            <p style="color: #92400e; font-size: 14px; margin-top: 8px;">
                Lütfen müşteriyle 24 saat içinde meeting ayarlayın.
            </p>
        """
        
        # Meeting link ekle
        if self.config_class and hasattr(self.config_class, 'BUSINESS_MEETING_LINK'):
            meeting_section += f"""
            <p style="color: #92400e; margin-top: 12px;">
                <strong>Meeting Link:</strong> 
                <a href="{self.config_class.BUSINESS_MEETING_LINK}" style="color: #f59e0b;">
                    {self.config_class.BUSINESS_MEETING_LINK}
                </a>
            </p>
            """
        
        meeting_section += "</div>"
        content_sections.append(meeting_section)
        
        # UK Market Entry stratejisi
        strategy_section = """
        <h3 style="margin: 24px 0 16px 0; color: #1e293b;">🎯 UK Market Entry Stratejisi</h3>
        <div style="background: white; border-radius: 8px; border: 1px solid #e2e8f0; padding: 20px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div style="text-align: center; padding: 15px; background: #f0f9ff; border-radius: 6px;">
                    <div style="font-size: 24px; margin-bottom: 8px;">🏢</div>
                    <div style="font-weight: 600; color: #0c4a6e;">Company Setup</div>
                    <div style="font-size: 12px; color: #64748b;">UK'da şirket kurulumu</div>
                </div>
                <div style="text-align: center; padding: 15px; background: #f0fdf4; border-radius: 6px;">
                    <div style="font-size: 24px; margin-bottom: 8px;">📊</div>
                    <div style="font-weight: 600; color: #166534;">Market Research</div>
                    <div style="font-size: 12px; color: #64748b;">Pazar analizi</div>
                </div>
                <div style="text-align: center; padding: 15px; background: #fefce8; border-radius: 6px;">
                    <div style="font-size: 24px; margin-bottom: 8px;">🤝</div>
                    <div style="font-weight: 600; color: #a16207;">Partnership</div>
                    <div style="font-size: 12px; color: #64748b;">İş ortaklıkları</div>
                </div>
                <div style="text-align: center; padding: 15px; background: #fdf2f8; border-radius: 6px;">
                    <div style="font-size: 24px; margin-bottom: 8px;">📈</div>
                    <div style="font-weight: 600; color: #be185d;">Growth Plan</div>
                    <div style="font-size: 12px; color: #64748b;">Büyüme stratejisi</div>
                </div>
            </div>
        </div>
        """
        content_sections.append(strategy_section)
        
        # HubSpot Deal bilgisi
        if hubspot_result and hubspot_result.get('success'):
            hubspot_section = f"""
            <div class="info-card" style="background: #f0f9ff; border-left-color: #0ea5e9;">
                <h4 style="color: #0c4a6e; margin-bottom: 8px;">🔗 HubSpot Entegrasyonu</h4>
                <p style="color: #0c4a6e;">
                    ✅ Contact ve Deal başarıyla HubSpot'a kaydedildi
                    {f"<br>📋 Contact ID: {hubspot_result.get('contact_id', '')}" if hubspot_result.get('contact_id') else ""}
                    {f"<br>💼 Deal: UK Market Entry" if hubspot_result.get('deal_result', {}).get('success') else ""}
                </p>
            </div>
            """
            content_sections.append(hubspot_section)
        
        # Email body oluştur
        body = self.create_base_template(contact_info, 'business', content_sections)
        
        return subject, body
    
    def send_application_confirmation(self, contact_info: Dict, extracted_data: Dict) -> Dict:
        """Business başvurusu onay maili"""
        
        business_data = extracted_data.get('business', {})
        company_name = business_data.get('company_name', 'şirketiniz')
        sectors_text = business_data.get('sectors_text', 'belirttiğiniz sektörler')
        
        subject = "✅ Ticari Danışmanlık Başvurunuz Alındı - British Global"
        
        # Meeting link'i al
        meeting_link = "TBD"
        if self.config_class and hasattr(self.config_class, 'BUSINESS_MEETING_LINK'):
            meeting_link = self.config_class.BUSINESS_MEETING_LINK
        
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: #f59e0b; color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .highlight {{ background: #fef3c7; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b; }}
                .cta-button {{ 
                    display: inline-block; background: #f59e0b; color: white; 
                    padding: 15px 30px; border-radius: 8px; text-decoration: none; 
                    font-weight: 600; margin: 15px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💼 British Global</h1>
                    <p>İngiltere Ticari Danışmanlığı</p>
                </div>
                <div class="content">
                    <h2>Sayın {contact_info.get('firstname', '')}!</h2>
                    
                    <p>İngiltere pazarına giriş için yaptığınız başvurunuz alınmıştır.</p>
                    
                    <div class="highlight">
                        <h3>📋 Başvuru Detaylarınız:</h3>
                        <p><strong>Şirket:</strong> {company_name}</p>
                        <p><strong>Faaliyet Alanları:</strong> {sectors_text}</p>
                        <p><strong>Başvuru Tarihi:</strong> {datetime.now().strftime('%d %B %Y')}</p>
                    </div>
                    
                    <h3>📞 Sonraki Adımlar:</h3>
                    <ul>
                        <li>Ticari danışmanımız 24 saat içinde sizinle iletişime geçecektir</li>
                        <li>Detaylı görüşme için meeting ayarlayacağız</li>
                        <li>UK market entry stratejinizi oluşturacağız</li>
                        <li>Şirket kurulum sürecinizi yöneteceğiz</li>
                    </ul>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <h4>📅 Hemen Meeting Ayarlayın</h4>
                        <a href="{meeting_link}" class="cta-button">
                            🗓️ Meeting Takvimi
                        </a>
                        <p style="font-size: 14px; color: #64748b; margin-top: 10px;">
                            Yukarıdaki linkten size uygun bir zaman seçebilirsiniz
                        </p>
                    </div>
                    
                    <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h4 style="color: #0c4a6e;">🎯 UK Market Entry Hizmetlerimiz:</h4>
                        <ul style="color: #0c4a6e; margin-top: 10px;">
                            <li>UK'da şirket kurulumu ve kayıtlar</li>
                            <li>Pazar araştırması ve rakip analizi</li>
                            <li>Distribütör ve partner bulma</li>
                            <li>Yasal düzenlemeler ve compliance</li>
                            <li>Finans ve muhasebe çözümleri</li>
                        </ul>
                    </div>
                    
                    <p style="margin-top: 30px;">
                        Acil durumlar için bize <strong>info@britishglobal.com.tr</strong> 
                        adresinden ulaşabilirsiniz.
                    </p>
                    
                    <p>Saygılarımızla,<br><strong>British Global Ticari Danışmanlık Ekibi</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email([contact_info['email']], subject, body)
    
    def send_meeting_reminder(self, contact_info: Dict, meeting_date: str) -> Dict:
        """Meeting hatırlatma maili"""
        
        subject = f"📅 Meeting Hatırlatması - {meeting_date} - British Global"
        
        body = f"""
        <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 25px; text-align: center;">
            <h2 style="color: #92400e;">📅 Meeting Hatırlatması</h2>
            <p style="color: #92400e; font-size: 18px; font-weight: 600;">
                Sayın {contact_info.get('fullname', '')},
            </p>
            <p style="color: #92400e;">
                UK Market Entry görüşmeniz <strong>{meeting_date}</strong> tarihinde planlanmıştır.
            </p>
            <p style="color: #92400e; margin-top: 15px;">
                📞 Telefon: {contact_info.get('phone', '')}<br>
                📧 Email: {contact_info.get('email', '')}
            </p>
        </div>
        """
        
        return self.send_email([contact_info['email']], subject, body)