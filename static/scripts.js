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
     * Validate uploaded file
     */
    async function validateFile(file) {
        showLoading();
        hideError();
        hideResults();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/validate', {
                method: 'POST',
                body: formData
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
     * Display validation results
     */
    function displayResults(data) {
        // Set filename
        document.getElementById('fileName').textContent = data.filename || 'Unknown';

        // Set validation status
        const statusElement = document.getElementById('validationStatus');
        const status = data.validation_status || 'Unknown';

        let statusClass = 'status-warning';
        let statusIcon = 'bi-question-circle';

        if (status.toLowerCase().includes('success') || status.toLowerCase().includes('passed')) {
            statusClass = 'status-success';
            statusIcon = 'bi-check-circle';
        } else if (status.toLowerCase().includes('error') || status.toLowerCase().includes('failed')) {
            statusClass = 'status-error';
            statusIcon = 'bi-x-circle';
        }

        statusElement.innerHTML = `
            <label class="form-label fw-bold">Validation Status:</label>
            <div>
                <span class="${statusClass}">
                    <i class="bi ${statusIcon}"></i>
                    ${status}
                </span>
            </div>
        `;

        // Set report URL if available
        if (data.report_url) {
            document.getElementById('reportUrlSection').style.display = 'block';
            document.getElementById('reportUrl').value = data.report_url;
            document.getElementById('openReportBtn').href = data.report_url;
        } else {
            document.getElementById('reportUrlSection').style.display = 'none';
        }

        // Set validation report
        document.getElementById('validationReport').textContent =
            data.report || 'No detailed report available';

        // Set raw response
        document.getElementById('rawResponseContent').textContent =
            JSON.stringify(data.initial_response || data, null, 2);

        // Show results with animation
        resultsContainer.style.display = 'block';
        resultsContainer.classList.add('fade-in');

        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
