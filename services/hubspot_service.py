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
        
        # Lead status'u education için güncelle
        properties["hs_lead_status"] = "NEW"  # Güvenli değer
        
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
        
        properties["hs_lead_status"] = "NEW"
    
    # Boş değerleri temizle
    properties = {k: v for k, v in properties.items() if v and str(v).strip()}
    
    logger.info(f"Built {len(properties)} properties for {category} contact")
    logger.debug(f"Properties: {list(properties.keys())}")
    
    return properties