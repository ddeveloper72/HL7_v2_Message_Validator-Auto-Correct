"""
Local Flask App Test Script
Starts the dashboard app and provides test instructions
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_environment():
    """Verify all required environment variables are set"""
    required_vars = {
        'AZURE_SQL_SERVER': 'Azure SQL Server address',
        'AZURE_SQL_DATABASE': 'Database name',
        'AZURE_SQL_USERNAME': 'Database username',
        'AZURE_SQL_PASSWORD': 'Database password',
        'ENCRYPTION_KEY': 'Encryption key for API keys',
        'AZURE_AD_CLIENT_ID': 'Azure AD Client ID',
        'AZURE_AD_CLIENT_SECRET': 'Azure AD Client Secret',
        'AZURE_AD_TENANT_ID': 'Azure AD Tenant ID'
    }
    
    print("\n" + "="*80)
    print("CHECKING ENVIRONMENT CONFIGURATION")
    print("="*80 + "\n")
    
    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                print(f"✓ {var}: {'*' * 10}")
            else:
                print(f"✓ {var}: {value[:30]}...")
        else:
            print(f"✗ {var}: NOT SET ({description})")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        print("\nPlease set these in your .env file before running the app.")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True

def print_test_instructions():
    """Print manual testing instructions"""
    print("\n" + "="*80)
    print("LOCAL TESTING INSTRUCTIONS")
    print("="*80 + "\n")
    
    print("The Flask app will start on http://localhost:5000")
    print("\nManual Test Steps:")
    print("\n1. LOGIN/AUTHENTICATION")
    print("   - Open http://localhost:5000")
    print("   - Click 'Login with Azure AD'")
    print("   - Complete authentication")
    
    print("\n2. SET API KEY")
    print("   - Go to Profile page")
    print("   - Enter your Gazelle API key")
    print("   - Click 'Save API Key'")
    print("   - Verify success message")
    
    print("\n3. UPLOAD AND VALIDATE FILE")
    print("   - Go to Dashboard")
    print("   - Upload a test HL7 file (e.g., from 'Healthlink Tests' folder)")
    print("   - Click 'Validate with Gazelle'")
    print("   - Wait for validation to complete")
    print("   - Verify report appears in dashboard")
    
    print("\n4. TEST AUTO-CORRECT (NEW UPLOAD)")
    print("   - Find a report with status 'FAILED'")
    print("   - Click 'Try Auto-Correct' button")
    print("   - Verify corrections are applied")
    print("   - Check that corrected file is saved to database")
    
    print("\n5. TEST AUTO-CORRECT (DATABASE REPORT) - THE FIX!")
    print("   - Refresh the page (or restart Flask app)")
    print("   - Go to Dashboard")
    print("   - Reports should load from database (db_XXX IDs)")
    print("   - Click 'Try Auto-Correct' on a failed database report")
    print("   - ✅ This should now WORK (previously failed with 404)")
    print("   - Verify corrections applied and new report saved")
    
    print("\n6. VERIFY DATABASE PERSISTENCE")
    print("   - Close browser completely")
    print("   - Restart Flask app")
    print("   - Login again")
    print("   - Go to Dashboard")
    print("   - Verify all previous reports are still there")
    print("   - Verify API key is still saved")
    
    print("\n7. DOWNLOAD CORRECTED FILES")
    print("   - Find a report with corrections applied")
    print("   - Click 'Download' button")
    print("   - Verify corrected file downloads")
    
    print("\n" + "="*80)
    print("\nReady to start testing!")
    print("Press Ctrl+C to stop the server when done.")
    print("="*80 + "\n")

def main():
    """Main function"""
    print("\n" + "="*80)
    print("LOCAL FLASK APP TEST")
    print("="*80)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Print test instructions
    print_test_instructions()
    
    # Start Flask app
    print("Starting Flask development server...\n")
    
    try:
        # Import and run the app
        from dashboard_app import app
        app.run(debug=True, host='localhost', port=5000)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        print("\n" + "="*80)
        print("TESTING COMPLETE")
        print("="*80)
        print("\nIf all tests passed:")
        print("  1. Review BUG_FIX_REPORT.md")
        print("  2. Commit changes to git")
        print("  3. Deploy to Heroku")
        print("  4. Test on production")
        print("\n")
    except Exception as e:
        print(f"\n❌ Error starting Flask app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
