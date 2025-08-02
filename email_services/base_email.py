import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseEmailService(ABC):
    """Tüm email servisleri için temel sınıf"""
    
    def __init__(self, email_config: Dict):
        self.config = email_config
        self.sent_emails = set()  # Duplicate prevention
        
    def test_smtp_connection(self) -> Dict:
        """SMTP bağlantısını test et"""
        
        try:
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.config['user'], self.config['password'])
            server.quit()
            
            return {
                "success": True,
                "message": "SMTP connection successful",
                "server": f"{self.config['smtp_server']}:{self.config['smtp_port']}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            return {
                "success": False,
                "error": "Authentication failed",
                "details": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Connection failed",
                "details": str(e)
            }
    
    def send_email(self, recipients: List[str], subject: str, body: str, submission_id: str = "") -> Dict:
        """Email gönder - Temel metod"""
        
        if not self.config.get('user') or not self.config.get('password'):
            return {"success": False, "error": "Email configuration missing"}
        
        # Duplicate kontrolü
        email_key = f"{submission_id}_{hash(subject)}_{','.join(recipients)}"
        if email_key in self.sent_emails:
            logger.info(f"Duplicate email prevented: {email_key}")
            return {"success": True, "message": "Email already sent (duplicate prevention)"}
        
        try:
            # SMTP bağlantısı
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.config['user'], self.config['password'])
            
            logger.info(f"SMTP connected: {self.config['user']}")
            
            # Her alıcıya gönder
            results = []
            for recipient in recipients:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = f"{self.config.get('from_name', 'British Global')} <{self.config['user']}>"
                    msg['To'] = recipient
                    msg['Subject'] = subject
                    msg.attach(MIMEText(body, 'html', 'utf-8'))
                    
                    server.send_message(msg)
                    results.append({"recipient": recipient, "status": "success"})
                    logger.info(f"Email sent successfully to: {recipient}")
                    
                except Exception as e:
                    results.append({"recipient": recipient, "status": "failed", "error": str(e)})
                    logger.error(f"Failed to send email to {recipient}: {str(e)}")
            
            server.quit()
            
            # Cache'e ekle
            self.sent_emails.add(email_key)
            
            success_count = len([r for r in results if r["status"] == "success"])
            
            return {
                "success": success_count > 0,
                "results": results,
                "success_count": success_count,
                "total_recipients": len(recipients)
            }
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @abstractmethod
    def get_recipients(self, contact_info: Dict) -> List[str]:
        """Alt sınıflar tarafından implement edilmeli"""
        pass
    
    @abstractmethod
    def create_email_content(self, contact_info: Dict, extracted_data: Dict, hubspot_result: Dict) -> tuple:
        """Alt sınıflar tarafından implement edilmeli - (subject, body) döner"""
        pass
    
    def send_notification(self, contact_info: Dict, extracted_data: Dict, hubspot_result: Dict = None) -> Dict:
        """Ana notification gönderme metodu"""
        
        try:
            # Recipients al
            recipients = self.get_recipients(contact_info)
            if not recipients:
                return {"success": False, "error": "No recipients found"}
            
            # Email içeriği oluştur
            subject, body = self.create_email_content(contact_info, extracted_data, hubspot_result or {})
            
            # Email gönder
            submission_id = extracted_data.get('submission_id', '')
            result = self.send_email(recipients, subject, body, submission_id)
            
            logger.info(f"Notification sent - Recipients: {len(recipients)}, Success: {result.get('success')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_base_template(self, contact_info: Dict, category: str, content_sections: List[str]) -> str:
        """Temel HTML template oluştur"""
        
        category_colors = {
            'education': '#10b981',  # Green
            'legal': '#ef4444',      # Red
            'business': '#f59e0b'    # Orange
        }
        
        category_icons = {
            'education': '🎓',
            'legal': '⚖️',
            'business': '💼'
        }
        
        category_tr = {
            'education': 'Eğitim',
            'legal': 'Hukuk',
            'business': 'Ticari'
        }
        
        color = category_colors.get(category, '#667eea')
        icon = category_icons.get(category, '📋')
        category_name = category_tr.get(category, 'Genel')
        
        # Content sections'ı birleştir
        content_html = '\n'.join(content_sections)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6; 
                    color: #2c3e50;
                    background-color: #f8fafc;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 20px auto; 
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: linear-gradient(135deg, {color} 0%, #764ba2 100%);
                    color: white; 
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{ 
                    font-size: 24px; 
                    font-weight: 700;
                    margin-bottom: 8px;
                }}
                .header p {{ 
                    font-size: 16px; 
                    opacity: 0.9;
                }}
                .content {{ 
                    padding: 30px;
                }}
                .info-card {{
                    background: #f8fafc;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    border-left: 4px solid {color};
                }}
                .contact-grid {{ 
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin: 20px 0;
                }}
                .contact-item {{ 
                    background: white;
                    padding: 15px;
                    border-radius: 6px;
                    border: 1px solid #e2e8f0;
                }}
                .label {{ 
                    font-size: 12px;
                    color: #64748b;
                    text-transform: uppercase;
                    font-weight: 600;
                    margin-bottom: 4px;
                }}
                .value {{ 
                    font-size: 16px;
                    color: #1e293b;
                    font-weight: 500;
                }}
                .cta-button {{
                    display: inline-block;
                    background: {color};
                    color: white;
                    padding: 12px 24px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .footer {{ 
                    background: #1e293b;
                    color: #94a3b8;
                    padding: 25px;
                    text-align: center;
                }}
                .urgent {{ 
                    background: #fef2f2;
                    border-left-color: #ef4444;
                    color: #991b1b;
                }}
                @media (max-width: 600px) {{
                    .contact-grid {{ grid-template-columns: 1fr; }}
                    .content {{ padding: 20px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} British Global</h1>
                    <p>Yeni {category_name} Danışmanlık Başvurusu</p>
                </div>
                
                <div class="content">
                    <div class="info-card">
                        <h2 style="margin-bottom: 8px; color: #1e293b;">📋 Başvuru Detayları</h2>
                        <p style="color: #64748b;">📅 {datetime.now().strftime('%d %B %Y, %H:%M')}</p>
                    </div>
                    
                    <h3 style="margin: 24px 0 16px 0; color: #1e293b;">👤 İletişim Bilgileri</h3>
                    <div class="contact-grid">
                        <div class="contact-item">
                            <div class="label">Ad Soyad</div>
                            <div class="value">{contact_info.get('fullname', 'Belirtilmemiş')}</div>
                        </div>
                        <div class="contact-item">
                            <div class="label">Email</div>
                            <div class="value">
                                <a href="mailto:{contact_info.get('email', '')}" style="color: {color}; text-decoration: none;">
                                    {contact_info.get('email', 'Belirtilmemiş')}
                                </a>
                            </div>
                        </div>
                        <div class="contact-item">
                            <div class="label">Telefon</div>
                            <div class="value">
                                <a href="tel:{contact_info.get('phone', '')}" style="color: {color}; text-decoration: none;">
                                    {contact_info.get('phone', 'Belirtilmemiş')}
                                </a>
                            </div>
                        </div>
                        <div class="contact-item">
                            <div class="label">Kategori</div>
                            <div class="value">{category_name} Danışmanlık</div>
                        </div>
                    </div>
                    
                    {content_html}
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; text-align: center;">
                        <p style="color: #ef4444; font-weight: 600; font-size: 16px;">
                            ⏰ Bu müşteriyi 24 saat içinde arayın!
                        </p>
                    </div>
                </div>
                
                <div class="footer">
                    <h3 style="color: white; margin-bottom: 8px;">British Global</h3>
                    <p>İngiltere Eğitim, Yatırım ve Hukuk Danışmanlığı</p>
                    <p style="margin-top: 12px; font-size: 12px; opacity: 0.7;">
                        Bu email otomatik oluşturulmuştur - British Global Webhook System v6.0
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test_service(self) -> Dict:
        """Servis test metodu"""
        return self.test_smtp_connection()