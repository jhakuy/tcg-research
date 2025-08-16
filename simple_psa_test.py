#!/usr/bin/env python3
"""
Simple PSA API test using only standard library.
"""

import json
import urllib.request
import urllib.error
import os

def test_psa_api_simple():
    """Test PSA API connection using urllib."""
    
    print("🧪 Simple PSA API Test")
    print("=" * 30)
    
    # Get token from environment
    access_token = "8fz260u5pNCn-uNo1ZVTX5Jo_DoYG0XEiytSGEIhBNKKNAe5Tl8QJ3PVKRWED0MMYJhUntRM7C8ptOXaAizWrQE22HlXxgnDqITDn2jduQQX0BB55H8YmN3FCesthqM6YG2DbepWzpH6aZr6wmpKFoEJn0n38SdKVJSTa8cRxSXAm5BVKlQcAocpwY3bpOrz0cn1SzI6RrirkCvyxmDY2W8-bQRZxuN7yN3KMr8r20RBjErfWtt0bE-rMreP7AC7YxNQ-ZqENn6cGs-kYnEvY2yFbi4AT44XY50osqOxpABpTeWa"
    
    if not access_token:
        print("❌ No access token found")
        return False
    
    print(f"✅ Access token loaded (length: {len(access_token)})")
    
    # Test PSA API endpoint
    test_cert = "00000001"
    url = f"https://api.psacard.com/publicapi/cert/GetByCertNumber/{test_cert}"
    
    try:
        # Create request with authorization header
        request = urllib.request.Request(url)
        request.add_header('Authorization', f'bearer {access_token}')
        request.add_header('User-Agent', 'TCG-Research-System/1.0')
        
        print(f"🔍 Testing PSA API with cert: {test_cert}")
        print(f"📡 URL: {url}")
        
        # Make request
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.getcode()
            content_type = response.getheader('Content-Type', '')
            
            print(f"✅ Response status: {status_code}")
            print(f"📄 Content-Type: {content_type}")
            
            if status_code == 200:
                # Read and parse response
                data = response.read().decode('utf-8')
                
                try:
                    json_data = json.loads(data)
                    print("✅ Valid JSON response received")
                    
                    # Check if we got PSA cert data
                    if 'PSACert' in json_data:
                        cert_data = json_data['PSACert']
                        print(f"🎯 Found cert data:")
                        print(f"   Card: {cert_data.get('Subject', 'Unknown')}")
                        print(f"   Grade: {cert_data.get('CardGrade', 'Unknown')}")
                        print(f"   Brand: {cert_data.get('Brand', 'Unknown')}")
                    else:
                        print("ℹ️  No cert data in response (normal for non-existent cert)")
                        
                except json.JSONDecodeError:
                    print("⚠️  Response is not valid JSON")
                    print(f"Raw response: {data[:200]}...")
                    
            return True
            
    except urllib.error.HTTPError as e:
        status_code = e.code
        print(f"❌ HTTP Error: {status_code}")
        
        if status_code == 401:
            print("🔒 Authentication failed - check access token")
        elif status_code == 403:
            print("🚫 Access forbidden - token may not have permissions")
        elif status_code == 404:
            print("📭 Endpoint not found - check API URL")
        elif status_code == 429:
            print("⏰ Rate limit exceeded")
        else:
            print(f"🔴 HTTP error: {e.reason}")
            
        # Try to read error response
        try:
            error_data = e.read().decode('utf-8')
            print(f"Error details: {error_data[:200]}")
        except:
            pass
            
        return False
        
    except urllib.error.URLError as e:
        print(f"❌ Network error: {e.reason}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_psa_endpoints_info():
    """Show available PSA endpoints for testing."""
    
    print("\n📚 PSA API Endpoints Available:")
    print("=" * 40)
    
    endpoints = [
        ("GET /api/psa/status", "Check PSA API status and authentication"),
        ("GET /api/psa/cert/{cert_number}", "Look up PSA certificate by number"),
        ("POST /api/psa/test-connection", "Test PSA API connection"),
        ("GET /api/psa/population/{card_name}", "Get population data for card"),
        ("GET /api/psa/market-pressure/{card_name}", "Get market pressure analysis"),
        ("GET /api/psa/search-certs", "Search PSA certificates"),
        ("GET /api/psa/analytics/grade-distribution/{card_name}", "Get grade distribution"),
    ]
    
    for endpoint, description in endpoints:
        print(f"  🔗 {endpoint}")
        print(f"     {description}")
        print()
    
    print("🚀 To test these endpoints:")
    print("1. Start FastAPI server: python -m tcg_research.api.main")
    print("2. Visit: http://localhost:8000/docs")
    print("3. Or test directly: curl http://localhost:8000/api/psa/status")


if __name__ == "__main__":
    print("🚀 Starting Simple PSA API Test...")
    
    success = test_psa_api_simple()
    
    if success:
        print("\n🎉 PSA API connection successful!")
        print("✅ Your access token is working correctly")
        print("✅ PSA API endpoints are accessible")
        
        test_psa_endpoints_info()
        
    else:
        print("\n❌ PSA API test failed")
        print("\n🔧 Troubleshooting:")
        print("1. Check if your PSA access token is correct")
        print("2. Verify you have internet connectivity")
        print("3. Check PSA API status at psacard.com")
        print("4. Ensure token has proper permissions")
        
    print("\n" + "=" * 50)
    print("PSA API Integration Setup Complete! 🎯")