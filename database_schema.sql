-- Gazelle HL7 Validator Database Schema
-- Minimal storage approach: Store user profiles and validation metadata only

-- Users table
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Email NVARCHAR(255) NOT NULL UNIQUE,
    AzureADObjectID NVARCHAR(255) UNIQUE,
    DisplayName NVARCHAR(255),
    EncryptedAPIKey NVARCHAR(MAX),  -- Encrypted Gazelle API key
    CreatedDate DATETIME2 DEFAULT GETUTCDATE(),
    LastLoginDate DATETIME2,
    IsActive BIT DEFAULT 1,
    INDEX IX_Users_Email (Email),
    INDEX IX_Users_AzureAD (AzureADObjectID)
);

-- Validation History table
CREATE TABLE ValidationHistory (
    ValidationID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    Filename NVARCHAR(255) NOT NULL,
    MessageType NVARCHAR(50),  -- SIU_S12, ORU_R01, etc.
    Status NVARCHAR(20),  -- PASSED, FAILED, UNDEFINED
    ReportURL NVARCHAR(1000),  -- Persistent Gazelle report link
    ErrorCount INT DEFAULT 0,
    WarningCount INT DEFAULT 0,
    CorrectionsApplied INT DEFAULT 0,
    ValidationTimestamp DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    INDEX IX_ValidationHistory_User (UserID),
    INDEX IX_ValidationHistory_Timestamp (ValidationTimestamp DESC),
    INDEX IX_ValidationHistory_Status (Status)
);

-- Optional: User API Key audit log (track when keys are updated)
CREATE TABLE APIKeyAuditLog (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    Action NVARCHAR(50),  -- 'SET', 'UPDATE', 'DELETE'
    ActionTimestamp DATETIME2 DEFAULT GETUTCDATE(),
    IPAddress NVARCHAR(50),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    INDEX IX_APIKeyAudit_User (UserID)
);

-- Create a view for user validation summary
GO
CREATE VIEW UserValidationSummary AS
SELECT 
    u.UserID,
    u.Email,
    u.DisplayName,
    COUNT(vh.ValidationID) AS TotalValidations,
    SUM(CASE WHEN vh.Status = 'PASSED' THEN 1 ELSE 0 END) AS PassedCount,
    SUM(CASE WHEN vh.Status = 'FAILED' THEN 1 ELSE 0 END) AS FailedCount,
    SUM(CASE WHEN vh.Status = 'UNDEFINED' THEN 1 ELSE 0 END) AS UndefinedCount,
    MAX(vh.ValidationTimestamp) AS LastValidationDate
FROM Users u
LEFT JOIN ValidationHistory vh ON u.UserID = vh.UserID
GROUP BY u.UserID, u.Email, u.DisplayName;
GO
