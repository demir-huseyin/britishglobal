import logging
from typing import Dict, List
from .base_email import BaseEmailService
from config.settings import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class LegalEmailService(BaseEmailService):
    """Hukuk danışmanlığı email servisi"""
    
    def get_recipients(self, contact_info: Dict) -> List[str]:
        """Hukuk kategorisi alıcıları"""
        recipients = [Config.ADMIN_EMAIL]
        
        if Config.LEGAL_PARTNER_EMAIL:
            recipients.append(Config.LEGAL_PARTNER_EMAIL)
            
        return recipients
    
    def create_email_content(self, contact_info: Dict, extracted_data: Dict, hubspot_result: Dict) -> tuple:
        """Hukuk özel email içeriği"""
        
        # Legal data al
        legal_data = extracted_data.get('legal', {})
        
        # Subject oluştur - Aciliyet kontrolü
        services = legal_data.get('selected_services', [])
        main_service = services[0] if services else 'Genel Hukuki'
        
        subject = f"⚖️ Yeni Hukuk Başvurusu - {main_service} - {contact_info.get('fullname', 'İsimsiz')}"
        
        # Acil durumlar için özel subject
        urgent_services = ['vize_red', 'turistik_vize']
        if any(service in urgent_services for service in services):
            subject = f"🚨 ACİL HUKUK - {subject}"
        
        # Content sections
        content_sections = []
        
        # Hukuk hizmetleri detayları
        legal_section = f"""
        <h3 style="margin: 24px 0 16px 0; color: #1e293b;">⚖️ Hukuki Hizmet Detayları</h3>
        <div class="info-card {'urgent' if legal_data.get('urgency_level') == 'urgent' else ''}">
        """
        
        if legal_data.get('services_text'):
            legal_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Talep Edilen Hizmetler</div>
                <div class="value" style="font-weight: 600;">{legal_data['services_text']}</div>
            </div>
            """
        
        if legal_data.get('topic'):
            legal_section += f"""
            <div style="margin-bottom: 16px;">
                <div class="label">Ek Açıklama</div>
                <div class="value">{legal_data['topic']}</div>
            </div>
            """
        
        # Aciliyet seviyesi
        urgency_level = legal_data.get('urgency_level', 'medium')
        urgency_colors = {
            'urgent': '#ef4444',
            'high': '#f59e0b', 
            'medium': '#10b981'
        }
        urgency_texts = {
            'urgent': '🚨 ACİL - Hemen İletişim Gerekli',
            'high': '⚡ Yüksek Öncelik',
            'medium': '📋 Normal Öncelik'
        }
        
        legal_section += f"""
        <div style="margin-top: 16px; padding: 12px; background: {urgency_colors.get(urgency_level, '#10b981')}; 
             border-radius: 6px; color: white; text-align: center; font-weight: 600;">
            {urgency_texts.get(urgency_level, 'Normal Öncelik')}
        </div>
        </div>
        """
        content_sections.append(legal_section)
        
        # Hizmet detay listesi
        if services:
            service_list = """
            <h3 style="margin: 24px 0 16px 0; color: #1e293b;">📋 Seçilen Hukuki Hizmetler</h3>
            <div style="background: white; border-radius: 8px; border: 1px solid #e2e8f0;">
            """
            
            service_details = {
                'turistik_vize': {
                    'icon': '✈️',
                    'name': 'Turistik Vize (Visitor Visa)',
                    'urgency': 'high',
                    'typical_duration': '2-4 hafta'
                },
                'ogrenci_vize': {
                    'icon': '🎓', 
                    'name': 'Öğrenci Vizesi (Student Visa)',
                    'urgency': 'high',
                    'typical_duration': '3-8 hafta'
                },
                'calisma_vize': {
                    'icon': '💼',
                    'name': 'Çalışma Vizesi (Work Visa)', 
                    'urgency': 'high',
                    'typical_duration': '8-12 hafta'
                },
                'aile_vize': {
                    'icon': '👨‍👩‍👧‍👦',
                    'name': 'Aile Birleşimi (Family Visa)',
                    'urgency': 'medium',
                    'typical_duration': '12-24 hafta'
                },
                'ilr': {
                    'icon': '🏠',
                    'name': 'Süresiz Oturum (ILR)',
                    'urgency': 'medium', 
                    'typical_duration': '6-12 hafta'
                },
                'vatandaslik': {
                    'icon': '🇬🇧',
                    'name': 'Vatandaşlık Başvurusu',
                    'urgency': 'medium',
                    'typical_duration': '6-12 ay'
                },
                'vize_red': {
                    'icon': '⚖️',
                    'name': 'Vize Red İtiraz',
                    'urgency': 'urgent',
                    'typical_duration': '2-6 hafta'
                }
            }
            
            for i, service in enumerate(services):
                if service in service_details:
                    details = service_details[service]
                    border_style = "" if i == len(services) - 1 else "border-bottom: 1px solid #f1f5f9;"
                    urgency_color = urgency_colors.get(details['urgency'], '#10b981')
                    
                    service_list += f"""
                    <div style="padding: 15px 20px; {border_style}">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center;">
                                <span style="font-size: 24px; margin-right: 12px;">{details['icon']}</span>
                                <div>
                                    <div style="font-weight: 600; color: #1e293b;">{details['name']}</div>
                                    <div style="font-size: 14px; color: #64748b;">Süre: {details['typical_duration']}</div>
                                </div>
                            </div>
                            <div style="background: {urgency_color}; color: white; padding: 4px 8px; 
                                 border-radius: 4px; font-size: 12px; font-weight: 600;">
                                {urgency_texts.get(details['urgency'], 'Normal')}
                            </div>
                        </div>
                    </div>
                    """
            
            service_list += "</div>"
            content_sections.append(service_list)
        
        # Partner özel notlar
        if Config.LEGAL_PARTNER_EMAIL:
            partner_note = f"""
            <div class="info-card" style="background: #fef2f2; border-left-color: #ef4444;">
                <h4 style="color: #dc2626; margin-bottom: 8px;">🤝 Hukuk Partneri Koordinasyonu</h4>
                <p style="color: #dc2626;">
                    Bu başvuru hukuk partnerimize de gönderilmiştir: 
                    <strong>{Config.LEGAL_PARTNER_EMAIL}</strong>
                </p>
                <p style="color: #dc2626; font-size: 14px; margin-top: 8px;">
                    Vize başvuru süreçleri için partnerimizle koordineli çalışın.
                </p>
            </div>
            """
            content_sections.append(partner_note)
        
        # Acil durum uyarısı
        if legal_data.get('urgency_level') == 'urgent':
            urgent_warning = """
            <div class="info-card urgent" style="text-align: center;">
                <h3 style="color: #dc2626; margin-bottom: 12px;">🚨 ACİL DURUM</h3>
                <p style="color: #dc2626; font-weight: 600; font-size: 18px;">
                    Bu başvuru ACELE cevap gerektirmektedir!
                </p>
                <p style="color: #dc2626; margin-top: 8px;">
                    Lütfen 4 saat içinde müşteriyle iletişime geçin.
                </p>
            </div>
            """
            content_sections.insert(0, urgent_warning)  # En üste ekle
        
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
        body = self.create_base_template(contact_info, 'legal', content_sections)
        
        return subject, body
    
    def send_application_confirmation(self, contact_info: Dict, extracted_data: Dict) -> Dict:
        """Hukuk başvurusu onay maili"""
        
        legal_data = extracted_data.get('legal', {})
        services = legal_data.get('services_text', 'seçtiğiniz hizmetler')
        
        subject = "✅ Hukuki Danışmanlık Başvurunuz Alındı - British Global"
        
        # Acil durum kontrolü
        urgency_message = ""
        if legal_data.get('urgency_level') == 'urgent':
            urgency_message = """
            <div style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px; 
                 padding: 20px; margin: 20px 0; text-align: center;">
                <h3 style="color: #dc2626;">🚨 Acil Başvuru</h3>
                <p style="color: #dc2626; font-weight: 600;">
                    Başvurunuz acil olarak değerlendirilecek ve en kısa sürede size dönüş yapılacaktır.
                </p>
            </div>
            """
        
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: #ef4444; color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .highlight {{ background: #fef2f2; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚖️ British Global</h1>
                    <p>İngiltere Hukuk ve Vize Danışmanlığı</p>
                </div>
                <div class="content">
                    <h2>Sayın {contact_info.get('firstname', '')}!</h2>
                    
                    {urgency_message}
                    
                    <p>İngiltere hukuki işlemleriniz için yaptığınız başvurunuz alınmıştır.</p>
                    
                    <div class="highlight">
                        <h3>📋 Başvuru Detaylarınız:</h3>
                        <p><strong>Talep Edilen Hizmetler:</strong> {services}</p>
                        {f"<p><strong>Ek Açıklama:</strong> {legal_data.get('topic', '')}</p>" if legal_data.get('topic') else ""}
                        <p><strong>Başvuru Tarihi:</strong> {datetime.now().strftime('%d %B %Y')}</p>
                    </div>
                    
                    <h3>📞 Sonraki Adımlar:</h3>
                    <ul>
                        <li>Hukuk danışmanımız {'4 saat' if legal_data.get('urgency_level') == 'urgent' else '24 saat'} içinde sizinle iletişime geçecektir</li>
                        <li>Dosyanızı detaylı inceleyeceğiz</li>
                        <li>Size en uygun çözümü sunacağız</li>
                        <li>Başvuru sürecinizi takip edeceğiz</li>
                    </ul>
                    
                    <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h4 style="color: #0c4a6e;">📋 Hazırlamanız Gerekenler:</h4>
                        <ul style="color: #0c4a6e; margin-top: 10px;">
                            <li>Pasaport fotokopisi</li>
                            <li>Mevcut visa/residence permit (varsa)</li>
                            <li>İlgili belgeler (duruma göre)</li>
                        </ul>
                        <p style="color: #0c4a6e; margin-top: 12px; font-size: 14px;">
                            Detaylı belge listesi danışmanımız tarafından size iletilecektir.
                        </p>
                    </div>
                    
                    <p style="margin-top: 30px;">
                        Acil durumlar için bize <strong>info@britishglobal.com.tr</strong> 
                        adresinden ulaşabilirsiniz.
                    </p>
                    
                    <p>Saygılarımızla,<br><strong>British Global Hukuk Danışmanlığı Ekibi</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email([contact_info['email']], subject, body)
    
    def send_urgent_alert(self, contact_info: Dict, legal_data: Dict) -> Dict:
        """Acil hukuk durumları için özel uyarı"""
        
        subject = f"🚨 ACİL HUKUK UYARISI - {contact_info.get('fullname')} - HEMEN ARAY!"
        
        body = f"""
        <div style="background: #fef2f2; border: 3px solid #ef4444; border-radius: 12px; padding: 30px; text-align: center;">
            <h1 style="color: #dc2626; font-size: 32px; margin-bottom: 20px;">🚨 ACİL DURUM</h1>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h2 style="color: #dc2626;">Müşteri Bilgileri</h2>
                <p><strong>Ad:</strong> {contact_info.get('fullname')}</p>
                <p><strong>Telefon:</strong> <a href="tel:{contact_info.get('phone')}" style="color: #dc2626; font-weight: 600; font-size: 18px;">{contact_info.get('phone')}</a></p>
                <p><strong>Email:</strong> {contact_info.get('email')}</p>
                <p><strong>Hizmet:</strong> {legal_data.get('services_text', '')}</p>
            </div>
            
            <div style="background: #dc2626; color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>⏰ HEMEN EYLEM GEREKLİ</h3>
                <p style="font-size: 18px; font-weight: 600;">
                    Bu müşteriyi ŞİMDİ ARAYIN!
                </p>
                <p>Maksimum 4 saat içinde iletişim kurulmalıdır.</p>
            </div>
        </div>
        """
        
        # Sadece admin'e acil uyarı gönder
        return self.send_email([Config.ADMIN_EMAIL], subject, body)
    
    def send_deadline_reminder(self, contact_info: Dict, service_type: str, days_remaining: int) -> Dict:
        """Vize başvuru deadline hatırlatması"""
        
        subject = f"⏰ DEADLINE UYARISI - {service_type} - {days_remaining} gün kaldı"
        
        body = f"""
        <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 25px;">
            <h2 style="color: #92400e;">⏰ Deadline Yaklaşıyor</h2>
            <p style="color: #92400e; font-size: 18px; font-weight: 600;">
                {contact_info.get('fullname')} - {service_type}
            </p>
            <p style="color: #92400e;">
                Başvuru deadline'ına <strong>{days_remaining} gün</strong> kaldı.
            </p>
            <p style="color: #92400e; margin-top: 15px;">
                📞 Telefon: {contact_info.get('phone')}<br>
                📧 Email: {contact_info.get('email')}
            </p>
        </div>
        """
        
        recipients = [Config.ADMIN_EMAIL]
        if Config.LEGAL_PARTNER_EMAIL:
            recipients.append(Config.LEGAL_PARTNER_EMAIL)
            
        return self.send_email(recipients, subject, body)