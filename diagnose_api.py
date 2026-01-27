"""
Try alternative API approaches to diagnose the issue
"""
import requests
import json
import base64
from dotenv import load_dotenv
import os

load_dotenv()
GAZELLE_API_KEY = os.getenv('GAZELLE_API_KEY', '')

with open('vin.xml', 'rb') as f:
    xml_content = f.read()

base64_content = base64.b64encode(xml_content).decode('utf-8')

base_url = 'https://testing.ehealthireland.ie/evs/rest'

# Test 1: Try with specific validationService names from web UI
test_configs = [
    {
        "name": "Test 1: With validationService HL7v2Validator",
        "payload": {
            "objects": [{
                "originalFileName": "vin.xml",
                "content": base64_content
            }],
            "validationService": {
                "name": "HL7v2Validator",
                "validator": "REF^I12^REF_I12"
            }
        }
    },
    {
        "name": "Test 2: Just objectType without specific message type",
        "payload": {
            "objects": [{
                "originalFileName": "vin.xml",
                "content": base64_content,
                "objectType": "HL7v2"
            }]
        }
    },
    {
        "name": "Test 3: Try without any validation specification (let server auto-detect)",
        "payload": {
            "objects": [{
                "originalFileName": "vin.xml",
                "content": base64_content
            }]
        }
    }
]

headers_base = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'GazelleAPIKey {GAZELLE_API_KEY}'
}

print(f"Testing multiple configurations with API key...\n")

for i, test in enumerate(test_configs, 1):
    print(f"{'='*70}")
    print(f"{test['name']}")
    print(f"{'='*70}")
    
    try:
        response = requests.post(
            f'{base_url}/validations',
            json=test['payload'],
            headers=headers_base,
            timeout=30,
            verify=True
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code in [201, 202]:
            print(f"✅ SUCCESS!")
            print(f"Location: {response.headers.get('Location')}")
            if response.status_code == 201:
                print("This configuration works! Use this format.")
            break
        elif response.status_code == 400:
            print(f"❌ Bad Request")
            try:
                print(f"Error: {response.json()}")
            except:
                print(f"Error: {response.text[:300]}")
        elif response.status_code == 401:
            print(f"❌ Unauthorized - API key issue")
        elif response.status_code == 500:
            print(f"❌ Server Error (500)")
        else:
            print(f"⚠️  Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()

# Test 4: Check if we can GET the validations list or other endpoints
print(f"{'='*70}")
print("Test 4: Try GET requests to explore API")
print(f"{'='*70}")

endpoints_to_try = [
    '/validations',
    '/validators',
    '/validationServices',
    '/objectTypes'
]

for endpoint in endpoints_to_try:
    try:
        url = f'{base_url}{endpoint}'
        response = requests.get(
            url,
            headers={'Accept': 'application/json', 'Authorization': f'GazelleAPIKey {GAZELLE_API_KEY}'},
            timeout=10,
            verify=True
        )
        print(f"GET {endpoint}: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ Content: {response.text[:200]}...")
    except Exception as e:
        print(f"GET {endpoint}: Error - {e}")

print(f"\n{'='*70}")
print("Summary:")
print("If all tests show 500 errors, the REST API may not be properly")
print("configured on this server, even with valid authentication.")
print("Recommendation: Contact eHealth Ireland or Gazelle support.")
