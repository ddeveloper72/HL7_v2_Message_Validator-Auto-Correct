-- Add column to store detailed validation report
-- This will store the full markdown report content including all errors and warnings

ALTER TABLE ValidationHistory
ADD ReportDetails NVARCHAR(MAX);

-- Add index for better query performance
CREATE INDEX IX_ValidationHistory_Details ON ValidationHistory(ValidationID) INCLUDE (ReportDetails);
