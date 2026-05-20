-- Add API Key Validity Date Columns to Users Table
-- Migration Script for per-user API key expiration tracking

-- Add columns for API key validity dates
ALTER TABLE Users
ADD APIKeyValidFrom DATE NULL,
    APIKeyValidTo DATE NULL;

-- Add index for quick expiration lookups
CREATE INDEX IX_Users_APIKeyValidTo ON Users(APIKeyValidTo);

-- Optional: Add a computed column to check if key is expired
-- This is useful for quick filtering, but we'll handle logic in Python
-- ALTER TABLE Users
-- ADD IsAPIKeyExpired AS (CASE WHEN APIKeyValidTo < CAST(GETUTCDATE() AS DATE) THEN 1 ELSE 0 END);

GO

-- Update the UserValidationSummary view to include API key validity
DROP VIEW IF EXISTS UserValidationSummary;
GO

CREATE VIEW UserValidationSummary AS
SELECT 
    u.UserID,
    u.Email,
    u.DisplayName,
    u.APIKeyValidFrom,
    u.APIKeyValidTo,
    CASE 
        WHEN u.APIKeyValidTo IS NULL THEN 'NOT_CONFIGURED'
        WHEN u.APIKeyValidTo < CAST(GETUTCDATE() AS DATE) THEN 'EXPIRED'
        WHEN u.APIKeyValidTo = CAST(GETUTCDATE() AS DATE) THEN 'EXPIRING_TODAY'
        WHEN DATEDIFF(day, CAST(GETUTCDATE() AS DATE), u.APIKeyValidTo) <= 7 THEN 'EXPIRING_SOON'
        ELSE 'VALID'
    END AS APIKeyStatus,
    DATEDIFF(day, CAST(GETUTCDATE() AS DATE), u.APIKeyValidTo) AS DaysUntilExpiration,
    COUNT(vh.ValidationID) AS TotalValidations,
    SUM(CASE WHEN vh.Status = 'PASSED' THEN 1 ELSE 0 END) AS PassedCount,
    SUM(CASE WHEN vh.Status = 'FAILED' THEN 1 ELSE 0 END) AS FailedCount,
    SUM(CASE WHEN vh.Status = 'UNDEFINED' THEN 1 ELSE 0 END) AS UndefinedCount,
    MAX(vh.ValidationTimestamp) AS LastValidationDate
FROM Users u
LEFT JOIN ValidationHistory vh ON u.UserID = vh.UserID
GROUP BY u.UserID, u.Email, u.DisplayName, u.APIKeyValidFrom, u.APIKeyValidTo;
GO

-- Verification queries
SELECT 'Users table structure after migration:' AS Info;
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Users'
ORDER BY ORDINAL_POSITION;

SELECT 'Sample user data:' AS Info;
SELECT TOP 5 UserID, Email, DisplayName, APIKeyValidFrom, APIKeyValidTo
FROM Users;
