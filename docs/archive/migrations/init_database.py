"""Initialize database schema"""
from db_utils import DatabaseManager
import sys
import os

try:
    print("="*60)
    print("Database Schema Initialization")
    print("="*60)
    
    schema_file = 'database_schema.sql'
    if not os.path.exists(schema_file):
        print(f"❌ Error: {schema_file} not found")
        sys.exit(1)
    
    print(f"✓ Found schema file: {schema_file}")
    
    print("\nReading schema file...")
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    print(f"✓ Read {len(schema_sql)} characters")
    
    print("\nConnecting to database...")
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    print("✓ Connected successfully")
    
    # Split the SQL file by GO statements (SQL Server batch separator)
    batches = [batch.strip() for batch in schema_sql.split('GO') if batch.strip()]
    
    print(f"Executing {len(batches)} SQL batches...")
    
    for i, batch in enumerate(batches, 1):
        if batch.strip():
            print(f"  Batch {i}/{len(batches)}...")
            try:
                cursor.execute(batch)
                conn.commit()
            except Exception as e:
                # Check if error is "object already exists"
                if 'already an object' in str(e) or 'already exists' in str(e):
                    print(f"    ⚠️  Skipped (already exists)")
                else:
                    print(f"    ❌ Error: {e}")
                    raise
    
    cursor.close()
    conn.close()
    
    print("\n✅ Database schema created successfully!")
    print("\nTables created:")
    print("  - Users")
    print("  - ValidationHistory")
    print("  - APIKeyAuditLog")
    print("  - UserValidationSummary (view)")
    
except FileNotFoundError:
    print("❌ Error: database_schema.sql not found")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
