import requests
import logging
from typing import Dict, Any
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
                
                # Deal oluştur (business için)
                deal_result = {}
                if category == 'business':
                    deal_result = self._create_business_deal(contact_id, extracted_data)
                
                return {
                    "success": True,
                    "contact_id": contact_id,
                    "contact_result": contact_result,
                    "note_result": note_result,
                    "deal_result": deal_result if deal_result else {"message": "No deal created"}
                }
            else:
                return contact_result
                
        except Exception as e:
            logger.error(f"HubSpot save error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _build_contact_properties(self, contact_info: Dict, category: str, extracted_data: Dict) -> Dict:
        """Contact properties oluştur"""
        
        # Temel properties
        properties = {
            "email": contact_info['email'],
            "firstname": contact_info['firstname'] or "",
            "lastname": contact_info['lastname'] or "",
            "phone": contact_info['phone'],
            "lifecyclestage": "lead",
            "hs_lead_status": "NEW",
            "lead_source": "Website Form",
            "original_source": "Tally Form"
        }
        
        # Kategori özel properties
        if category == 'education':
            education_data = extracted_data.get('education', {})
            
            if education_data.get('gpa'):
                try:
                    properties["gpa"] = float(education_data['gpa'])
                except (ValueError, TypeError):
                    properties["gpa_text"] = str(education_data['gpa'])
            
            if education_data.get('budget'):
                try:
                    properties["education_budget"] = float(education_data['budget'])
                except (ValueError, TypeError):
                    properties["education_budget_text"] = str(education_data['budget'])
            
            if education_data.get('programs'):
                properties["education_level"] = ', '.join(education_data['programs'])
            
            properties["hs_lead_status"] = "EDUCATION_INQUIRY"
            
        elif category == 'legal':
            legal_data = extracted_data.get('legal', {})
            
            if legal_data.get('selected_services'):
                properties["legal_service_type"] = legal_data['services_text']
            
            if legal_data.get('topic'):
                properties["legal_notes"] = legal_data['topic']
            
            if legal_data.get('urgency_level'):
                properties["priority"] = legal_data['urgency_level'].upper()
            
            properties["hs_lead_status"] = "LEGAL_INQUIRY"
            
        elif category == 'business':
            business_data = extracted_data.get('business', {})
            
            if business_data.get('company_name'):
                properties["company"] = business_data['company_name']
            
            if business_data.get('sectors_text'):
                properties["industry"] = business_data['sectors_text']
            
            if business_data.get('business_type'):
                properties["business_type"] = business_data['business_type']
            
            properties["hs_lead_status"] = "BUSINESS_INQUIRY"
            properties["meeting_required"] = "true"
        
        # Boş değerleri temizle
        properties = {k: v for k, v in properties.items() if v and str(v).strip()}
        
        logger.info(f"Built {len(properties)} properties for {category} contact")
        
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
            
            if education_data.get('priority_level'):
                note_body += f"⚡ Öncelik: {education_data['priority_level'].upper()}\n"
        
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
            
            if legal_data.get('urgency_level'):
                note_body += f"🚨 Aciliyet: {legal_data['urgency_level'].upper()}\n"
                
                if legal_data['urgency_level'] == 'urgent':
                    note_body += "⚠️ ACİL DURUM - HEMEN İLETİŞİM GEREKLİ!\n"
        
        elif category == 'business':
            business_data = extracted_data.get('business', {})
            note_body += "💼 TİCARİ DANIŞMANLIK\n"
            note_body += "=" * 30 + "\n"
            
            if business_data.get('company_name'):
                note_body += f"🏢 Şirket: {business_data['company_name']}\n"
            
            if business_data.get('sector'):
                note_body += f"🏭 Ana Sektör: {business_data['sector']}\n"
            
            if business_data.get('selected_sectors'):
                note_body += f"📈 Faaliyet Alanları:\n"
                for sector in business_data['selected_sectors']:
                    note_body += f"  • {sector}\n"
                note_body += "\n"
            
            if business_data.get('business_type'):
                note_body += f"📊 İş Tipi: {business_data['business_type']}\n"
            
            note_body += f"📅 Meeting Gerekli: EVET\n"
            
            # Business meeting link'i dinamik olarak al
            try:
                from config.settings import Config
                meeting_link = Config.BUSINESS_MEETING_LINK
            except ImportError:
                meeting_link = "TBD"
            note_body += f"🔗 Meeting Link: {meeting_link}\n"
        
        # Contact info ekle
        note_body += f"\n📧 Email: {extracted_data.get('email', '')}\n"
        note_body += f"📞 Telefon: {extracted_data.get('phone', '')}\n"
        note_body += f"\n🤖 Otomatik webhook kaydı - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        return note_body
    
    def _create_business_deal(self, contact_id: str, extracted_data: Dict) -> Dict:
        """Business contact için deal oluştur"""
        
        try:
            business_data = extracted_data.get('business', {})
            company_name = business_data.get('company_name', 'Unnamed Company')
            
            deal_properties = {
                "dealname": f"UK Market Entry - {company_name}",
                "dealstage": "appointmentscheduled",  # İlk aşama
                "pipeline": "default",
                "amount": "0",  # Başlangıçta 0, sonra güncellenecek
                "closedate": self._calculate_expected_close_date(),
                "deal_source": "Website Form",
                "deal_type": "UK Market Entry"
            }
            
            # Deal oluştur
            url = f"{self.base_url}/deals"
            payload = {"properties": deal_properties}
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                deal_result = response.json()
                deal_id = deal_result.get('id')
                
                # Deal'ı contact ile ilişkilendir
                association_result = self._associate_deal_to_contact(deal_id, contact_id)
                
                logger.info(f"Business deal created - ID: {deal_id}")
                
                return {
                    "success": True,
                    "deal_id": deal_id,
                    "deal_name": deal_properties["dealname"],
                    "association_result": association_result
                }
            else:
                logger.error(f"Deal creation error: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Deal creation error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _associate_deal_to_contact(self, deal_id: str, contact_id: str) -> Dict:
        """Deal'ı contact ile ilişkilendir"""
        
        try:
            url = f"{self.base_url}/deals/{deal_id}/associations/contacts/{contact_id}/3"  # 3 = deal_to_contact
            
            response = requests.put(url, headers=self.headers, timeout=30)
            
            if response.status_code in [200, 201]:
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_expected_close_date(self) -> str:
        """Expected close date hesapla (3 ay sonra)"""
        expected_date = datetime.now() + timedelta(days=90)
        return expected_date.strftime('%Y-%m-%d')
    
    def update_deal_stage(self, deal_id: str, new_stage: str, amount: float = None) -> Dict:
        """Deal stage güncelle"""
        
        try:
            properties = {"dealstage": new_stage}
            
            if amount:
                properties["amount"] = str(amount)
            
            url = f"{self.base_url}/deals/{deal_id}"
            payload = {"properties": properties}
            
            response = requests.patch(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Deal {deal_id} updated to stage: {new_stage}")
                return {"success": True, "deal_id": deal_id, "new_stage": new_stage}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_contact_activity(self, contact_id: str, activity_type: str, notes: str) -> Dict:
        """Contact'a aktivite ekle"""
        
        try:
            activity_body = f"{activity_type}\n\n{notes}\n\nOtomatik kayıt: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            url = f"{self.base_url}/notes"
            payload = {
                "properties": {
                    "hs_note_body": activity_body
                },
                "associations": [{
                    "to": {"id": str(contact_id)},
                    "types": [{
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 202
                    }]
                }]
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                return {"success": True, "activity_type": activity_type}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_task(self, contact_id: str, task_title: str, due_date: str, notes: str = "") -> Dict:
        """Contact için task oluştur"""
        
        try:
            task_properties = {
                "hs_task_subject": task_title,
                "hs_task_body": notes,
                "hs_task_status": "NOT_STARTED",
                "hs_task_priority": "HIGH",
                "hs_timestamp": due_date
            }
            
            url = f"{self.base_url}/tasks"
            payload = {"properties": task_properties}
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                task_result = response.json()
                task_id = task_result.get('id')
                
                # Task'ı contact ile ilişkilendir
                association_url = f"{self.base_url}/tasks/{task_id}/associations/contacts/{contact_id}/204"  # task_to_contact
                association_response = requests.put(association_url, headers=self.headers, timeout=30)
                
                logger.info(f"Task created and associated - ID: {task_id}")
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "task_title": task_title,
                    "associated": association_response.status_code in [200, 201]
                }
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Task creation error: {str(e)}")
            return {"success": False, "error": str(e)}