# Contact Gazelle Support - Question Template

## Background

You have successfully configured API authentication and implemented the REST API client according to the Swagger specification. The configuration files show your message is:

**Message Details:**
- **Type:** HL7 v2.4 HealthLink Discharge Summary
- **Trigger Event:** REF^I12^REF_I12
- **Transaction:** HL-3 (Discharge Summary Report)
- **Profile OID:** 1.3.6.1.4.1.12559.11.35.10.1.20
- **Domain:** HEALTHLINK
- **From:** HIS (Hospital Information System)
- **To:** GPSYS (GP System)

**API Status:**
- ✅ API Key: Working (no 401 errors)
- ✅ Endpoint: Accessible
- ✅ Request Format: Correct per Swagger spec
- ❌ Validator Names: Unknown

---

## Email to Send to Support

**To:** eHealth Ireland Support / Gazelle Support Team  
**Subject:** REST API Validator Configuration for HealthLink HL7 v2.4 Messages

---

Hello,

I'm implementing validation for HL7 v2.4 HealthLink messages using the Gazelle EVS REST API at `https://testing.ehealthireland.ie/evs/rest/validations`.

I have a working API key and can successfully authenticate, but I need help with the correct validator configuration.

**My Message Profile:**
- **Message Type:** REF^I12^REF_I12 (Discharge Summary)
- **HL7 Version:** 2.4
- **Transaction:** HL-3 (Discharge Summary Report)
- **Profile OID:** 1.3.6.1.4.1.12559.11.35.10.1.20
- **Domain:** HEALTHLINK

**Request Format (per Swagger spec):**
```json
{
  "objects": [{
    "originalFileName": "discharge_summary.xml",
    "content": "<base64-encoded-content>"
  }],
  "validationService": {
    "name": "???",
    "validator": "???"
  }
}
```

**My Questions:**

1. What `validationService.name` value should I use for HL7 v2.4 HealthLink messages?

2. What `validator` name corresponds to the HL-3 / REF^I12^REF_I12 profile?

3. Alternatively, what `objectType` value should I specify instead of using validationService/validator?

4. Is there an API endpoint to query the list of available validators/objectTypes?

**What I've Tried:**
- Various combinations of "HL7v2Validator", "SchematronValidator" with "HL-3", "REF^I12^REF_I12", "HEALTHLINK"
- All return either 400 Bad Request or 500 Internal Server Error
- The profile OID as objectType also returns 500

**API Key Details:**
- Valid through: February 25, 2026
- Authentication: Working correctly

Could you please provide:
1. The exact validator configuration for HealthLink HL7 v2.4 messages
2. Any documentation specific to the eHealth Ireland Gazelle deployment
3. Example API requests that work on your system

Thank you for your assistance!

---

**Attachments to Include:**
1. Sample vin.xml file (if appropriate)
2. Screenshot of error response
3. API request/response logs

---

## Contact Information

**Possible Contacts:**
- eHealth Ireland Support: [Find contact info]
- IHE Gazelle: https://gazelle.ihe.net/content/contact
- Gazelle Testing Platform: https://testing.ehealthireland.ie

**Documentation Links:**
- Swagger API: https://app.swaggerhub.com/apis/gazelletestbed/gazelle-evs_client_api/3.0
- Gazelle Documentation: https://testing.ehealthireland.ie/gazelle-documentation/

---

## While Waiting for Response

Consider these alternatives:

### Option 1: Use the Web UI
- Navigate to: https://testing.ehealthireland.ie/evs/default/validator.seam
- Manually validate files to confirm system is working
- Inspect browser network traffic to see what the UI sends

### Option 2: Local Validation
- Implement HL7 v2.4 schema validation locally using Python libraries
- Use `hl7apy` or `python-hl7` for structure validation
- Build custom Healthlink-specific validators

### Option 3: Test Other Message Types
- Try the ORU^R01 profile (OID: 1.3.6.1.4.1.12559.11.35.10.1.12)
- See if different message types work
- May help identify which validators are configured

---

**Your implementation is complete and ready - you just need the correct validator names from the Gazelle team!**
