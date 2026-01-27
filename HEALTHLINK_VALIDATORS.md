# HealthLink HL7 v2.x Validators

## Available Validators on Gazelle EVS

All validators use the **"Gazelle HL7v2.x validator"** validation service.

| Message Type | Transaction | OID | Description |
|--------------|-------------|-----|-------------|
| REF^I12^REF_I12 | HL-3 | 1.3.6.1.4.1.12559.11.35.10.1.20 | Discharge Summary (Default) |
| ORU^R01^ORU_R01 | HL-12 | 1.3.6.1.4.1.12559.11.35.10.1.12 | Laboratory Results |
| ORL^O22^ORL_O22 | HL-11 | 1.3.6.1.4.1.12559.11.35.10.1.16 | Laboratory Order Response |
| VXU^V04^VXU_V04 | HL-16 | 1.3.6.1.4.1.12559.11.35.10.1.19 | Vaccination Update |
| SIU^S12^SIU_S12 | HL-8 | 1.3.6.1.4.1.12559.11.35.10.1.21 | Appointment Notification |
| OML^O21^OML_O21 | HL-13 | 1.3.6.1.4.1.12559.11.35.10.1.22 | Laboratory Order |
| RRI^R12^RRI_R12 | HL-9 | 1.3.6.1.4.1.12559.11.35.10.1.23 | Radiology Results Interpretation |
| ACK^GENERIC | HL-2 | 1.3.6.1.4.1.12559.11.35.10.1.24 | General Acknowledgement |
| ADT^A01^ADT_A01 | HL-1 | 1.3.6.1.4.1.12559.11.35.10.1.7 | Patient Admit |
| ADT^A03^ADT_A03 | HL-5 | 1.3.6.1.4.1.12559.11.35.10.1.9 | Patient Discharge |

## Payload Format (Working Configuration)

```json
{
  "objects": [
    {
      "originalFileName": "your_file.xml",
      "content": "BASE64_ENCODED_CONTENT_HERE"
    }
  ],
  "validationService": {
    "name": "Gazelle HL7v2.x validator",
    "validator": "1.3.6.1.4.1.12559.11.35.10.1.20"
  }
}
```

## Headers

```
Content-Type: application/json
Accept: application/json
Authorization: GazelleAPIKey YOUR_API_KEY_HERE
```

## Response

**Success (201 Created):**
```
Location: https://testing.ehealthireland.ie/evs/rest/validations/{OID}?privacyKey={KEY}
```

The `Location` header contains the URL to:
- Check validation status: `GET {Location}`
- View report: `GET {Location}/report`

## Usage in app.py

To change the validator, modify the `validator` OID in both endpoints:
- `/validate` - Line ~128
- `/validate-sample` - Line ~283

Example for Laboratory Results (ORU^R01):
```python
"validationService": {
    "name": "Gazelle HL7v2.x validator",
    "validator": "1.3.6.1.4.1.12559.11.35.10.1.12"  # ORU^R01
}
```

## Notes

- All validators support HL7 v2.4 format
- System actor: HIS (Hospital Information System)
- Domain: HEALTHLINK
- Content MUST be base64-encoded (EVS-45 requirement)
- API key authentication required for production use
