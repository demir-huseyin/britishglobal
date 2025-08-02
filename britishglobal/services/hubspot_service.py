def _build_contact_properties(self, contact_info: Dict, category: str, extracted_data: Dict) -> Dict:
    """Contact properties oluştur - Güncellenmiş alan eşleştirmeleri"""
    
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
        
        # GPA alanı - HubSpot'ta "Gpa" olarak görünüyor
        if education_data.get('gpa'):
            try:
                properties["gpa"] = float(education_data['gpa'])
            except (ValueError, TypeError):
                properties["gpa"] = str(education_data['gpa'])
        
        # Budget alanı - HubSpot'ta "Budget" olarak görünüyor  
        if education_data.get('budget'):
            try:
                # Budget değerini sayısal olarak kaydet
                budget_value = str(education_data['budget']).replace('£', '').replace(',', '').strip()
                properties["budget"] = float(budget_value)
            except (ValueError, TypeError):
                properties["budget"] = str(education_data['budget'])
        
        # Education Level - HubSpot'ta "Education Level" olarak görünüyor
        if education_data.get('programs'):
            properties["education_level"] = ', '.join(education_data['programs'])
        
        properties["hs_lead_status"] = "EDUCATION_INQUIRY"
        
    elif category == 'legal':
        legal_data = extracted_data.get('legal', {})
        
        # Legal Service Type - HubSpot'ta "Legal Service Type" olarak görünüyor
        if legal_data.get('selected_services'):
            properties["legal_service_type"] = legal_data['services_text']
        
        # Legal konusu için özel alan gerekebilir
        if legal_data.get('topic'):
            properties["legal_topic"] = legal_data['topic']
        
        # Aciliyet seviyesi
        if legal_data.get('urgency_level'):
            properties["priority"] = legal_data['urgency_level'].upper()
        
        properties["hs_lead_status"] = "LEGAL_INQUIRY"
        
    elif category == 'business':
        business_data = extracted_data.get('business', {})
        
        # Şirket adı
        if business_data.get('company_name'):
            properties["company"] = business_data['company_name']
        
        # Sektör bilgisi - Annual Revenue alanı business için kullanılabilir
        if business_data.get('sectors_text'):
            properties["industry"] = business_data['sectors_text']
        
        # Business type
        if business_data.get('business_type'):
            properties["business_type"] = business_data['business_type']
        
        # Annual Revenue alanı için - eğer business formunda gelir bilgisi varsa
        if business_data.get('annual_revenue'):
            try:
                properties["annual_revenue"] = float(business_data['annual_revenue'])
            except (ValueError, TypeError):
                properties["annual_revenue"] = str(business_data['annual_revenue'])
        
        properties["hs_lead_status"] = "BUSINESS_INQUIRY"
        properties["meeting_required"] = "true"
    
    # Boş değerleri temizle
    properties = {k: v for k, v in properties.items() if v and str(v).strip()}
    
    logger.info(f"Built {len(properties)} properties for {category} contact")
    logger.debug(f"Properties: {properties}")  # Debug için
    
    return properties

# HubSpot property isimlerini kontrol etmek için yardımcı method
def get_contact_properties(self) -> Dict:
    """HubSpot'taki mevcut contact property'lerini listele"""
    
    try:
        url = "https://api.hubapi.com/crm/v3/properties/contacts"
        response = requests.get(url, headers=self.headers, timeout=30)
        
        if response.status_code == 200:
            properties_data = response.json()
            properties = {}
            
            for prop in properties_data.get('results', []):
                name = prop.get('name')
                label = prop.get('label')
                field_type = prop.get('type')
                properties[name] = {
                    'label': label,
                    'type': field_type
                }
            
            return {"success": True, "properties": properties}
        else:
            return {"success": False, "error": response.text}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# Form verilerini doğru kategorilere eşleştirme
def map_form_data_to_category(self, form_data: Dict) -> str:
    """Form verilerinden kategoriyi belirle"""
    
    # Form içeriğine göre kategori tespiti
    if any(key in form_data for key in ['gpa', 'education_level', 'budget']):
        return 'education'
    elif any(key in form_data for key in ['legal_service', 'legal_topic', 'urgency']):
        return 'legal'  
    elif any(key in form_data for key in ['company_name', 'sector', 'annual_revenue']):
        return 'business'
    else:
        # Default kategorisi
        return 'general'

# Test için property mapping'i kontrol et
def test_property_mapping(self, test_data: Dict) -> Dict:
    """Property mapping'i test et"""
    
    try:
        # Önce HubSpot'taki property'leri al
        props_result = self.get_contact_properties()
        
        if not props_result.get('success'):
            return props_result
        
        available_properties = props_result['properties']
        
        # Test verisi ile property'leri oluştur
        category = self.map_form_data_to_category(test_data)
        contact_info = {
            'email': test_data.get('email', 'test@example.com'),
            'firstname': test_data.get('firstname', 'Test'),
            'lastname': test_data.get('lastname', 'User'),
            'phone': test_data.get('phone', '+90 555 123 45 67')
        }
        
        properties = self._build_contact_properties(contact_info, category, test_data)
        
        # Hangi property'lerin HubSpot'ta mevcut olduğunu kontrol et
        missing_properties = []
        existing_properties = []
        
        for prop_name in properties.keys():
            if prop_name in available_properties:
                existing_properties.append({
                    'name': prop_name,
                    'label': available_properties[prop_name]['label'],
                    'type': available_properties[prop_name]['type'],
                    'value': properties[prop_name]
                })
            else:
                missing_properties.append(prop_name)
        
        return {
            "success": True,
            "category": category,
            "total_properties": len(properties),
            "existing_properties": existing_properties,
            "missing_properties": missing_properties,
            "available_custom_properties": [
                name for name, details in available_properties.items() 
                if name not in ['email', 'firstname', 'lastname', 'phone']
            ]
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}