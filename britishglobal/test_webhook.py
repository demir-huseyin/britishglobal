#!/usr/bin/env python3
"""
British Global Webhook Hızlı Test Scripti
Tüm servisleri ve endpoint'leri test eder
"""

import requests
import json
import time
from datetime import datetime

# Test edilecek base URL (local veya production)
BASE_URL = "http://localhost:8080"  # Local test için
# BASE_URL = "https://your-cloud-run-url.com"  # Production test için

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Endpoint test helper"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        success = response.status_code == expected_status
        
        print(f"{'✅' if success else '❌'} {method} {endpoint} - Status: {response.status_code}")
        
        if not success:
            print(f"   Error: {response.text[:200]}")
        
        return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        
    except Exception as e:
        print(f"❌ {method} {endpoint} - Exception: {str(e)}")
        return False, str(e)

def run_tests():
    """Tüm testleri çalıştır"""
    
    print("🚀 British Global Webhook Test Suite")
    print("=" * 50)
    print(f"Testing: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # 1. Health Check
    print("\n📋 1. HEALTH CHECKS")
    print("-" * 30)
    
    success, result = test_endpoint("GET", "/")
    tests_total += 1
    if success: tests_passed += 1
    
    success, result = test_endpoint("GET", "/config")
    tests_total += 1
    if success: tests_passed += 1
    
    # 2. Service Health Checks
    print("\n🔧 2. SERVICE HEALTH CHECKS")
    print("-" * 30)
    
    services = ["email", "hubspot", "education", "legal", "business"]
    for service in services:
        success, result = test_endpoint("GET", f"/health/{service}")
        tests_total += 1
        if success: tests_passed += 1
    
    # 3. Category Email Tests
    print("\n📧 3. CATEGORY EMAIL TESTS")
    print("-" * 30)
    
    categories = ["education", "legal", "business"]
    for category in categories:
        success, result = test_endpoint("POST", f"/test/{category}")
        tests_total += 1
        if success: tests_passed += 1
        
        if success and isinstance(result, dict):
            email_success = result.get('test_result', {}).get('success', False)
            print(f"   📧 Email result: {'✅' if email_success else '❌'}")
    
    # 4. Debug Test
    print("\n🐛 4. DEBUG TEST")
    print("-" * 30)
    
    debug_data = {
        "data": {
            "responseId": "test_debug_123",
            "createdAt": datetime.now().isoformat(),
            "fields": [
                {"label": "Adınız Soyadınız", "value": "Test User"},
                {"label": "Mail Adresiniz", "value": "test@britishglobal.com.tr"},
                {"label": "Telefon Numaranız", "value": "+90 555 123 4567"},
                {"label": "Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Eğitim Danışmanlığı)", "value": True}
            ]
        }
    }
    
    success, result = test_endpoint("POST", "/debug", debug_data)
    tests_total += 1
    if success: tests_passed += 1
    
    if success and isinstance(result, dict):
        form_analysis = result.get('form_analysis', {})
        print(f"   📋 Extracted fields: {form_analysis.get('extracted_fields', 0)}")
        print(f"   🏷️ Category: {form_analysis.get('category', 'unknown')}")
        print(f"   ✉️ Has email: {'✅' if form_analysis.get('has_email') else '❌'}")
    
    # 5. Webhook Simulation
    print("\n🔄 5. WEBHOOK SIMULATION")
    print("-" * 30)
    
    webhook_data = {
        "eventId": "test_webhook_" + str(int(time.time())),
        "eventType": "form_response",
        "createdAt": datetime.now().isoformat(),
        "data": {
            "responseId": f"test_response_{int(time.time())}",
            "submissionId": f"test_submission_{int(time.time())}",
            "respondentId": "test_respondent_123",
            "formId": "test_form_456",
            "formName": "British Global Contact Form",
            "createdAt": datetime.now().isoformat(),
            "fields": [
                {
                    "key": "question_name",
                    "label": "Adınız Soyadınız", 
                    "type": "INPUT_TEXT",
                    "value": "Ahmet Yılmaz"
                },
                {
                    "key": "question_email",
                    "label": "Mail Adresiniz",
                    "type": "INPUT_EMAIL", 
                    "value": "ahmet.yilmaz@example.com"
                },
                {
                    "key": "question_phone",
                    "label": "Telefon Numaranız",
                    "type": "INPUT_PHONE",
                    "value": "+90 532 123 4567"
                },
                {
                    "key": "question_category",
                    "label": "Hangi Konuda Danışmanlık Almak İstiyorsunuz? (Ticari Danışmanlık)",
                    "type": "MULTIPLE_CHOICE",
                    "value": True
                },
                {
                    "key": "question_company",
                    "label": "Şirketinizin Adı",
                    "type": "INPUT_TEXT",
                    "value": "Yılmaz Tekstil Ltd"
                },
                {
                    "key": "question_sector",
                    "label": "Sektörünüz (Tekstil ve Giyim)",
                    "type": "MULTIPLE_CHOICE", 
                    "value": True
                }
            ]
        }
    }
    
    success, result = test_endpoint("POST", "/tally", webhook_data)
    tests_total += 1
    if success: tests_passed += 1
    
    if success and isinstance(result, dict):
        webhook_results = result.get('results', {})
        print(f"   🔗 HubSpot: {'✅' if webhook_results.get('hubspot') else '❌'}")
        print(f"   📧 Email: {'✅' if webhook_results.get('email') else '❌'}")
        print(f"   ✉️ Confirmation: {'✅' if webhook_results.get('confirmation') else '❌'}")
        print(f"   🏷️ Category: {result.get('category', 'unknown')}")
    
    # Test Sonuçları
    print("\n" + "=" * 50)
    print("📊 TEST SONUÇLARI")
    print("=" * 50)
    print(f"✅ Başarılı: {tests_passed}/{tests_total}")
    print(f"❌ Başarısız: {tests_total - tests_passed}/{tests_total}")
    print(f"📈 Başarı Oranı: {(tests_passed/tests_total)*100:.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 TÜM TESTLER BAŞARILI! Webhook sistemi hazır.")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test başarısız. Logları kontrol edin.")
    
    print("=" * 50)

if __name__ == "__main__":
    print("British Global Webhook Test Suite v1.0")
    print("Bu script tüm webhook fonksiyonlarını test eder.\n")
    
    # URL kontrolü
    user_url = input(f"Test URL'i (Enter = {BASE_URL}): ").strip()
    if user_url:
        BASE_URL = user_url.rstrip('/')
    
    print(f"\nTesting webhook at: {BASE_URL}")
    print("Starting tests in 3 seconds...")
    
    time.sleep(3)
    run_tests()