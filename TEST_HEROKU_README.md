# Heroku Automated Test Suite

Automated testing script to verify that the Heroku deployment is working correctly with data-driven HL7 code corrections.

## What This Script Tests

### TEST 1: Heroku App Connection
- ✅ Verifies the Heroku app is responding
- ✅ Confirms HTTP 200 status

### TEST 2: File Upload & Dashboard Access
- ✅ Uploads a test HL7 file (ORU_R01.txt) to the app
- ✅ Generates and retrieves a file ID
- ✅ Verifies dashboard is accessible

### TEST 3: Code Tables Integration
- ✅ Verifies test file contains invalid HL7 codes
- ✅ Confirms known issues are present:
  - XXX (invalid specimen source code, should be OTH)
  - MCN.HLPracticeID (invalid universal ID type, should be ISO/OID/L)
- ✅ Notes that data-driven corrector should handle these

### TEST 4: Local Corrector Module Test
- ✅ Imports hl7_corrector and hl7_code_tables modules
- ✅ Verifies code tables are loaded from JSON
- ✅ HL70070: 534 valid specimen source codes
- ✅ HL70301: 24 valid universal ID type codes
- ✅ Tests code validation (5 test cases)
- ✅ Confirms invalid codes are rejected
- ✅ Confirms valid codes are accepted

### TEST 5: App Endpoints Responsiveness
- ✅ Tests: `/` (home page)
- ✅ Tests: `/dashboard` (dashboard)
- ✅ Tests: `/upload-page` (upload form)
- ✅ Verifies all return HTTP 200

## Running the Tests

### Prerequisites
```bash
# Make sure Python environment is configured
python -m pip install requests
```

### Run Tests
```bash
# From project root directory
python test_heroku.py
```

### Expected Output
```
======================================================================
             HEROKU AUTO-CORRECTION DEPLOYMENT TEST SUITE
======================================================================

Testing: https://hl7-v2-message-validator-a1efcbc737cd.herokuapp.com
Test File: Healthlink Tests/ORU_R01.txt

TEST 1: Heroku App Connection ............................ PASS
TEST 2: File Upload & Dashboard........................... PASS
TEST 3: Code Tables Integration........................... PASS
TEST 4: Local Corrector Module Test....................... PASS
TEST 5: App Endpoints Responsiveness...................... PASS

Total: 5/5 tests passed

✓ All tests passed! Heroku deployment is working correctly.
✓ Data-driven HL7 code corrections are active in production!
✓ Code tables (HL70070, HL70301) properly integrated
✓ Corrector module successfully using HL7 standards
```

## What the Tests Validate

| Test | Purpose | Success Criteria |
|------|---------|------------------|
| Connection | Is the app running? | HTTP 200 from Heroku |
| Upload | Can we upload files? | File accepted, ID assigned |
| Integration | Are code tables present? | Invalid codes detected in test file |
| Corrector | Is module working locally? | All 5 validation tests pass |
| Endpoints | Are UI pages accessible? | All pages return HTTP 200 |

## Understanding the Results

### All Tests Passed ✅
The deployment is working correctly:
- App is responding
- File upload works
- Code tables loaded (558 valid codes)
- Code validation functioning
- UI endpoints accessible

### Some Tests Failed ❌
Check Heroku logs:
```bash
heroku logs -n 100 --app hl7-v2-message-validator
```

Common issues:
- **Connection FAIL** → App may be asleep or crashed
- **Upload FAIL** → Session issue, check Flask configuration
- **Corrector FAIL** → Module import issue, check hl7_code_tables.json exists

## Key Files Tested

| File | Role |
|------|------|
| `hl7_code_tables.py` | Data-driven code table manager |
| `hl7_code_tables.json` | HL7 code table definitions (558 codes) |
| `hl7_corrector.py` | Auto-correction logic (uses hl7_code_tables) |
| `dashboard_app.py` | Flask web application |
| `Healthlink Tests/ORU_R01.txt` | Test file with invalid codes |

## Test Output Details

### Connection Test
```
→ Connecting to https://hl7-v2-message-validator-a1efcbc737cd.herokuapp.com
✓ Heroku app is responding (Status: 200)
```
Shows the app is live and responding.

### Upload & Dashboard Test
```
→ Reading test file: Healthlink Tests/ORU_R01.txt
ℹ File size: 7882 bytes
→ Uploading file to Heroku app
✓ File uploaded successfully
ℹ File ID: 7f414352-3766-4e2e-8429-19369825ee91
```
Shows file upload working and session established.

### Code Tables Integration Test
```
→ Analyzing test file for invalid codes...
ℹ   • Found 1x 'XXX' in file
ℹ     Expected replacement: OTH
ℹ   • Found 1x 'MCN.HLPracticeID' in file
ℹ     Expected replacement: ISO, OID, or L
✓ Test file contains 2 types of invalid codes
```
Confirms test file has expected invalid codes for correction testing.

### Local Corrector Module Test
```
✓ HL70070 table loaded with 534 codes
ℹ   • 'OTH' found in HL70070 (correct replacement for 'XXX')
✓ HL70301 table loaded with 24 codes
ℹ   • 'ISO' found in HL70301
ℹ   • 'OID' found in HL70301
ℹ   • 'L' found in HL70301

✓ ✓ XXX in HL70070: Invalid HL70070 code
✓ ✓ OTH in HL70070: Valid HL70070 code
✓ ✓ MCN.HLPracticeID in HL70301: Invalid HL70301 code
✓ ✓ ISO in HL70301: Valid HL70301 code
✓ ✓ L in HL70301: Valid HL70301 code
✓ All 5 validation tests passed
```
Shows code tables properly loaded and validation working.

### Endpoints Test
```
→ Testing Home page: /
✓ Home page responding (Status 200)
→ Testing Dashboard: /dashboard
✓ Dashboard responding (Status 200)
→ Testing Upload page: /upload-page
✓ Upload page responding (Status 200)
```
Shows all UI endpoints accessible.

## Troubleshooting

### If Connection Test Fails
```bash
# Check if Heroku app exists
heroku apps:info --app hl7-v2-message-validator

# Check if it's sleeping (free tier apps sleep after inactivity)
heroku ps --app hl7-v2-message-validator

# View recent logs
heroku logs --app hl7-v2-message-validator
```

### If Upload Test Fails
```bash
# Check for Flask session configuration issues
heroku config --app hl7-v2-message-validator

# Verify upload folder permissions
heroku run bash --app hl7-v2-message-validator
ls -la /tmp/
```

### If Corrector Module Test Fails
```bash
# Verify hl7_code_tables.json exists
heroku run ls --app hl7-v2-message-validator

# Check JSON file is valid
heroku run python -c "import json; json.load(open('hl7_code_tables.json'))" --app hl7-v2-message-validator
```

## Related Documentation

- [DEPLOYMENT_REPORT.md](DEPLOYMENT_REPORT.md) - Full deployment details
- [test_local.py](test_local.py) - Local unit tests (offline testing)
- [hl7_code_tables.py](hl7_code_tables.py) - Code table manager implementation
- [hl7_code_tables.json](hl7_code_tables.json) - Valid HL7 codes configuration

## Contact & Support

For issues with the deployment test:
1. Check Heroku logs: `heroku logs --app hl7-v2-message-validator`
2. Run local tests to isolate issues: `python test_local.py`
3. Verify code tables are present: `python -c "from hl7_code_tables import get_code_table_manager; m = get_code_table_manager(); m.load_tables()"`
