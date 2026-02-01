"""
Heroku Deployment Helper Script
Guides through deployment process with safety checks
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Run a shell command and return output"""
    print(f"\n{description}...")
    print(f"Command: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"✓ {description} successful")
            if result.stdout:
                print(result.stdout[:500])  # Show first 500 chars
            return True, result.stdout
        else:
            print(f"✗ {description} failed")
            if result.stderr:
                print(result.stderr[:500])
            return False, result.stderr
    except Exception as e:
        print(f"✗ Error: {e}")
        return False, str(e)

def check_git_status():
    """Check if there are uncommitted changes"""
    print("\n" + "="*80)
    print("CHECKING GIT STATUS")
    print("="*80)
    
    success, output = run_command("git status --short", "Checking git status")
    if not success:
        return False
    
    if output.strip():
        print("\n⚠️  You have uncommitted changes:")
        print(output)
        response = input("\nDo you want to commit these changes? (yes/no): ").lower()
        if response == 'yes':
            message = input("Enter commit message: ")
            if not message:
                message = "Fix: Auto-correct works with database reports"
            
            run_command("git add .", "Staging files")
            run_command(f'git commit -m "{message}"', "Committing changes")
        else:
            print("⚠️  Proceeding without committing changes")
    else:
        print("✓ No uncommitted changes")
    
    return True

def check_heroku_remote():
    """Verify Heroku remote is configured"""
    print("\n" + "="*80)
    print("CHECKING HEROKU REMOTE")
    print("="*80)
    
    success, output = run_command("git remote -v", "Checking git remotes")
    if not success:
        return False
    
    if 'heroku' in output.lower():
        print("✓ Heroku remote configured")
        # Extract Heroku app name
        for line in output.split('\n'):
            if 'heroku' in line.lower() and 'push' in line:
                print(f"  {line.strip()}")
        return True
    else:
        print("✗ Heroku remote not found")
        app_name = input("Enter your Heroku app name: ")
        if app_name:
            success, _ = run_command(f"heroku git:remote -a {app_name}", "Adding Heroku remote")
            return success
        return False

def verify_heroku_config():
    """Check critical environment variables on Heroku"""
    print("\n" + "="*80)
    print("VERIFYING HEROKU CONFIGURATION")
    print("="*80)
    
    critical_vars = [
        'AZURE_SQL_SERVER',
        'AZURE_SQL_DATABASE',
        'ENCRYPTION_KEY',
        'SESSION_SECRET_KEY',
        'AZURE_AD_CLIENT_ID'
    ]
    
    success, output = run_command("heroku config", "Fetching Heroku config")
    if not success:
        print("✗ Cannot verify Heroku config")
        return False
    
    missing = []
    for var in critical_vars:
        if var not in output:
            missing.append(var)
            print(f"✗ Missing: {var}")
        else:
            print(f"✓ Found: {var}")
    
    if missing:
        print(f"\n⚠️  Missing required variables: {', '.join(missing)}")
        print("Please set these before deploying:")
        for var in missing:
            print(f"  heroku config:set {var}=<value>")
        return False
    
    print("\n✓ All critical environment variables present")
    return True

def run_tests():
    """Run local tests before deployment"""
    print("\n" + "="*80)
    print("RUNNING TESTS")
    print("="*80)
    
    test_files = [
        'test_database_and_autocorrect.py',
        'test_integration_autocorrect.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\nRunning {test_file}...")
            success, output = run_command(
                f"C:/Users/Duncan/VS_Code_Projects/HL7_v2_Message_Validator-Auto-Correct/.venv/Scripts/python.exe {test_file}",
                f"Test: {test_file}"
            )
            if not success:
                print(f"✗ Test {test_file} failed")
                response = input("Continue anyway? (yes/no): ").lower()
                if response != 'yes':
                    return False
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    return True

def deploy_to_heroku():
    """Deploy to Heroku"""
    print("\n" + "="*80)
    print("DEPLOYING TO HEROKU")
    print("="*80)
    
    print("\n⚠️  This will deploy your code to production!")
    response = input("Are you sure you want to proceed? (yes/no): ").lower()
    
    if response != 'yes':
        print("Deployment cancelled")
        return False
    
    # Push to Heroku
    success, output = run_command("git push heroku main", "Pushing to Heroku")
    if not success:
        print("\n✗ Deployment failed!")
        print("Check the error messages above")
        return False
    
    print("\n✓ Deployment successful!")
    return True

def post_deployment_checks():
    """Perform post-deployment verification"""
    print("\n" + "="*80)
    print("POST-DEPLOYMENT CHECKS")
    print("="*80)
    
    # Check dyno status
    run_command("heroku ps", "Checking dyno status")
    
    # View recent logs
    print("\nFetching recent logs (last 50 lines)...")
    run_command("heroku logs -n 50", "Fetching logs")
    
    print("\n" + "="*80)
    print("DEPLOYMENT COMPLETE")
    print("="*80)
    
    print("\n✅ Next Steps:")
    print("1. Test login: https://your-app.herokuapp.com")
    print("2. Set API key in profile")
    print("3. Upload and validate a test file")
    print("4. Test auto-correct on NEW upload")
    print("5. Test auto-correct on DATABASE report (db_XXX) ← THE FIX!")
    print("6. Monitor logs: heroku logs --tail")
    
    print("\n📋 Full testing checklist in: DEPLOYMENT_CHECKLIST.md")

def main():
    """Main deployment workflow"""
    print("\n" + "="*80)
    print("HEROKU DEPLOYMENT HELPER")
    print("="*80)
    
    print("\nThis script will:")
    print("1. Check git status")
    print("2. Verify Heroku configuration")
    print("3. Run tests")
    print("4. Deploy to Heroku")
    print("5. Run post-deployment checks")
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    # Step 1: Git status
    if not check_git_status():
        print("✗ Git check failed")
        sys.exit(1)
    
    # Step 2: Heroku remote
    if not check_heroku_remote():
        print("✗ Heroku remote check failed")
        sys.exit(1)
    
    # Step 3: Heroku config
    if not verify_heroku_config():
        print("✗ Heroku config check failed")
        response = input("Continue anyway? (yes/no): ").lower()
        if response != 'yes':
            sys.exit(1)
    
    # Step 4: Run tests
    if not run_tests():
        print("✗ Tests failed")
        sys.exit(1)
    
    # Step 5: Deploy
    if not deploy_to_heroku():
        print("✗ Deployment failed")
        sys.exit(1)
    
    # Step 6: Post-deployment checks
    post_deployment_checks()
    
    print("\n🎉 Deployment process complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDeployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
