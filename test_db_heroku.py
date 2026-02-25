"""Test database connection on Heroku"""
import os
import sys

print("="*80)
print("DATABASE CONNECTION TEST")
print("="*80)

# Check environment variables
print("\n1. Environment Variables:")
print(f"   AZURE_SQL_SERVER: {os.getenv('AZURE_SQL_SERVER', 'NOT SET')}")
print(f"   AZURE_SQL_DATABASE: {os.getenv('AZURE_SQL_DATABASE', 'NOT SET')}")
print(f"   AZURE_SQL_USERNAME: {os.getenv('AZURE_SQL_USERNAME', 'NOT SET')}")
print(f"   AZURE_SQL_PASSWORD: {'***SET***' if os.getenv('AZURE_SQL_PASSWORD') else 'NOT SET'}")
print(f"   DB_DRIVER: {os.getenv('DB_DRIVER', 'NOT SET')}")

# Try to import pyodbc
print("\n2. Import pyodbc:")
try:
    import pyodbc
    print("   ✓ pyodbc imported successfully")
    print(f"   pyodbc version: {pyodbc.version}")
except Exception as e:
    print(f"   ✗ Failed to import pyodbc: {e}")
    sys.exit(1)

# Try to import db_utils
print("\n3. Import db_utils:")
try:
    import db_utils
    print(f"   ✓ db_utils imported from: {db_utils.__file__}")
except Exception as e:
    print(f"   ✗ Failed to import db_utils: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to create DatabaseManager instance
print("\n4. Create DatabaseManager:")
try:
    db = db_utils.DatabaseManager()
    print("   ✓ DatabaseManager created")
except Exception as e:
    print(f"   ✗ Failed to create DatabaseManager: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to get connection
print("\n5. Test database connection:")
try:
    conn = db.get_connection()
    print("   ✓ Connection established!")
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()
    print(f"   SQL Server version: {version[0][:50]}...")
    conn.close()
    print("   ✓ Connection closed successfully")
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("ALL TESTS PASSED!")
print("="*80)
