import logging
from typing import Dict, List
from .base_email import BaseEmailService
from datetime import datetime

logger = logging.getLogger(__name__)

class EducationEmailService(BaseEmailService):
    """Eğitim danışmanlığı email servisi"""
    
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
        """Eğitim kategorisi alıcıları"""
        recipients = []
        
        if self.config_class:
            if self.config_class.ADMIN_EMAIL:
                recipients.append(self.config_class.ADMIN_EMAIL)
            if self.config_class.EDUCATION_PARTNER_EMAIL:
                recipients.append(self.config_class.EDUCATION_PARTNER_EMAIL)
        
        # Fallback
        if not recipients:
            recipients = ['info@britishglobal.com.tr']
            
        return recipients
    
    def create_email_content(self, contact_info: Dict, extracted_data: Dict, hubspot_result: Dict) -> tuple:
        """Eğitim özel email içeriği"""
        
        # Education data al
        education_data = extracted_data.get('education', {})
        
        # Subject oluştur
        programs = education_data.get('programs', [])
        main_program = programs[0] if programs else 'Genel Eğitim'
        
        subject = f"🎓 Yeni Eğitim Başvurusu - {main_program} - {contact_info.get('fullname', 'İsimsiz')}"
        
        # Aciliyet kontrolü
        urgency_class = ""
        if education_data.get('priority_level') == 'urgent':
            subject = f"⚡ ACİL - {subject}"
            urgency_class = "urgent"
        
        # Content sections
        content_sections = []
        
        # Eğitim detayları
        education_section = f"""
        <h3 style="margin: 24px 0 16px 0; color: #1e293b;">🎓 Eğitim Detayları</h3>
        <div class="info-card {urgency_class}">
        """
        
        if programs:
            education_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">İlgilenilen Programlar</div>
                <div class="value">{education_data.get('programs_text', '')}</div>
            </div>
            """
        
        if education_data.get('gpa'):
            education_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Not Ortalaması</div>
                <div class="value">{education_data['gpa']}</div>
            </div>
            """
        
        if education_data.get('budget'):
            education_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Bütçe (Eğitim + Konaklama)</div>
                <div class="value" style="color: #10b981; font-weight: 600;">{education_data.get('budget_formatted', '')}</div>
            </div>
            """
        
        education_section += "</div>"
        content_sections.append(education_section)
        
        # Program detay listesi
        if programs:
            program_list = """
            <h3 style="margin: 24px 0 16px 0; color: #1e293b;">📚 Seçilen Programlar</h3>
            <div style="background: white; border-radius: 8px; border: 1px solid #e2e8f0;">
            """
            
            program_icons = {
                'Doktora (PhD)': '🎯',
                'Yüksek Lisans (Master)': '📚', 
                'Lisans (Üniversite)': '🏫',
                'Lise (İngiltere)': '📖',
                'Dil Okulu': '🗣️',
                'Yaz Kampı (12-18 yaş)': '🏕️'
            }
            
            for i, program in enumerate(programs):
                icon = program_icons.get(program, '📋')
                border_style = "" if i == len(programs) - 1 else "border-bottom: 1px solid #f1f5f9;"
                
                program_list += f"""
                <div style="padding: 12px 20px; display: flex; align-items: center; {border_style}">
                    <span style="font-size: 20px; margin-right: 12px;">{icon}</span>
                    <span style="font-weight: 500; color: #1e293b;">{program}</span>
                </div>
                """
            
            program_list += "</div>"
            content_sections.append(program_list)
        
        # Partner özel notlar
        if self.config_class and self.config_class.EDUCATION_PARTNER_EMAIL:
            partner_note = f"""
            <div class="info-card" style="background: #fef3c7; border-left-color: #f59e0b;">
                <h4 style="color: #92400e; margin-bottom: 8px;">📢 Eğitim Partneri Notu</h4>
                <p style="color: #92400e;">
                    Bu başvuru eğitim partnerimize de gönderilmiştir: 
                    <strong>{self.config_class.EDUCATION_PARTNER_EMAIL}</strong>
                </p>
                <p style="color: #92400e; font-size: 14px; margin-top: 8px;">
                    Koordinasyon için lütfen partnerimizle iletişime geçin.
                </p>
            </div>
            """
            content_sections.append(partner_note)
        
        # HubSpot bilgileri
        if hubspot_result and hubspot_result.get('success'):
            hubspot_section = f"""
            <div class="info-card" style="background: #f0f9ff; border-left-color: #0ea5e9;">
                <h4 style="color: #0c4a6e; margin-bottom: 8px;">🔗 HubSpot Entegrasyonu</h4>
                <p style="color: #0c4a6e;">
                    ✅ Contact başarıyla HubSpot'a kaydedildi
                    {f"<br>📋 Contact ID: {hubspot_result.get('contact_id', '')}" if hubspot_result.get('contact_id') else ""}
                </p>
            </div>
            """
            content_sections.append(hubspot_section)
        
        # Email body oluştur
        body = self.create_base_template(contact_info, 'education', content_sections)
        
        return subject, body
    
    def send_application_confirmation(self, contact_info: Dict, extracted_data: Dict) -> Dict:
        """Eğitim başvurusu onay maili"""
        
        education_data = extracted_data.get('education', {})
        programs_text = education_data.get('programs_text', 'seçtiğiniz programlar')
        
        subject = "✅ Eğitim Danışmanlığı Başvurunuz Alındı - British Global"
        
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: #10b981; color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .highlight {{ background: #f0fdf4; padding: 20px; border-radius: 8px; border-left: 4px solid #10b981; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 British Global</h1>
                    <p>İngiltere Eğitim Danışmanlığı</p>
                </div>
                <div class="content">
                    <h2>Sayın {contact_info.get('firstname', '')}!</h2>
                    
                    <p>İngiltere'de eğitim almak için yaptığınız başvurunuz alınmıştır.</p>
                    
                    <div class="highlight">
                        <h3>📋 Başvuru Detaylarınız:</h3>
                        <p><strong>İlgilenilen Programlar:</strong> {programs_text}</p>
                        {f"<p><strong>Not Ortalaması:</strong> {education_data.get('gpa', '')}</p>" if education_data.get('gpa') else ""}
                        {f"<p><strong>Bütçe:</strong> {education_data.get('budget_formatted', '')}</p>" if education_data.get('budget') else ""}
                        <p><strong>Başvuru Tarihi:</strong> {datetime.now().strftime('%d %B %Y')}</p>
                    </div>
                    
                    <h3>📞 Sonraki Adımlar:</h3>
                    <ul>
                        <li>Eğitim danışmanımız 24 saat içinde sizinle iletişime geçecektir</li>
                        <li>Size en uygun üniversite ve programları önereceğiz</li>
                        <li>Başvuru sürecinizi baştan sona takip edeceğiz</li>
                        <li>Vize işlemlerinizde size yardımcı olacağız</li>
                    </ul>
                    
                    <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h4 style="color: #92400e;">📋 Hazırlamanız Gerekenler:</h4>
                        <ul style="color: #92400e; margin-top: 10px;">
                            <li>Transkript (not dökümleri)</li>
                            <li>Diploma/mezuniyet belgesi</li>
                            <li>İngilizce sınav sonuçları (IELTS/TOEFL)</li>
                            <li>Pasaport fotokopisi</li>
                        </ul>
                        <p style="color: #92400e; margin-top: 12px; font-size: 14px;">
                            Detaylı belge listesi danışmanımız tarafından size iletilecektir.
                        </p>
                    </div>
                    
                    <p style="margin-top: 30px;">
                        Acil durumlar için bize <strong>info@britishglobal.com.tr</strong> 
                        adresinden ulaşabilirsiniz.
                    </p>
                    
                    <p>Saygılarımızla,<br><strong>British Global Eğitim Danışmanlığı Ekibi</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email([contact_info['email']], subject, body)