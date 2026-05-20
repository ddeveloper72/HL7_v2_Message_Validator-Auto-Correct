"""
Apply API Key Validity Dates Migration to Azure SQL Database
Run this script to add APIKeyValidFrom and APIKeyValidTo columns to Users table
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def apply_migration():
    """Apply the SQL migration to add API key validity date columns"""
    
    # Get database connection details
    server = os.getenv('AZURE_SQL_SERVER')
    database = os.getenv('AZURE_SQL_DATABASE')
    username = os.getenv('AZURE_SQL_USERNAME')
    password = os.getenv('AZURE_SQL_PASSWORD')
    
    # Use Windows ODBC driver for local execution (ignore .env DB_DRIVER setting)
    driver = 'ODBC Driver 18 for SQL Server'
    
    if not all([server, database, username, password]):
        print("❌ Missing database configuration in .env file")
        return False
    
    print(f"🔧 Connecting to Azure SQL Database: {server}/{database}")
    
    # Create connection string
    connection_string = (
        f'DRIVER={{{driver}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
        f'Encrypt=yes;'
        f'TrustServerCertificate=no;'
        f'Connection Timeout=60;'
    )
    
    try:
        # Connect to database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        print("✅ Connected successfully")
        print("\n📋 Applying migration...\n")
        
        # Read the SQL migration file
        with open('add_api_key_validity_dates.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Split by GO statements and execute each batch
        batches = [batch.strip() for batch in sql_script.split('GO') if batch.strip()]
        
        for i, batch in enumerate(batches, 1):
            # Skip comment-only batches
            if batch.startswith('--') and '\n' not in batch:
                continue
                
            print(f"Executing batch {i}/{len(batches)}...")
            
            try:
                cursor.execute(batch)
                conn.commit()
                print(f"  ✅ Batch {i} completed")
                
                # If this batch returns results, print them
                if cursor.description:
                    rows = cursor.fetchall()
                    if rows:
                        print("\n  Results:")
                        for row in rows:
                            print(f"    {row}")
                        print()
                        
            except pyodbc.Error as e:
                # Some errors are OK (like "object already exists")
                error_msg = str(e)
                if 'already exists' in error_msg or 'Cannot drop' in error_msg:
                    print(f"  ⚠️  Batch {i}: {error_msg} (continuing...)")
                else:
                    print(f"  ❌ Batch {i} failed: {error_msg}")
                    raise
        
        print("\n🎉 Migration completed successfully!")
        print("\n📊 Verifying changes...")
        
        # Verify the columns were added (use new cursor to avoid sequence errors)
        cursor.close()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Users'
            AND COLUMN_NAME IN ('APIKeyValidFrom', 'APIKeyValidTo')
            ORDER BY COLUMN_NAME
        """)
        
        columns = cursor.fetchall()
        if columns:
            print("\n✅ New columns added to Users table:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
        else:
            print("\n⚠️  Could not verify new columns (they may already exist)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except pyodbc.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Migration file 'add_api_key_validity_dates.sql' not found")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("API Key Validity Dates Migration")
    print("=" * 80)
    print()
    
    success = apply_migration()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Test the application locally")
        print("  2. Update users' API keys with validity dates via profile page")
        print("  3. Deploy to Heroku/Docker with updated code")
    else:
        print("❌ Migration failed!")
        print("\nPlease check the error messages above and try again.")
    print("=" * 80)
