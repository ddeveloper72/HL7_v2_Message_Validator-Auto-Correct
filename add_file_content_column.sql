-- Add OriginalFileContent column to existing ValidationHistory table
-- Run this on Azure SQL Database to add file storage capability

USE [gazelle-healthlink];
GO

-- Check if column already exists
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('ValidationHistory') 
    AND name = 'OriginalFileContent'
)
BEGIN
    ALTER TABLE ValidationHistory
    ADD OriginalFileContent VARBINARY(MAX) NULL;
    
    PRINT 'OriginalFileContent column added successfully';
END
ELSE
BEGIN
    PRINT 'OriginalFileContent column already exists';
END
GO
