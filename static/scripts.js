// Gazelle HL7 v2 Validator - Custom JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Get DOM elements
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const validateBtn = document.getElementById('validateBtn');
    const validateSampleBtn = document.getElementById('validateSampleBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultsContainer = document.getElementById('resultsContainer');
    const errorContainer = document.getElementById('errorContainer');
    const closeResults = document.getElementById('closeResults');

    // File upload validation handler
    uploadForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file');
            return;
        }

        if (!file.name.toLowerCase().endsWith('.xml')) {
            showError('Please select an XML file');
            return;
        }

        await validateFile(file);
    });

    // Sample file validation handler
    validateSampleBtn.addEventListener('click', async function () {
        await validateSample();
    });

    // Close results handler
    closeResults.addEventListener('click', function () {
        hideResults();
    });

    // Copy URL button handler
    document.getElementById('copyUrlBtn').addEventListener('click', function () {
        const reportUrl = document.getElementById('reportUrl');
        reportUrl.select();
        document.execCommand('copy');

        // Change button text temporarily
        const btn = this;
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check"></i> Copied!';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
        }, 2000);
    });

    /**
     * Validate uploaded file with auto-correction
     */
    async function validateFile(file) {
        showLoading();
        hideError();
        hideResults();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/auto-validate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                showError(data.error || 'Validation failed');
                // Still show corrections if any were applied
                if (data.corrections_applied) {
                    displayCorrectionsOnly(data);
                }
            }
        } catch (error) {
            showError('Network error: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    /**
     * Validate sample file
     */
    async function validateSample() {
        showLoading();
        hideError();
        hideResults();

        try {
            const response = await fetch('/validate-sample', {
                method: 'POST'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                displayResults(data);
            } else {
                showError(data.error || 'Validation failed');
            }
        } catch (error) {
            showError('Network error: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    /**
     * Display validation results with corrections
     */
    function displayResults(data) {
        // Set filename
        document.getElementById('fileName').textContent = data.filename || 'Unknown';

        // Set validation status
        const statusElement = document.getElementById('validationStatus');
        const isPassed = data.validation_passed || data.validation_status === 'PASSED';
        const status = data.validation_status || 'Unknown';

        let statusHTML = '';
        
        if (isPassed) {
            statusHTML = `
                <div class="alert alert-success">
                    <h5><i class="bi bi-check-circle"></i> Validation PASSED</h5>
                    <p class="mb-0">Message Type: <strong>${data.message_type || 'Unknown'}</strong></p>
                </div>
            `;
        } else {
            statusHTML = `
                <div class="alert alert-danger">
                    <h5><i class="bi bi-x-circle"></i> Validation FAILED</h5>
                    <p class="mb-0">Message Type: <strong>${data.message_type || 'Unknown'}</strong></p>
                    <p class="mb-0">Status: <strong>${status}</strong></p>
                </div>
            `;
            
            // Show errors if any
            if (data.errors && data.errors.length > 0) {
                statusHTML += '<div class="alert alert-warning mt-2"><h6>Errors Found:</h6><ul class="mb-0">';
                data.errors.forEach(error => {
                    statusHTML += `<li>${error}</li>`;
                });
                statusHTML += '</ul></div>';
            }
        }

        statusElement.innerHTML = statusHTML;

        // Show corrections if any were applied
        if (data.corrections_applied && data.corrections_applied.total_corrections > 0) {
            const correctionsHTML = buildCorrectionsDisplay(data.corrections_applied, data.correction_report);
            statusElement.innerHTML += correctionsHTML;
        }

        // Set report URL if available
        if (data.report_url) {
            document.getElementById('reportUrlSection').style.display = 'block';
            document.getElementById('reportUrl').value = data.report_url;
            document.getElementById('openReportBtn').href = data.report_url;
        } else {
            document.getElementById('reportUrlSection').style.display = 'none';
        }

        // Set validation report
        let reportText = '';
        if (data.correction_report) {
            reportText = data.correction_report;
        } else if (data.report) {
            reportText = data.report;
        } else {
            reportText = 'View full report on Gazelle EVS using the link above.';
        }
        
        document.getElementById('validationReport').textContent = reportText;

        // Set raw response
        document.getElementById('rawResponseContent').textContent =
            JSON.stringify(data, null, 2);

        // Show results with animation
        resultsContainer.style.display = 'block';
        resultsContainer.classList.add('fade-in');

        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Build HTML for corrections display
     */
    function buildCorrectionsDisplay(corrections, report) {
        const total = corrections.total_corrections;
        const critical = corrections.critical_fixes || 0;
        const codeFixes = corrections.code_fixes || 0;
        const fieldInsertions = corrections.field_insertions || 0;

        let html = `
            <div class="alert alert-info mt-3">
                <h6><i class="bi bi-tools"></i> Auto-Corrections Applied: ${total}</h6>
                <ul class="mb-0">
        `;

        if (critical > 0) {
            html += `<li><strong>Critical Fixes:</strong> ${critical} (BOM removal, XML declaration)</li>`;
        }
        if (codeFixes > 0) {
            html += `<li><strong>Code Corrections:</strong> ${codeFixes} (Invalid HL7 codes fixed)</li>`;
        }
        if (fieldInsertions > 0) {
            html += `<li><strong>Field Insertions:</strong> ${fieldInsertions} (Missing required fields added)</li>`;
        }

        html += `
                </ul>
                <small class="text-muted mt-2 d-block">See detailed report below for specifics.</small>
            </div>
        `;

        return html;
    }

    /**
     * Display corrections even when validation fails
     */
    function displayCorrectionsOnly(data) {
        if (data.corrections_applied && data.corrections_applied.total_corrections > 0) {
            const correctionsHTML = buildCorrectionsDisplay(data.corrections_applied, data.correction_report);
            
            const tempDiv = document.createElement('div');
            tempDiv.className = 'alert alert-warning mt-3';
            tempDiv.innerHTML = correctionsHTML;
            
            errorContainer.appendChild(tempDiv);
        }
    }

    /**
     * Show loading spinner
     */
    function showLoading() {
        loadingSpinner.style.display = 'block';
        validateBtn.disabled = true;
        validateSampleBtn.disabled = true;
    }

    /**
     * Hide loading spinner
     */
    function hideLoading() {
        loadingSpinner.style.display = 'none';
        validateBtn.disabled = false;
        validateSampleBtn.disabled = false;
    }

    /**
     * Show error message
     */
    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        errorContainer.style.display = 'block';
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Hide error message
     */
    function hideError() {
        errorContainer.style.display = 'none';
    }

    /**
     * Hide results
     */
    function hideResults() {
        resultsContainer.style.display = 'none';
        resultsContainer.classList.remove('fade-in');
    }
});
