# Gazelle EVS API Implementation Summary

## Project Status: API Authentication Working, Validator Configuration Needed

### Latest Update: January 27, 2026 - 5:15 PM

**✅ API Key Obtained and Configured**
- API Key: Active (expires February 25, 2026 at 11:00 PM GMT)
- Authentication: Working (no 401 errors)
- API Endpoint: Responding correctly

**❌ Current Issue: Validator Names Unknown**

The API is now accepting our authenticated requests, but returning different errors based on configuration:

| Configuration | Status Code | Meaning |
|--------------|-------------|---------|
| With `validationService` + `validator` | 400 Bad Request | Validator names don't exist/match |
| With `objectType` only | 500 Internal Server Error | Server can't auto-detect validator |
| Without either | 500 Internal Server Error | Missing required parameters |

### What We've Accomplished

1. **✓ Project Structure Created**
   - Flask web application with Bootstrap UI
   - Virtual environment (`.venv`) with proper dependencies
   - File upload and validation interface

2. **✓ API Documentation Found**
   - Swagger API Spec v3.0: https://app.swaggerhub.com/apis/gazelletestbed/gazelle-evs_client_api/3.0
   - Downloaded complete specification to `gazelle_api_spec.json`
   - Identified correct request format requirements

3. **✓ Correct API Format Identified**
   - Endpoint: `POST https://testing.ehealthireland.ie/evs/rest/validations`
   - Content-Type: `application/json` OR `application/xml` (EVS-42, EVS-43)
   - **CRITICAL**: Content must be base64-encoded (EVS-45)
   - **CRITICAL**: Must provide either:
     - `validationService` (name) + `validator` (name), OR
     - `objectType`

### Current Issue: 500 Internal Server Errors

**UPDATE: Authentication Working, Validator Configuration Needed**

With the API key configured, we're getting HTTP 400 Bad Request when specifying validators, which indicates:
- ✅ API key is valid and accepted
- ✅ Server is processing our requests
- ❌ The validator service/name combinations we're trying don't exist in the system

#### Test Results with API Key

**Tested Validator Combinations (All returned 400):**
- `SchematronValidator` / `HL7v2.4`
- `SchematronValidator` / `REF^I12^REF_I12`
- `HL7v2Validator` / `HL7v2.4`
- `HL7v2Validator` / `REF_I12`
- `MessageValidator` / `REF^I12^REF_I12`
- `XMLValidator` / `HL7v2`

**Tested ObjectType Values (All returned 500):**
- `HL7v2`
- `REF^I12^REF_I12`
- `HL7v2.4`

**Working Responses:**
- GET `/validations`: 405 Method Not Allowed ✓ (correct - POST only)
- Authentication: No 401 errors ✓

All API requests are returning HTTP 500 (Internal Server Error), regardless of format.

#### Attempted Formats

**JSON Format (EVS-43):**
```json
{
  "objects": [
    {
      "originalFileName": "vin.xml",
      "content": "<base64-encoded-content>",
      "objectType": "HL7v2"  // Also tried: "REF^I12^REF_I12", "HL7v2.4"
    }
  ]
}
```

**XML Format (EVS-42):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<validation xmlns="http://evsobjects.gazelle.ihe.net/">
    <objects>
        <object originalFileName="vin.xml" objectType="REF^I12^REF_I12">
            <content>base64-encoded-content</content>
        </object>
    </objects>
</validation>
```

**With ValidationService:**
```json
{
  "objects": [{
    "originalFileName": "vin.xml",
    "content": "base64-encoded-content"
  }],
  "validationService": {
    "name": "HL7v2Validator",
    "validator": "HL7v2.4"
  }
}
```

All resulted in HTTP 500.

### Possible Causes

1. **API Not Fully Deployed**
   - The REST API endpoints may not be properly configured on `testing.ehealthireland.ie`
   - The Swagger spec might describe a different deployment

2. **Authentication Required**
   - EVS-50, EVS-51: Optional `Authorization: GazelleAPIKey <key>` header
   - Server might require this for the API to function
   - Need to obtain API key from Gazelle administrators

3. **Validator Names Unknown**
   - The exact `validationService.name` and `validator` values are not documented
   - The `objectType` values might not match what's configured
   - Web UI shows: "REF^I12^REF_I12 / HL7v2.4 / HIS / HL-3 / HEALTHLINK"

4. **Server Configuration**
   - Testing instance may have different configuration than production
   - The API feature might not be enabled on this server

### What Works

- ✓ EVS Validator web UI at https://testing.ehealthireland.ie/evs/default/validator.seam
- ✓ Manual file upload through browser works
- ✓ Our Flask application structure is correct
- ✓ Base64 encoding is working properly
- ✓ API endpoint is accessible (returns 405 for GET, accepts POST)

### Sample File Details

**File:** `vin.xml`
- **Message Type:** REF^I12^REF_I12
- **HL7 Version:** 2.4
- **System:** Healthlink eDischargeSummary
- **Sending Facility:** St. Vincent's University Hospital
- **Size:** 31,789 bytes (42,388 base64-encoded)

### Next Steps Required

**IMMEDIATE: Contact eHealth Ireland / Gazelle Support**

Now that we have a working API key, we need to obtain the correct validator configuration:

**Questions to ask:**
1. ✅ ~~Do I need an API key?~~ (Yes, obtained and working)
2. **What are the exact `validationService.name` values available on testing.ehealthireland.ie?**
3. **What are the valid `validator` names for HL7 v2.4 Healthlink messages (REF^I12)?**
4. **Can I get a list of configured `objectType` values?**
5. **Is there an endpoint to query available validators?** (tried `/validators`, `/validationServices`, `/objectTypes` - all 404)

**Evidence to share with support:**
- API key is working (no 401 errors)
- Server responds to API endpoint (405 for GET, 400/500 for POST)
- All validator combinations tested return 400 Bad Request
- All objectType values tested return 500 Internal Server Error
- Request format matches Swagger specification exactly

**Alternative next actions:**
1. Check if there's API documentation specific to the eHealth Ireland deployment
2. Ask for example curl commands that work on their system
3. Request access to a working validator configuration for HL7v2

1. **Contact Gazelle Support**
   - Report 500 errors when using REST API
   - Request API key for authentication
   - Confirm API is enabled on testing.ehealthireland.ie
   - Ask for list of valid `objectType` and `validationService`/`validator` combinations

2. **Alternative: Examine Network Traffic**
   - Use browser DevTools to capture successful validation from web UI
   - Reverse-engineer the exact format the web UI uses
   - Note: Web UI uses JSF/SEAM framework, not REST API

3. **Test Different Deployment**
   - Swagger spec mentions it's from `gazelletestbed`
   - May need to test against different Gazelle instance
   - Contact: IHE Gazelle team

### Code Implementation

**Updated Files:**
- `app.py` - Flask application with Swagger-compliant format
- `test_direct_api.py` - Direct API testing script
- `test_xml_format.py` - XML format testing
- `test_validator_options.py` - Multiple format variations

**Working Code Structure:**
```python
import base64
import requests

# Read HL7 v2 XML file
with open('vin.xml', 'rb') as f:
    xml_content = f.read()

# Encode to base64
base64_content = base64.b64encode(xml_content).decode('utf-8')

# Prepare request
payload = {
    "objects": [{
        "originalFileName": "vin.xml",
        "content": base64_content,
        "objectType": "HL7v2"
    }]
}

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# POST to API
response = requests.post(
    'https://testing.ehealthireland.ie/evs/rest/validations',
    json=payload,
    headers=headers,
    timeout=60
)

# Expected: 201 Created with Location header
# Actual: 500 Internal Server Error
```

### API Requirements (from Swagger Spec)

**EVS-45:** Content must be base64-encoded ✓ **Implemented**

**EVS-46:** Must provide:
- `validationService` + `validator`, OR
- `objectType`
✓ **Implemented** (tried both)

**EVS-42:** XML format supported ✓ **Tested**

**EVS-43:** JSON format supported ✓ **Tested**

**EVS-50:** Optional API key in Authorization header ⚠ **Not tested** (don't have key)

### Error Messages

```
Status Code: 500
Content-Type: text/html; charset=iso-8859-1

<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>500 Internal Server Error</title>
</head><body>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error or
misconfiguration and was unable to complete
your request.</p>
```

This is an Apache error page, not an application-level error, suggesting server configuration issues.

### Contact Information

**Gazelle Testing Platform:**
- Base URL: https://testing.ehealthireland.ie
- Documentation: https://testing.ehealthireland.ie/gazelle-documentation/
- API Spec: https://app.swaggerhub.com/apis/gazelletestbed/gazelle-evs_client_api/3.0

**Potential Contacts:**
- IHE Gazelle project: https://gazelle.ihe.net
- eHealth Ireland support

---

## For Continuation

When resuming this project:

1. First check if you have obtained an API key
2. Test with API key in Authorization header
3. If still failing, contact Gazelle support with this summary
4. Consider alternative: scraping/automating the web UI (not ideal)
5. Or implement validation locally using HL7 v2 libraries

**Alternative Approach:**
If REST API remains non-functional, consider:
- Using Python hl7apy or hl7 libraries for local validation
- Implementing schema validation against HL7 v2.4 XSD
- Building custom Healthlink-specific validators
