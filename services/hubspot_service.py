from typing import Dict, Any, List
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HubSpotService:
    """HubSpot CRM entegrasyonu"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com/crm/v3/objects"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def test_connection(self) -> Dict:
        """HubSpot API bağlantısını test et"""
        
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}
        
        try:
            # Account info endpoint'i test et
            url = "https://api.hubapi.com/oauth/v1/access-tokens/" + self.api_key
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "HubSpot connection successful",
                    "api_status": "Valid"
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid API key or connection failed",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_contact(self, contact_info: Dict, category: str, extracted_data: Dict) -> Dict:
        """Contact'ı HubSpot'a kaydet"""
        
        if not self.api_key:
            return {"success": False, "error": "HubSpot API key not configured"}
        
        try:
            # Properties oluştur
            properties = self._build_contact_properties(contact_info, category, extracted_data)
            
            # Contact oluştur/güncelle
            contact_result = self._create_or_update_contact(properties)
            
            if contact_result.get('success'):
                contact_id = contact_result.get('contact_id')
                
                # Note ekle
                note_result = self._create_contact_note(contact_id, category, extracted_data)
                
                return {
                    "success": True,
                    "contact_id": contact_id,
                    "contact_result": contact_result,
                    "note_result": note_result
                }
            else:
                return contact_result
                
        except Exception as e:
            logger.error(f"HubSpot save error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _build_contact_properties(self, contact_info: Dict, category: str, extracted_data: Dict) -> Dict:
        """Contact properties oluştur - HubSpot uyumlu"""
        
        # Temel properties (sadece mevcut olanlar)
        properties = {
            "email": contact_info['email'],
            "firstname": contact_info['firstname'] or "",
            "lastname": contact_info['lastname'] or "",
            "phone": contact_info['phone'],
            "lifecyclestage": "lead",
            "hs_lead_status": "NEW"  # Standart HubSpot değeri
        }
        
        # Notes field - tüm kategoriler için
        notes = extracted_data.get('notes', '')
        if notes:
            properties["notes_last_contacted"] = notes[:500]  # HubSpot field limit
        
        # Kategori özel properties
        if category == 'education':
            education_data = extracted_data.get('education', {})
            
            # GPA - mevcut property
            if education_data.get('gpa'):
                try:
                    properties["gpa"] = float(education_data['gpa'])
                except (ValueError, TypeError):
                    properties["gpa"] = str(education_data['gpa'])
            
            # Budget - mevcut property kullan
            if education_data.get('budget'):
                try:
                    budget_value = str(education_data['budget']).replace('£', '').replace(',', '').strip()
                    properties["budget"] = float(budget_value)
                except (ValueError, TypeError):
                    properties["budget"] = str(education_data['budget'])
            
            # Education Level - mevcut property
            if education_data.get('programs'):
                properties["education_level"] = ', '.join(education_data['programs'])
            
        elif category == 'legal':
            legal_data = extracted_data.get('legal', {})
            
            # Legal Service Type - mevcut property
            if legal_data.get('selected_services'):
                properties["legal_service_type"] = ', '.join(legal_data['selected_services'])
            
            # Aciliyet için standart priority kullan
            if legal_data.get('urgency_level'):
                if legal_data['urgency_level'] == 'urgent':
                    properties["hs_lead_status"] = "ATTEMPTED_TO_CONTACT"  # Acil için
                else:
                    properties["hs_lead_status"] = "NEW"
        
        elif category == 'business':
            business_data = extracted_data.get('business', {})
            
            # Şirket adı
            if business_data.get('company_name'):
                properties["company"] = business_data['company_name']
            
            # Sektör bilgisi için industry kullan
            if business_data.get('sectors_text'):
                properties["industry"] = business_data['sectors_text']
            
            # Annual Revenue - eğer mevcut property varsa
            if business_data.get('annual_revenue'):
                try:
                    properties["annual_revenue"] = float(business_data['annual_revenue'])
                except (ValueError, TypeError):
                    pass  # Skip if not valid
        
        # Boş değerleri temizle
        properties = {k: v for k, v in properties.items() if v and str(v).strip()}
        
        logger.info(f"Built {len(properties)} properties for {category} contact")
        logger.debug(f"Properties: {list(properties.keys())}")
        
        return properties
    
    def _create_or_update_contact(self, properties: Dict) -> Dict:
        """Contact oluştur veya güncelle"""
        
        try:
            url = f"{self.base_url}/contacts"
            payload = {"properties": properties}
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                contact_id = result.get('id')
                logger.info(f"Contact created/updated successfully - ID: {contact_id}")
                
                return {
                    "success": True,
                    "contact_id": contact_id,
                    "action": "created",
                    "properties_count": len(properties)
                }
                
            elif response.status_code == 409:
                # Contact zaten var - email ile ara ve güncelle
                logger.info("Contact exists, attempting update...")
                return self._update_existing_contact(properties)
                
            else:
                logger.error(f"HubSpot contact error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            logger.error(f"Contact creation error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _update_existing_contact(self, properties: Dict) -> Dict:
        """Mevcut contact'ı güncelle"""
        
        try:
            # Email ile contact ara
            email = properties.get('email')
            search_url = f"{self.base_url}/contacts/search"
            
            search_payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }]
            }
            
            search_response = requests.post(search_url, headers=self.headers, json=search_payload, timeout=30)
            
            if search_response.status_code == 200:
                search_result = search_response.json()
                contacts = search_result.get('results', [])
                
                if contacts:
                    contact_id = contacts[0]['id']
                    
                    # Contact'ı güncelle
                    update_url = f"{self.base_url}/contacts/{contact_id}"
                    update_payload = {"properties": properties}
                    
                    update_response = requests.patch(update_url, headers=self.headers, json=update_payload, timeout=30)
                    
                    if update_response.status_code == 200:
                        logger.info(f"Contact updated successfully - ID: {contact_id}")
                        return {
                            "success": True,
                            "contact_id": contact_id,
                            "action": "updated"
                        }
                    else:
                        return {"success": False, "error": "Failed to update contact"}
                else:
                    return {"success": False, "error": "Contact not found for update"}
            else:
                return {"success": False, "error": "Search failed"}
                
        except Exception as e:
            logger.error(f"Contact update error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_contact_note(self, contact_id: str, category: str, extracted_data: Dict) -> Dict:
        """Contact'a detaylı note ekle"""
        
        try:
            # Note içeriği oluştur
            note_body = self._build_note_content(category, extracted_data)
            
            url = f"{self.base_url}/notes"
            payload = {
                "properties": {
                    "hs_note_body": note_body,
                    "hs_timestamp": datetime.now().isoformat()
                },
                "associations": [{
                    "to": {"id": str(contact_id)},
                    "types": [{
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 202  # note_to_contact
                    }]
                }]
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                note_result = response.json()
                note_id = note_result.get('id')
                logger.info(f"Note created successfully - ID: {note_id}")
                
                return {"success": True, "note_id": note_id}
            else:
                logger.error(f"Note creation error: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Note creation error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _build_note_content(self, category: str, extracted_data: Dict) -> str:
        """Note içeriği oluştur"""
        
        note_body = f"🎯 BRITISH GLOBAL - {category.upper()}\n"
        note_body += f"📅 Başvuru: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        note_body += f"📋 Submission ID: {extracted_data.get('submission_id', 'N/A')}\n\n"
        
        # Genel notlar - tüm kategoriler için
        general_notes = extracted_data.get('notes', '')
        if general_notes:
            note_body += f"📝 Ek Notlar: {general_notes}\n\n"
        
        if category == 'education':
            education_data = extracted_data.get('education', {})
            note_body += "🎓 EĞİTİM DANIŞMANLIĞI\n"
            note_body += "=" * 30 + "\n"
            
            if education_data.get('programs'):
                note_body += f"📚 İlgilenilen Programlar:\n"
                for program in education_data['programs']:
                    note_body += f"  • {program}\n"
                note_body += "\n"
            
            if education_data.get('gpa'):
                note_body += f"📊 Not Ortalaması: {education_data['gpa']}\n"
            
            if education_data.get('budget'):
                note_body += f"💰 Bütçe: £{education_data['budget']}\n"
            
            # Kategori özel notlar
            edu_notes = education_data.get('notes', '')
            if edu_notes:
                note_body += f"📋 Eğitim Notları: {edu_notes}\n"
        
        elif category == 'legal':
            legal_data = extracted_data.get('legal', {})
            note_body += "⚖️ HUKUK DANIŞMANLIĞI\n"
            note_body += "=" * 30 + "\n"
            
            if legal_data.get('selected_services'):
                note_body += f"📋 Talep Edilen Hizmetler:\n"
                for service in legal_data['selected_services']:
                    note_body += f"  • {service}\n"
                note_body += "\n"
            
            if legal_data.get('topic'):
                note_body += f"📝 Ek Açıklama: {legal_data['topic']}\n"
            
            # Kategori özel notlar
            legal_notes = legal_data.get('notes', '')
            if legal_notes:
                note_body += f"⚖️ Hukuk Notları: {legal_notes}\n"
        
        elif category == 'business':
            business_data = extracted_data.get('business', {})
            note_body += "💼 TİCARİ DANIŞMANLIK\n"
            note_body += "=" * 30 + "\n"
            
            if business_data.get('company_name'):
                note_body += f"🏢 Şirket: {business_data['company_name']}\n"
            
            if business_data.get('selected_sectors'):
                note_body += f"📈 Faaliyet Alanları:\n"
                for sector in business_data['selected_sectors']:
                    note_body += f"  • {sector}\n"
                note_body += "\n"
            
            # Kategori özel notlar
            business_notes = business_data.get('notes', '')
            if business_notes:
                note_body += f"💼 Ticari Notlar: {business_notes}\n"
        
        # Contact info ekle
        note_body += f"\n📧 Email: {extracted_data.get('email', '')}\n"
        note_body += f"📞 Telefon: {extracted_data.get('phone', '')}\n"
        note_body += f"\n🤖 Otomatik webhook kaydı - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        return note_body