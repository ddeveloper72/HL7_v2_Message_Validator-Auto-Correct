# Gazelle EVS Application Configuration Review

## From Screenshot Analysis

Based on the Application Preferences screenshot, here are potentially relevant configurations:

### Key Sections Visible:

1. **Application Preferences**
   - Validation tool settings
   - Application URL configurations

2. **Validation Settings**
   - May contain validator service configurations
   - Object type mappings

3. **REST API Settings**
   - Look for REST API enabled/disabled toggle
   - API authentication settings

### What to Check/Configure:

#### 1. REST API Enablement
**Look for:** Settings that enable/disable the REST API functionality
- May be under "Web Services" or "API Configuration"
- Check if REST validation endpoint needs to be explicitly enabled

#### 2. Validator Service Configuration
**Look for:** 
- List of configured validation services (HL7v2Validator, SchematronValidator, etc.)
- Which validators are active/enabled
- Validator name mappings

#### 3. Object Type Definitions
**Look for:**
- Configured object types (HL7v2, HEALTHLINK, etc.)
- Mapping between object types and validation services
- Profile-to-validator associations

#### 4. HL7 Message Profile Settings
**Look for:**
- Which HL7 profiles are active
- Profile OID to validator name mappings
- Transaction code (HL-3, HL-12, etc.) configurations

### Recommended Actions:

1. **Navigate to Validation Configuration Section**
   - Look for "Validation Services" or "Validators" menu
   - Check which validators are registered in the system

2. **Check Object Type Mappings**
   - See if there's a mapping table showing:
     - Object Type → Validation Service → Validator
   - This would show the exact names to use in the API

3. **Review REST API Settings**
   - Confirm REST API is enabled
   - Check if there are any validator restrictions for API access
   - See if certain validators require special permissions

4. **Look for Documentation/Help**
   - Check if there's an inline help or documentation link
   - May show example API requests with actual validator names

### Questions to Ask While Navigating:

1. **In Validation Configuration:**
   - What validation services are installed and active?
   - What are their exact names as shown in the system?

2. **In Object Type Configuration:**
   - Is there a list of valid objectType values?
   - Can you see HEALTHLINK or HL7v2 configurations?

3. **In HL7 Profile Settings:**
   - Can you see the HL-3 transaction configuration?
   - Does it show which validator service handles it?

### Specific Items to Screenshot/Document:

If you can navigate to these sections, please capture:

1. **Validation Services list** - Shows all available validator service names
2. **Object Types list** - Shows all valid objectType values
3. **HL7 Profile mappings** - Shows which validators handle which profiles
4. **REST API configuration** - Shows any API-specific settings

### Expected Format Clues:

Based on the Swagger spec example, we're looking for configurations like:
```
Service Name: SchematronValidator
Validator: ANS - CR-BIO - v2021-02-15
```

For your HealthLink messages, there should be something like:
```
Service Name: [?]
Validator: [HL-3 or REF^I12^REF_I12 or similar]
Object Type: [HEALTHLINK or HL7v2 or similar]
```

### Navigation Paths to Try:

1. **Admin → Validation → Services**
2. **Admin → Configuration → Object Types**
3. **Admin → HL7 → Message Profiles**
4. **Admin → API → REST Configuration**
5. **Tools → Validators**

---

**Next Step:** Navigate through the admin interface to find the validation service configuration section and document the exact names shown there. Those are the names the REST API will accept!
