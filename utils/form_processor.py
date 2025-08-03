import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class FormProcessor:
    """Tally form verilerini işleyen sınıf"""
    
    def __init__(self):
        self.field_mappings = self._initialize_field_mappings()
    
    def _initialize_field_mappings(self) -> Dict:
        """Field mapping'lerini başlat"""
        return {
            # Temel bilgiler
            'name_fields': ['Adınız Soyadınız', 'Full Name', 'Ad Soyad'],
            'email_fields': ['Mail Adresiniz', 'E-mail Adresiniz', 'Email Address'],
            'phone_fields': ['Telefon Numaranız', 'Phone Number', 'Telefon'],
            'notes_fields': ['Not', 'Notlar', 'Ek Notlarınız', 'Additional Notes', 'Açıklama'],
            
            # Kategori belirleme
            'business_fields': ['Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Ticari Danışmanlık)'],
            'education_fields': ['Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Eğitim Danışmanlığı)'],
            'legal_fields': ['Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Vize ve Hukuki Danışmanlık)'],
            
            # Eğitim seviyesi
            'education_levels': {
                'lise': 'İlgilendiğiniz Eğitim Seviyesi (Lise (İngiltere\'de lise eğitimi almak isteyenler için))',
                'lisans': 'İlgilendiğiniz Eğitim Seviyesi (Lisans (Üniversite eğitimi))',
                'master': 'İlgilendiğiniz Eğitim Seviyesi (Yüksek Lisans (Master programları))',
                'doktora': 'İlgilendiğiniz Eğitim Seviyesi (Doktora (Phd programları))',
                'dil_okulu': 'İlgilendiğiniz Eğitim Seviyesi (Dil Okulları (Yetişkinler için genel, IELTS veya mesleki İngilizce))',
                'yaz_kampi': 'İlgilendiğiniz Eğitim Seviyesi (Yaz Kampı (12-18 yaş grubu))'
            },
            
            # Hukuk hizmetleri
            'legal_services': {
                'turistik_vize': 'Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Turistik Vize (Visitor Visa))',
                'ogrenci_vize': 'Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Öğrenci Vizesi (Tier 4 / Graduate Route))',
                'calisma_vize': 'Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Çalışma Vizesi (Skilled Worker, Health and Care vb.))',
                'aile_vize': 'Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Aile Birleşimi / Partner Vizesi)',
                'ilr': 'Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere\'de Süresiz Oturum (ILR) Başvurusu)',
                'vatandaslik': 'Hangi konularda hukuki destek almak istiyorsunuz? (İngiltere Vatandaşlık Başvurusu)',
                'vize_red': 'Hangi konularda hukuki destek almak istiyorsunuz? (Vize Reddi İtiraz ve Yeniden Başvuru Danışmanlığı)'
            },
            
            # Sektörler
            'business_sectors': {
                'ambalaj': 'Sektörünüz (Ambalaj ve Baskı Ürünleri)',
                'tekstil': 'Sektörünüz (Tekstil ve Giyim)',
                'ayakkabi': 'Sektörünüz (Ayakkabı ve Deri Ürünleri)',
                'mobilya': 'Sektörünüz (Mobilya ve Ev Dekorasyonu)',
                'gida': 'Sektörünüz (Gıda Ürünleri / Yiyecek-İçecek)',
                'taki': 'Sektörünüz (Takı, Bijuteri ve Aksesuar)',
                'hediye': 'Sektörünüz (Hediyelik Eşya)',
                'kozmetik': 'Sektörünüz (Kozmetik ve Kişisel Bakım)',
                'oyuncak': 'Sektörünüz (Oyuncak ve Kırtasiye)',
                'temizlik': 'Sektörünüz (Temizlik ve Hijyen Ürünleri)',
                'ev_gereci': 'Sektörünüz (Ev Gereçleri ve Mutfak Ürünleri)',
                'hirdavat': 'Sektörünüz (Hırdavat / Yapı Malzemeleri)',
                'otomotiv': 'Sektörünüz (Otomotiv Yan Sanayi)',
                'bahce': 'Sektörünüz (Bahçe ve Outdoor Ürünleri)',
                'diger_sektor': 'Sektörünüz (Diğer)'
            }
        }
    
    def _map_fields_to_structure(self, field_dict: Dict, data_section: Dict) -> Dict:
        """Field'ları yapılandırılmış veri haline getir"""
        
        extracted = {
            # Meta bilgiler
            'submission_id': data_section.get('responseId', ''),
            'submitted_at': data_section.get('createdAt', ''),
            
            # Temel bilgiler
            'name': self._get_field_value(field_dict, self.field_mappings['name_fields']),
            'email': self._get_field_value(field_dict, self.field_mappings['email_fields']),
            'phone': self._get_field_value(field_dict, self.field_mappings['phone_fields']),
            'notes': self._get_field_value(field_dict, self.field_mappings['notes_fields']),
            
            # Kategori boolean'ları
            'ticari': self._get_boolean_field(field_dict, self.field_mappings['business_fields'][0]),
            'egitim': self._get_boolean_field(field_dict, self.field_mappings['education_fields'][0]),
            'hukuk': self._get_boolean_field(field_dict, self.field_mappings['legal_fields'][0]),
            
            # Eğitim detayları
            'education': self._extract_education_data(field_dict),
            
            # Hukuk detayları
            'legal': self._extract_legal_data(field_dict),
            
            # Business detayları
            'business': self._extract_business_data(field_dict)
        }
        
        return extracted
    
    def _extract_education_data(self, field_dict: Dict) -> Dict:
        """Eğitim verilerini çıkar"""
        
        education_data = {
            'gpa': self._get_field_value(field_dict, ['Not Ortalamanız', 'Your GPA']),
            'budget': self._get_field_value(field_dict, [
                'Eğitim ve Konaklama için Düşündüğünüz Bütçe Nedir? (£)',
                'Budget for Education and Accommodation (£)'
            ]),
            'notes': self._get_field_value(field_dict, self.field_mappings['notes_fields']),
            'levels': {},
            'programs': []
        }
        
        # Eğitim seviyelerini kontrol et
        for level, field_name in self.field_mappings['education_levels'].items():
            if self._get_boolean_field(field_dict, field_name):
                education_data['levels'][level] = True
                education_data['programs'].append(level)
        
        return education_data
    
    def _extract_legal_data(self, field_dict: Dict) -> Dict:
        """Hukuk verilerini çıkar"""
        
        legal_data = {
            'topic': self._get_field_value(field_dict, [
                'Hangi konularda hukuki destek almak istiyorsunuz?',
                'What legal services do you need?'
            ]),
            'notes': self._get_field_value(field_dict, self.field_mappings['notes_fields']),
            'services': {},
            'selected_services': []
        }
        
        # Hukuk hizmetlerini kontrol et
        for service, field_name in self.field_mappings['legal_services'].items():
            if self._get_boolean_field(field_dict, field_name):
                legal_data['services'][service] = True
                legal_data['selected_services'].append(service)
        
        return legal_data
    
    def _extract_business_data(self, field_dict: Dict) -> Dict:
        """Business verilerini çıkar"""
        
        business_data = {
            'company_name': self._get_field_value(field_dict, ['Şirketinizin Adı', 'Company Name']),
            'sector': self._get_field_value(field_dict, ['Sektörünüz', 'Your Industry']),
            'notes': self._get_field_value(field_dict, self.field_mappings['notes_fields']),
            'sectors': {},
            'selected_sectors': []
        }
        
        # Sektörleri kontrol et
        for sector, field_name in self.field_mappings['business_sectors'].items():
            if self._get_boolean_field(field_dict, field_name):
                business_data['sectors'][sector] = True
                business_data['selected_sectors'].append(sector)
        
        return business_data
    
    # ... (diğer methodlar aynı kalıyor)
    
    def extract_form_data(self, tally_data: Dict) -> Dict:
        """Tally webhook verisinden form alanlarını çıkar"""
        
        try:
            if not isinstance(tally_data, dict):
                logger.warning("Webhook data is not a dictionary")
                return {}
            
            # Tally format: data.fields array
            data_section = tally_data.get('data', {})
            if not isinstance(data_section, dict):
                logger.warning("Data section is not a dictionary")
                return {}
            
            form_fields = data_section.get('fields', [])
            if not isinstance(form_fields, list):
                logger.warning("Fields is not a list")
                return {}
            
            # Fields'i dictionary'e çevir
            field_dict = {}
            for field in form_fields:
                if not isinstance(field, dict):
                    continue
                
                label = field.get('label', '')
                value = field.get('value')
                
                if value is not None and str(value).strip():
                    field_dict[label] = value
            
            logger.info(f"Extracted {len(field_dict)} fields from {len(form_fields)} total fields")
            
            # Structured data oluştur
            extracted = self._map_fields_to_structure(field_dict, data_section)
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting form data: {str(e)}")
            return {}
    
    def _get_field_value(self, field_dict: Dict, field_options: List[str]) -> str:
        """Birden fazla field option'dan değer al"""
        for field_name in field_options:
            if field_name in field_dict:
                return str(field_dict[field_name]).strip()
        return ""
    
    def _get_boolean_field(self, field_dict: Dict, field_name: str) -> bool:
        """Boolean field değeri al"""
        value = field_dict.get(field_name)
        return value is True or value == "true" or value == True
    
    def determine_category(self, extracted_data: Dict) -> str:
        """Form verilerine göre kategori belirle"""
        
        try:
            # Öncelik sırası: Boolean field'lar
            if extracted_data.get('ticari'):
                return 'business'
            elif extracted_data.get('egitim'):
                return 'education'
            elif extracted_data.get('hukuk'):
                return 'legal'
            
            # Boolean yoksa içerik analizi
            if (extracted_data.get('business', {}).get('company_name') or 
                extracted_data.get('business', {}).get('selected_sectors')):
                return 'business'
            
            if (extracted_data.get('education', {}).get('programs') or
                extracted_data.get('education', {}).get('gpa')):
                return 'education'
            
            if (extracted_data.get('legal', {}).get('selected_services') or
                extracted_data.get('legal', {}).get('topic')):
                return 'legal'
            
            # Default
            return 'general'
            
        except Exception as e:
            logger.error(f"Error determining category: {str(e)}")
            return 'general'
    
    def get_contact_info(self, extracted_data: Dict) -> Dict:
        """İletişim bilgilerini düzenli formatta al"""
        
        try:
            name = extracted_data.get('name', '').strip()
            email = extracted_data.get('email', '').strip()
            phone = extracted_data.get('phone', '').strip()
            
            # Name'i parse et
            name_parts = name.split(' ') if name else []
            firstname = name_parts[0] if name_parts else ''
            lastname = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
            return {
                'firstname': firstname,
                'lastname': lastname,
                'fullname': name,
                'email': email,
                'phone': phone,
                'valid': bool(email and firstname)  # Minimum validation
            }
            
        except Exception as e:
            logger.error(f"Error getting contact info: {str(e)}")
            return {
                'firstname': '', 'lastname': '', 'fullname': '',
                'email': '', 'phone': '', 'valid': False
            }
    
    def get_category_specific_data(self, extracted_data: Dict, category: str) -> Dict:
        """Kategori özel verileri al"""
        
        if category == 'education':
            return self._format_education_data(extracted_data.get('education', {}))
        elif category == 'legal':
            return self._format_legal_data(extracted_data.get('legal', {}))
        elif category == 'business':
            return self._format_business_data(extracted_data.get('business', {}))
        else:
            return {}
    
    def _format_education_data(self, education_raw: Dict) -> Dict:
        """Eğitim verilerini formatla"""
        
        # Program isimlerini Türkçe'ye çevir
        program_names = {
            'lise': 'Lise (İngiltere)',
            'lisans': 'Lisans (Üniversite)',
            'master': 'Yüksek Lisans (Master)',
            'doktora': 'Doktora (PhD)',
            'dil_okulu': 'Dil Okulu',
            'yaz_kampi': 'Yaz Kampı (12-18 yaş)'
        }
        
        selected_programs = []
        for program in education_raw.get('programs', []):
            if program in program_names:
                selected_programs.append(program_names[program])
        
        budget = education_raw.get('budget', '')
        budget_formatted = ""
        if budget:
            try:
                budget_num = float(budget.replace(',', ''))
                budget_formatted = f"£{budget_num:,.0f}"
            except (ValueError, TypeError):
                budget_formatted = f"£{budget}"
        
        return {
            'programs': selected_programs,
            'programs_text': ', '.join(selected_programs),
            'gpa': education_raw.get('gpa', ''),
            'budget': budget,
            'budget_formatted': budget_formatted,
            'notes': education_raw.get('notes', ''),
            'priority_level': self._determine_education_priority(education_raw)
        }
    
    def _format_legal_data(self, legal_raw: Dict) -> Dict:
        """Hukuk verilerini formatla"""
        
        service_names = {
            'turistik_vize': 'Turistik Vize (Visitor)',
            'ogrenci_vize': 'Öğrenci Vizesi (Student)',
            'calisma_vize': 'Çalışma Vizesi (Work)',
            'aile_vize': 'Aile Birleşimi (Family)',
            'ilr': 'Süresiz Oturum (ILR)',
            'vatandaslik': 'Vatandaşlık (Citizenship)',
            'vize_red': 'Vize Red İtiraz (Appeal)'
        }
        
        selected_services = []
        for service in legal_raw.get('selected_services', []):
            if service in service_names:
                selected_services.append(service_names[service])
        
        return {
            'services': selected_services,
            'services_text': ', '.join(selected_services),
            'topic': legal_raw.get('topic', ''),
            'notes': legal_raw.get('notes', ''),
            'urgency_level': self._determine_legal_urgency(legal_raw),
            'selected_services': legal_raw.get('selected_services', [])  # Original keys for logic
        }
    
    def _format_business_data(self, business_raw: Dict) -> Dict:
        """Business verilerini formatla"""
        
        sector_names = {
            'ambalaj': 'Ambalaj ve Baskı',
            'tekstil': 'Tekstil ve Giyim',
            'ayakkabi': 'Ayakkabı ve Deri',
            'mobilya': 'Mobilya ve Dekorasyon',
            'gida': 'Gıda ve İçecek',
            'taki': 'Takı ve Aksesuar',
            'hediye': 'Hediyelik Eşya',
            'kozmetik': 'Kozmetik ve Bakım',
            'oyuncak': 'Oyuncak ve Kırtasiye',
            'temizlik': 'Temizlik Ürünleri',
            'ev_gereci': 'Ev Gereçleri',
            'hirdavat': 'Hırdavat',
            'otomotiv': 'Otomotiv',
            'bahce': 'Bahçe Ürünleri',
            'diger_sektor': 'Diğer Sektör'
        }
        
        selected_sectors = []
        for sector in business_raw.get('selected_sectors', []):
            if sector in sector_names:
                selected_sectors.append(sector_names[sector])
        
        return {
            'company_name': business_raw.get('company_name', ''),
            'sector': business_raw.get('sector', ''),
            'sectors': selected_sectors,
            'sectors_text': ', '.join(selected_sectors),
            'notes': business_raw.get('notes', ''),
            'requires_meeting': True,  # Her business başvurusu meeting gerektirir
            'business_type': self._determine_business_type(business_raw),
            'selected_sectors': business_raw.get('selected_sectors', [])  # Original keys for logic
        }
    
    def _determine_education_priority(self, education_data: Dict) -> str:
        """Eğitim başvurusu öncelik seviyesi"""
        
        programs = education_data.get('programs', [])
        
        if 'doktora' in programs:
            return 'high'  # PhD başvuruları kompleks
        elif 'master' in programs:
            return 'high'
        elif 'lisans' in programs:
            return 'medium'
        elif 'yaz_kampi' in programs:
            return 'urgent'  # Sezonluk, hızlı cevap gerekir
        else:
            return 'medium'
    
    def _determine_legal_urgency(self, legal_data: Dict) -> str:
        """Hukuk başvurusu aciliyet seviyesi"""
        
        services = legal_data.get('selected_services', [])
        
        if 'vize_red' in services:
            return 'urgent'  # Vize reddi acil
        elif 'turistik_vize' in services:
            return 'high'  # Seyahat planları var olabilir
        elif any(s in services for s in ['calisma_vize', 'ogrenci_vize']):
            return 'high'  # Başvuru deadlineları var
        else:
            return 'medium'
    
    def _determine_business_type(self, business_data: Dict) -> str:
        """Business türünü belirle"""
        
        sectors = business_data.get('selected_sectors', [])
        
        if len(sectors) > 3:
            return 'multi_sector'  # Çok sektörlü
        elif any(s in sectors for s in ['gida', 'kozmetik', 'tekstil']):
            return 'consumer_goods'  # Tüketici ürünleri
        elif any(s in sectors for s in ['hirdavat', 'otomotiv']):
            return 'industrial'  # Endüstriyel
        else:
            return 'general'
    
    def validate_submission(self, extracted_data: Dict) -> Dict:
        """Başvuru validasyonu"""
        
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Email kontrolü
        email = extracted_data.get('email', '')
        if not email or '@' not in email:
            validation['is_valid'] = False
            validation['errors'].append('Invalid or missing email address')
        
        # Name kontrolü
        name = extracted_data.get('name', '')
        if not name or len(name.split()) < 2:
            validation['warnings'].append('Name seems incomplete')
        
        # Kategori kontrolü
        category_fields = ['ticari', 'egitim', 'hukuk']
        if not any(extracted_data.get(field) for field in category_fields):
            validation['warnings'].append('No category selected')
        
        return validation
    
    def get_form_summary(self, extracted_data: Dict) -> Dict:
        """Form özetini al"""
        
        category = self.determine_category(extracted_data)
        contact = self.get_contact_info(extracted_data)
        validation = self.validate_submission(extracted_data)
        
        summary = {
            'submission_id': extracted_data.get('submission_id', ''),
            'category': category,
            'contact_name': contact.get('fullname', ''),
            'contact_email': contact.get('email', ''),
            'is_valid': validation['is_valid'],
            'has_errors': len(validation['errors']) > 0,
            'has_warnings': len(validation['warnings']) > 0,
            'has_notes': bool(extracted_data.get('notes', '')),
            'timestamp': datetime.now().isoformat()
        }
        
        # Kategori özel özet bilgileri
        if category == 'education':
            education_data = extracted_data.get('education', {})
            summary['education_summary'] = {
                'programs_count': len(education_data.get('programs', [])),
                'has_budget': bool(education_data.get('budget')),
                'has_gpa': bool(education_data.get('gpa')),
                'has_notes': bool(education_data.get('notes')),
                'priority': education_data.get('priority_level', 'medium')
            }
        
        elif category == 'legal':
            legal_data = extracted_data.get('legal', {})
            summary['legal_summary'] = {
                'services_count': len(legal_data.get('selected_services', [])),
                'has_topic': bool(legal_data.get('topic')),
                'has_notes': bool(legal_data.get('notes')),
                'urgency': legal_data.get('urgency_level', 'medium')
            }
        
        elif category == 'business':
            business_data = extracted_data.get('business', {})
            summary['business_summary'] = {
                'has_company_name': bool(business_data.get('company_name')),
                'sectors_count': len(business_data.get('selected_sectors', [])),
                'has_notes': bool(business_data.get('notes')),
                'business_type': business_data.get('business_type', 'general'),
                'requires_meeting': True
            }
        
        return summary