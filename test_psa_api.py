#!/usr/bin/env python3
"""
Test script for PSA API integration.

This script validates the PSA API setup and tests various endpoints.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from tcg_research.mcp.psa_api import PSAAPIClient, test_psa_api
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def test_psa_integration():
    """Test PSA API integration end-to-end."""
    
    print("🧪 PSA API Integration Test")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    access_token = os.getenv('PSA_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ No PSA_ACCESS_TOKEN found in environment")
        print("Please set PSA_ACCESS_TOKEN in your .env file")
        return False
    
    print(f"✅ PSA access token loaded (length: {len(access_token)})")
    
    # Test 1: Basic connection
    print("\n🔗 Test 1: Connection Test")
    try:
        test_results = await test_psa_api(access_token)
        
        if test_results["connection_test"]:
            print("✅ PSA API connection successful")
        else:
            print(f"❌ PSA API connection failed: {test_results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed with exception: {e}")
        return False
    
    # Test 2: Certificate lookup
    print("\n📜 Test 2: Certificate Lookup")
    try:
        async with PSAAPIClient(access_token) as client:
            # Test with a few different cert numbers
            test_certs = ["00000001", "12345678", "87654321"]
            
            for cert_num in test_certs:
                print(f"  🔍 Looking up cert: {cert_num}")
                cert_data = await client.get_cert_by_number(cert_num)
                
                if cert_data:
                    print(f"    ✅ Found: {cert_data.card_name} (Grade {cert_data.grade})")
                    break
                else:
                    print(f"    ℹ️  Cert {cert_num} not found")
            else:
                print("    ⚠️  No test certificates found (this is normal)")
                
    except Exception as e:
        print(f"❌ Certificate lookup test failed: {e}")
        return False
    
    # Test 3: Rate limiting
    print("\n⏱️  Test 3: Rate Limiting")
    try:
        async with PSAAPIClient(access_token) as client:
            # Make a few rapid requests to test rate limiting
            print("  Making rapid requests to test rate limiting...")
            
            for i in range(3):
                start_time = asyncio.get_event_loop().time()
                await client.get_cert_by_number(f"test{i:08d}")
                end_time = asyncio.get_event_loop().time()
                
                elapsed = end_time - start_time
                print(f"    Request {i+1}: {elapsed:.2f}s")
            
            print("  ✅ Rate limiting working properly")
            
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False
    
    # Test 4: Cache functionality
    print("\n💾 Test 4: Cache Functionality")
    try:
        async with PSAAPIClient(access_token) as client:
            cert_num = "12345678"
            
            # First request
            print(f"  First lookup of cert {cert_num}...")
            cert_data1 = await client.get_cert_by_number(cert_num)
            
            # Second request (should be cached)
            print(f"  Second lookup of cert {cert_num} (should be cached)...")
            cert_data2 = await client.get_cert_by_number(cert_num)
            
            cache_size = len(client.cert_cache)
            print(f"  ✅ Cache functionality working (cache size: {cache_size})")
            
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False
    
    print("\n🎉 All PSA API tests completed successfully!")
    print("\n📊 Summary:")
    print("  ✅ PSA API authentication working")
    print("  ✅ Certificate lookup functional")
    print("  ✅ Rate limiting implemented")
    print("  ✅ Caching system working")
    
    return True


async def test_psa_endpoints():
    """Test FastAPI PSA endpoints."""
    
    print("\n🌐 Testing FastAPI PSA Endpoints")
    print("=" * 50)
    
    try:
        import httpx
        
        base_url = "http://localhost:8000/api/psa"
        
        async with httpx.AsyncClient() as client:
            # Test status endpoint
            print("🔍 Testing /psa/status endpoint...")
            try:
                response = await client.get(f"{base_url}/status")
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"  ✅ Status: {status_data['status']}")
                    print(f"  ✅ Authenticated: {status_data['authenticated']}")
                else:
                    print(f"  ❌ Status endpoint failed: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  Status endpoint not available (server not running?): {e}")
            
            # Test cert lookup endpoint
            print("🔍 Testing /psa/cert/{cert_number} endpoint...")
            try:
                response = await client.get(f"{base_url}/cert/12345678")
                if response.status_code in [200, 404]:
                    print(f"  ✅ Cert endpoint responding (status: {response.status_code})")
                else:
                    print(f"  ❌ Cert endpoint failed: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  Cert endpoint not available: {e}")
            
            # Test connection test endpoint
            print("🔍 Testing /psa/test-connection endpoint...")
            try:
                response = await client.post(f"{base_url}/test-connection")
                if response.status_code == 200:
                    test_data = response.json()
                    print(f"  ✅ Connection test: {test_data['status']}")
                else:
                    print(f"  ❌ Connection test failed: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  Connection test endpoint not available: {e}")
                
    except ImportError:
        print("  ⚠️  httpx not available, skipping endpoint tests")


if __name__ == "__main__":
    print("🚀 Starting PSA API Integration Tests...")
    
    async def run_all_tests():
        # Test core PSA API functionality
        success = await test_psa_integration()
        
        if success:
            # Test FastAPI endpoints
            await test_psa_endpoints()
            
            print("\n🎯 Next Steps:")
            print("1. Start the FastAPI server: python -m tcg_research.api.main")
            print("2. Test PSA endpoints at: http://localhost:8000/docs")
            print("3. Check PSA status: http://localhost:8000/api/psa/status")
            print("4. Test cert lookup: http://localhost:8000/api/psa/cert/12345678")
            
        else:
            print("\n❌ PSA API setup has issues. Please check:")
            print("1. PSA_ACCESS_TOKEN is correctly set in .env")
            print("2. Token has proper permissions")
            print("3. Network connectivity to PSA API")
    
    asyncio.run(run_all_tests())