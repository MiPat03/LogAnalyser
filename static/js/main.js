/**
 * Main JavaScript for Log Analyzer
 */

/**
 * Handle loading state for buttons
 * @param {HTMLElement} button - The button to show loading state
 * @param {boolean} isLoading - Whether to show loading or reset
 * @param {string} originalText - The original button text (only needed when resetting)
 */
function toggleButtonLoading(button, isLoading, originalText) {
    if (isLoading) {
        // Store original text
        button.dataset.originalText = button.innerHTML;
        // Replace with spinner
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Loading...';
        button.disabled = true;
        button.classList.add('disabled');
    } else {
        // Restore original text
        button.innerHTML = originalText || button.dataset.originalText;
        button.disabled = false;
        button.classList.remove('disabled');
    }
}

// Function to show logs tab and set file filter
function showLogsTab(fileName) {
    // Switch to logs tab
    const logsTab = document.getElementById('logs-tab');
    if (logsTab) {
        const tabTrigger = new bootstrap.Tab(logsTab);
        tabTrigger.show();
        
        // Set the file name in the filter
        const fileSelect = document.getElementById('file_name');
        if (fileSelect && fileName) {
            fileSelect.value = fileName;
            
            // Trigger the filter form submission
            const filterForm = document.getElementById('logsFilterForm');
            if (filterForm) {
                setTimeout(() => {
                    filterForm.dispatchEvent(new Event('submit'));
                }, 100);
            }
        }
    }
}

// Function to confirm file deletion
function confirmDelete(fileName) {
    if (confirm(`Are you sure you want to delete the file ${fileName}? This action cannot be undone.`)) {
        window.location.href = `/delete_file/${encodeURIComponent(fileName)}`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File upload validation
    const fileInput = document.getElementById('logfile');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const filePath = fileInput.value;
            const allowedExtensions = /(\.log|\.txt)$/i;
            
            if (!allowedExtensions.exec(filePath)) {
                alert('Please upload file having extensions .log or .txt only.');
                fileInput.value = '';
                return false;
            }
            
            // File size validation (max 300MB)
            const fileSize = this.files[0].size / 1024 / 1024; // in MB
            if (fileSize > 300) {
                alert('File size exceeds 300 MB. Please choose a smaller file.');
                fileInput.value = '';
                return false;
            }
        });
    }
    
    // Add loading state to upload form
    const uploadForm = document.querySelector('form[action*="upload_file"]');
    if (uploadForm) {
        const submitButton = uploadForm.querySelector('button[type="submit"]');
        
        uploadForm.addEventListener('submit', function(e) {
            const fileInput = document.getElementById('logfile');
            if (fileInput && fileInput.files.length > 0) {
                toggleButtonLoading(submitButton, true);
            }
        });
    }

    // Dynamic table filtering
    const searchInput = document.getElementById('tableSearch');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const searchTerm = searchInput.value.toLowerCase();
            const tableRows = document.querySelectorAll('table tbody tr');
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // Auto-close alerts after 5 seconds (except on permanent alerts)
    // Only apply to flash messages, not our info alerts
    const flashAlerts = document.querySelectorAll('.flash-alert:not(.alert-permanent)');
    flashAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Handle logs filter form submission via AJAX
    const logsFilterForm = document.getElementById('logsFilterForm');
    if (logsFilterForm) {
        const filterButton = logsFilterForm.querySelector('button[type="submit"]');
        
        logsFilterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show loading state
            if (filterButton) {
                toggleButtonLoading(filterButton, true);
            }
            
            // Get form data
            const formData = new FormData(logsFilterForm);
            const params = new URLSearchParams();
            
            // Add non-empty parameters
            for (const [key, value] of formData.entries()) {
                if (value !== '') {
                    params.append(key, value);
                }
            }
            
            // Show loading indicator in the logs table container
            const logsTableContainer = document.getElementById('logsTableContainer');
            if (logsTableContainer) {
                logsTableContainer.innerHTML = `
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-3">Loading logs...</p>
                    </div>
                `;
            }
            
            // Fetch logs via AJAX
            fetch(`/api/logs?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    // Reset button state
                    if (filterButton) {
                        toggleButtonLoading(filterButton, false);
                    }
                    
                    // Render logs table
                    if (logsTableContainer) {
                        if (data.logs && data.logs.length > 0) {
                            let tableHtml = `
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>IP</th>
                                            <th>Timestamp</th>
                                            <th>Method</th>
                                            <th>API</th>
                                            <th>Status</th>
                                            <th>Bytes</th>
                                            <th>Response Time</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                            `;
                            
                            data.logs.forEach(log => {
                                // Determine status code class
                                let statusClass = '';
                                if (log.status_code < 300) {
                                    statusClass = 'bg-success text-white';
                                } else if (log.status_code < 400) {
                                    statusClass = 'bg-info text-white';
                                } else if (log.status_code < 500) {
                                    statusClass = 'bg-warning';
                                } else {
                                    statusClass = 'bg-danger text-white';
                                }
                                
                                tableHtml += `
                                    <tr>
                                        <td>${log.ip}</td>
                                        <td>${log.timestamp}</td>
                                        <td>${log.request_type}</td>
                                        <td>${log.api}</td>
                                        <td><span class="badge ${statusClass}">${log.status_code}</span></td>
                                        <td>${log.bytes}</td>
                                        <td>${log.response_time}s</td>
                                    </tr>
                                `;
                            });
                            
                            tableHtml += `
                                    </tbody>
                                </table>
                                <div class="mt-3">
                                    <p>Showing ${data.logs.length} of ${data.total_count} logs</p>
                                </div>
                            `;
                            
                            logsTableContainer.innerHTML = tableHtml;
                        } else {
                            logsTableContainer.innerHTML = `
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle"></i> No logs found matching your criteria.
                                </div>
                            `;
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching logs:', error);
                    if (filterButton) {
                        toggleButtonLoading(filterButton, false);
                    }
                    
                    if (logsTableContainer) {
                        logsTableContainer.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle"></i> Error loading logs. Please try again.
                            </div>
                        `;
                    }
                });
        });
    }

    // Real-time log filtering (for client-side filtering)
    const filterInputs = document.querySelectorAll('.filter-control');
    filterInputs.forEach(input => {
        input.addEventListener('input', function() {
            applyFilters();
        });
    });

    function applyFilters() {
        const filters = {};
        document.querySelectorAll('.filter-control').forEach(input => {
            filters[input.dataset.field] = input.value.toLowerCase();
        });

        const tableRows = document.querySelectorAll('table tbody tr');
        tableRows.forEach(row => {
            let showRow = true;

            for (const field in filters) {
                if (filters[field]) {
                    const cellValue = row.querySelector(`td[data-field="${field}"]`).textContent.toLowerCase();
                    if (!cellValue.includes(filters[field])) {
                        showRow = false;
                        break;
                    }
                }
            }

            row.style.display = showRow ? '' : 'none';
        });
    }

    // Handle modal data loading
    const logModals = document.querySelectorAll('[data-bs-toggle="modal"]');
    logModals.forEach(button => {
        button.addEventListener('click', function() {
            const logId = this.dataset.logId;
            if (logId) {
                // If we implement dynamic loading of log details via AJAX
                // This would be the place to load that data
                console.log(`Loading details for log ID: ${logId}`);
            }
        });
    });

    // Responsive table handling
    function adjustTableResponsiveness() {
        const tables = document.querySelectorAll('.table-responsive-dynamic');
        const windowWidth = window.innerWidth;
        
        tables.forEach(table => {
            if (windowWidth < 768) {
                table.classList.add('table-responsive');
            } else {
                table.classList.remove('table-responsive');
            }
        });
    }

    // Call once on load
    adjustTableResponsiveness();
    
    // Call on window resize
    window.addEventListener('resize', adjustTableResponsiveness);
    
    // Add loading state to export buttons on analytics page
    const exportButtons = document.querySelectorAll('#exportCSV, #saveCharts');
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            toggleButtonLoading(this, true);
            // Reset after 3 seconds if the download starts
            setTimeout(() => {
                toggleButtonLoading(this, false);
            }, 3000);
        });
    });
    
    // Add loading state to pagination links
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Don't add loading to disabled links
            if (!this.parentElement.classList.contains('disabled') && !this.parentElement.classList.contains('active')) {
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            }
        });
    });
    
    // Initialize charts when analytics tab is shown
    const analyticsTab = document.getElementById('analytics-tab');
    if (analyticsTab) {
        analyticsTab.addEventListener('shown.bs.tab', function(e) {
            // Trigger resize event to make charts render properly
            window.dispatchEvent(new Event('resize'));
        });
    }
    
    // Load logs on initial page load if file_name is in URL params
    const urlParams = new URLSearchParams(window.location.search);
    const fileNameParam = urlParams.get('file_name');
    if (fileNameParam && document.getElementById('logsFilterForm')) {
        showLogsTab(fileNameParam);
    }
});