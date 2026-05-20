"""
Apply database schema update to add file content storage
"""
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def apply_schema_update():
    """Add OriginalFileContent column to ValidationHistory table"""
    
    # Build connection string
    connection_string = (
        f"DRIVER={{{os.getenv('DB_DRIVER')}}};"
        f"SERVER={os.getenv('AZURE_SQL_SERVER')};"
        f"DATABASE={os.getenv('AZURE_SQL_DATABASE')};"
        f"UID={os.getenv('AZURE_SQL_USERNAME')};"
        f"PWD={os.getenv('AZURE_SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM sys.columns 
            WHERE object_id = OBJECT_ID('ValidationHistory') 
            AND name = 'OriginalFileContent'
        """)
        
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            print("Adding OriginalFileContent column to ValidationHistory table...")
            cursor.execute("""
                ALTER TABLE ValidationHistory
                ADD OriginalFileContent VARBINARY(MAX) NULL
            """)
            conn.commit()
            print("✅ OriginalFileContent column added successfully!")
        else:
            print("ℹ️  OriginalFileContent column already exists")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    apply_schema_update()
