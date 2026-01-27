"""
Try to find working validator names by testing variations
Based on the web UI showing: REF^I12^REF_I12 / HL7v2.4 / HIS / HL-3 / HEALTHLINK
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

# Try different validator service and name combinations
validator_tests = [
    # Based on Swagger example: SchematronValidator / ANS - CR-BIO - v2021-02-15
    {"service": "SchematronValidator", "validator": "HL7v2.4"},
    {"service": "SchematronValidator", "validator": "REF^I12^REF_I12"},
    {"service": "SchematronValidator", "validator": "HEALTHLINK"},
    
    # Try HL7-specific validators
    {"service": "HL7v2Validator", "validator": "HL7v2.4"},
    {"service": "HL7v2Validator", "validator": "2.4"},
    {"service": "HL7v2Validator", "validator": "REF_I12"},
    
    # Try message-type specific
    {"service": "MessageValidator", "validator": "REF^I12^REF_I12"},
    {"service": "MessageValidator", "validator": "HL7v2.4"},
    
    # Try generic
    {"service": "XMLValidator", "validator": "HL7v2"},
    {"service": "Validator", "validator": "HL7v2.4"},
]

url = 'https://testing.ehealthireland.ie/evs/rest/validations'

print(f"Testing validator service/name combinations...\n")

for i, test in enumerate(validator_tests, 1):
    payload = {
        "objects": [{
            "originalFileName": "vin.xml",
            "content": base64_content
        }],
        "validationService": {
            "name": test["service"],
            "validator": test["validator"]
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'GazelleAPIKey {GAZELLE_API_KEY}'
    }
    
    print(f"{i:2d}. {test['service']:25s} / {test['validator']:25s} ... ", end='')
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30, verify=True)
        
        if response.status_code == 201:
            print(f"✅ SUCCESS (201)")
            print(f"\n{'='*70}")
            print(f"WORKING CONFIGURATION FOUND!")
            print(f"  Service: {test['service']}")
            print(f"  Validator: {test['validator']}")
            print(f"  Location: {response.headers.get('Location')}")
            print(f"{'='*70}\n")
            break
        elif response.status_code == 202:
            print(f"✅ ACCEPTED (202)")
            print(f"  Location: {response.headers.get('Location')}")
            break
        elif response.status_code == 400:
            print(f"⚠️  400 Bad Request")
        elif response.status_code == 401:
            print(f"❌ 401 Unauthorized")
        elif response.status_code == 404:
            print(f"❌ 404 Not Found")
        elif response.status_code == 500:
            print(f"❌ 500 Server Error")
        else:
            print(f"? {response.status_code}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout")
    except Exception as e:
        print(f"❌ Error: {str(e)[:50]}")

print(f"\nIf no success found, the validator names may need to be obtained from Gazelle admins.")
