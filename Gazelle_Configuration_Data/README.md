# Gazelle Configuration Data Analysis

## Folder Contents

This folder contains XML configuration files exported from the Gazelle EVS system:

1. **hl7MessageProfiles.xml** - HL7 v2 message profile definitions
2. **configurations.xml** - Actor, integration profile, and transaction configurations
3. **standards.xml** - Standards and protocol definitions
4. **auditMessages.xml** - Audit message configurations

## Key Findings for vin.xml (REF^I12 Discharge Summary)

### Message Profile Details

From `hl7MessageProfiles.xml`, the REF^I12 message matches:

**Profile Identifier:**
- **OID:** `1.3.6.1.4.1.12559.11.35.10.1.20`
- **HL7 Version:** `2.4`
- **Domain:** `HEALTHLINK` (The national healthlink project)
- **Transaction:** `HL-3` (Discharge Summary Report)
- **Trigger Event:** `REF^I12^REF_I12`
- **Affinity Domain:** `HL` (HealthLink)

**Actors:**
- **From:** `HIS` (Hospital Information System)
- **To:** `GPSYS` (GP system)

**Transaction Details:**
- **Keyword:** `HL-3`
- **Name:** Discharge Summary Report
- **Status:** `FT` (Final Text)

### Other HealthLink HL7 v2.4 Transactions Found

1. **HL-12:** Laboratory result, Radiology result
   - Trigger: `ORU^R01^ORU_R01`
   - From: HIS → GPSYS

2. **HL-11:** Lab Order Acknowledgement
   - OID: `1.3.6.1.4.1.12559.11.35.10.1.16`
   - Version: 2.4

3. **HL-8:** Appointment Notification
   - OID: `1.3.6.1.4.1.12559.11.35.10.1.21`
   - Version: 2.4

### HL7 Version 2.4 Standard

From `standards.xml`:
- **Keyword:** `HL7v2.4`
- **Name:** HL7 Version 2.4
- **Network Type:** `HL7v2`

## API Testing Results

**Tested configurations (all failed):**

| Configuration | Result | Note |
|--------------|--------|------|
| OID: `1.3.6.1.4.1.12559.11.35.10.1.20` | 500 | Server error |
| objectType: `HEALTHLINK-HL-3` | 500 | Not recognized |
| objectType: `HL-3` | 500 | Not recognized |
| objectType: `HL` | 500 | Not recognized |
| objectType: `HEALTHLINK` | 500 | Not recognized |
| validationService: `HL7v2Validator` / `HL-3` | 400 | Invalid validator name |
| validationService: `HL7v2Validator` / `HEALTHLINK / HL-3 / REF^I12^REF_I12` | 400 | Invalid validator name |

## Conclusion

The configuration data provides valuable information about the message structure and expected profiles, but:

1. **Profile data ≠ Validator names:** The transaction codes (HL-3, HL-12, etc.) and domain keywords (HEALTHLINK) from these configuration files do not match the validator names expected by the EVS REST API.

2. **Configuration vs. Validation:** These XML files describe the *configuration* of systems using these profiles, not the *validator names* used by the EVS validation service.

3. **Missing link:** There's a missing mapping between:
   - Profile definitions (what we have in these files)
   - Validator names (what the API expects)

## Next Steps

The configuration files confirm we have the right message type (REF^I12, HL7 v2.4, HealthLink HL-3), but we still need to contact Gazelle/eHealth Ireland support to ask:

**Specific question to ask:**

> "I have HL7 v2.4 HealthLink messages (Transaction HL-3, REF^I12^REF_I12, OID 1.3.6.1.4.1.12559.11.35.10.1.20) that I need to validate via the REST API. 
>
> What `validationService.name` and `validator` values should I use in my API request for this message type?
>
> Or what `objectType` value corresponds to this HealthLink discharge summary profile?"

## File Summary

### hl7MessageProfiles.xml (2,215 lines)
Complete message profile definitions including:
- 30+ HL7 message profiles
- OIDs, versions, domains, actors, transactions
- eHealthIreland (EHI) and HealthLink (HL) profiles

### configurations.xml (34,840 lines)
Comprehensive system configuration including:
- Actor definitions
- Integration profiles
- Transaction mappings
- IHE profile configurations

### standards.xml
Standards and protocol definitions:
- HL7 v2.3.1, 2.4, 2.5, 2.5.1, 2.6
- HL7 v3
- FHIR
- DICOM, XDS, PIX, PDQ, etc.

### auditMessages.xml
Audit and logging configurations

---

**These files are valuable for understanding the system architecture, but don't directly provide the REST API validator names needed for our implementation.**
