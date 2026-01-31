"""
Database utility module for Azure SQL Database integration
Handles user profiles and validation history storage
"""
import os
import pyodbc
from cryptography.fernet import Fernet
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    """Manages Azure SQL Database connections and operations"""
    
    def __init__(self):
        self.server = os.getenv('AZURE_SQL_SERVER')
        self.database = os.getenv('AZURE_SQL_DATABASE')
        self.username = os.getenv('AZURE_SQL_USERNAME')
        self.password = os.getenv('AZURE_SQL_PASSWORD')
        # Use FreeTDS driver on Heroku, ODBC Driver 18 locally
        self.driver = os.getenv('DB_DRIVER', 'FreeTDS' if os.getenv('DYNO') else 'ODBC Driver 18 for SQL Server')
        
        # Encryption key for API keys (generate once and store securely)
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            # Generate a key if not exists (store this in production!)
            encryption_key = Fernet.generate_key().decode()
            print(f"⚠️  WARNING: Generated new encryption key. Add to .env:")
            print(f"ENCRYPTION_KEY={encryption_key}")
        
        self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    
    def get_connection(self):
        """Create and return a database connection"""
        if self.driver == 'FreeTDS':
            # FreeTDS connection for Heroku - use direct driver path
            connection_string = (
                f'DRIVER=/app/.apt/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so;'
                f'SERVER={self.server};'
                f'PORT=1433;'
                f'DATABASE={self.database};'
                f'UID={self.username};'
                f'PWD={self.password};'
                f'TDS_Version=8.0;'
            )
        else:
            # Microsoft ODBC Driver for local development
            connection_string = (
                f'DRIVER={{{self.driver}}};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                f'UID={self.username};'
                f'PWD={self.password};'
                f'Encrypt=yes;'
                f'TrustServerCertificate=no;'
                f'Connection Timeout=30;'
            )
        return pyodbc.connect(connection_string)
    
    def encrypt_api_key(self, api_key):
        """Encrypt Gazelle API key"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key):
        """Decrypt Gazelle API key"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    # ==================== USER OPERATIONS ====================
    
    def create_or_update_user(self, email, azure_ad_oid=None, display_name=None):
        """Create or update user profile"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user exists
            cursor.execute("SELECT UserID FROM Users WHERE Email = ?", email)
            user = cursor.fetchone()
            
            if user:
                # Update existing user
                cursor.execute("""
                    UPDATE Users 
                    SET AzureADObjectID = ?, DisplayName = ?, LastLoginDate = GETUTCDATE()
                    WHERE Email = ?
                """, (azure_ad_oid, display_name, email))
                user_id = user[0]
            else:
                # Create new user
                cursor.execute("""
                    INSERT INTO Users (Email, AzureADObjectID, DisplayName, LastLoginDate)
                    OUTPUT INSERTED.UserID
                    VALUES (?, ?, ?, GETUTCDATE())
                """, (email, azure_ad_oid, display_name))
                user_id = cursor.fetchone()[0]
            
            conn.commit()
            return user_id
        finally:
            cursor.close()
            conn.close()
    
    def get_user_by_email(self, email):
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT UserID, Email, AzureADObjectID, DisplayName, EncryptedAPIKey, CreatedDate
                FROM Users WHERE Email = ? AND IsActive = 1
            """, email)
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT UserID, Email, AzureADObjectID, DisplayName, EncryptedAPIKey, CreatedDate
                FROM Users WHERE UserID = ? AND IsActive = 1
            """, user_id)
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    
    def set_user_api_key(self, user_id, api_key, ip_address=None):
        """Set or update user's Gazelle API key (encrypted)"""
        encrypted_key = self.encrypt_api_key(api_key)
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Update user's API key
            cursor.execute("""
                UPDATE Users SET EncryptedAPIKey = ? WHERE UserID = ?
            """, (encrypted_key, user_id))
            
            # Log the action
            cursor.execute("""
                INSERT INTO APIKeyAuditLog (UserID, Action, IPAddress)
                VALUES (?, ?, ?)
            """, (user_id, 'SET', ip_address))
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    
    def get_user_api_key(self, user_id):
        """Get user's decrypted Gazelle API key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT EncryptedAPIKey FROM Users WHERE UserID = ?", user_id)
            result = cursor.fetchone()
            if result and result[0]:
                return self.decrypt_api_key(result[0])
            return None
        finally:
            cursor.close()
            conn.close()
    
    # ==================== VALIDATION HISTORY ====================
    
    def save_validation_result(self, user_id, filename, message_type, status, 
                               report_url, error_count=0, warning_count=0, corrections_applied=0):
        """Save validation result to history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO ValidationHistory 
                (UserID, Filename, MessageType, Status, ReportURL, ErrorCount, WarningCount, CorrectionsApplied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, filename, message_type, status, report_url, error_count, warning_count, corrections_applied))
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    
    def get_user_validation_history(self, user_id, limit=50):
        """Get user's validation history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT TOP (?) 
                    ValidationID, Filename, MessageType, Status, ReportURL, 
                    ErrorCount, WarningCount, CorrectionsApplied, ValidationTimestamp
                FROM ValidationHistory
                WHERE UserID = ?
                ORDER BY ValidationTimestamp DESC
            """, (limit, user_id))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'filename': row[1],
                    'message_type': row[2],
                    'status': row[3],
                    'report_url': row[4],
                    'error_count': row[5],
                    'warning_count': row[6],
                    'corrections_applied': row[7],
                    'timestamp': row[8]
                })
            return results
        finally:
            cursor.close()
            conn.close()
    
    def get_user_statistics(self, user_id):
        """Get user validation statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN Status = 'PASSED' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN Status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN Status = 'UNDEFINED' THEN 1 ELSE 0 END) as undefined
                FROM ValidationHistory
                WHERE UserID = ?
            """, user_id)
            
            row = cursor.fetchone()
            return {
                'total': row[0] or 0,
                'passed': row[1] or 0,
                'failed': row[2] or 0,
                'undefined': row[3] or 0
            }
        finally:
            cursor.close()
            conn.close()
