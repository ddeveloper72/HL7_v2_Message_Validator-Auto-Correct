"""
Apply schema update to add ReportDetails column to ValidationHistory table
"""
from db_utils import DatabaseManager
import os
from dotenv import load_dotenv

load_dotenv()

def apply_schema_update():
    """Add ReportDetails column to ValidationHistory table"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("Connected to Azure SQL Database")
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'ValidationHistory' 
            AND COLUMN_NAME = 'ReportDetails'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✅ ReportDetails column already exists")
            cursor.close()
            conn.close()
            return True
        
        print("Adding ReportDetails column...")
        cursor.execute("ALTER TABLE ValidationHistory ADD ReportDetails NVARCHAR(MAX)")
        conn.commit()
        print("✅ Column added successfully")
        
        print("Creating index...")
        cursor.execute("""
            CREATE INDEX IX_ValidationHistory_Details 
            ON ValidationHistory(ValidationID) 
            INCLUDE (ReportDetails)
        """)
        conn.commit()
        print("✅ Index created successfully")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Schema update completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error applying schema update: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    apply_schema_update()
