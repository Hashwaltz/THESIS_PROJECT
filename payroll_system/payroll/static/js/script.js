// Payroll System JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Date picker initialization
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        // Set max date to today for certain fields
        if (input.name === 'pay_date' || input.name === 'start_date' || input.name === 'end_date') {
            input.max = new Date().toISOString().split('T')[0];
        }
    });

    // Currency formatting
    var currencyInputs = document.querySelectorAll('input[type="number"][data-currency]');
    currencyInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });

    // Payroll calculation
    var basicSalaryInput = document.querySelector('input[name="basic_salary"]');
    var overtimeHoursInput = document.querySelector('input[name="overtime_hours"]');
    var grossPayInput = document.querySelector('input[name="gross_pay"]');
    var netPayInput = document.querySelector('input[name="net_pay"]');

    if (basicSalaryInput && overtimeHoursInput) {
        function calculatePayroll() {
            var basicSalary = parseFloat(basicSalaryInput.value) || 0;
            var overtimeHours = parseFloat(overtimeHoursInput.value) || 0;
            
            // Calculate overtime pay (25% premium)
            var hourlyRate = basicSalary / 8 / 22; // Assuming 8 hours per day, 22 working days
            var overtimePay = overtimeHours * hourlyRate * 1.25;
            
            // Calculate gross pay
            var grossPay = basicSalary + overtimePay;
            
            // Calculate deductions (simplified)
            var sss = calculateSSS(basicSalary);
            var philhealth = basicSalary * 0.03;
            var pagibig = basicSalary * 0.02;
            var tax = calculateTax(grossPay);
            
            var totalDeductions = sss + philhealth + pagibig + tax;
            var netPay = grossPay - totalDeductions;
            
            if (grossPayInput) grossPayInput.value = grossPay.toFixed(2);
            if (netPayInput) netPayInput.value = netPay.toFixed(2);
            
            // Update display
            updatePayrollDisplay({
                basicSalary: basicSalary,
                overtimePay: overtimePay,
                grossPay: grossPay,
                sss: sss,
                philhealth: philhealth,
                pagibig: pagibig,
                tax: tax,
                totalDeductions: totalDeductions,
                netPay: netPay
            });
        }

        basicSalaryInput.addEventListener('input', calculatePayroll);
        overtimeHoursInput.addEventListener('input', calculatePayroll);
    }

    // SSS calculation
    function calculateSSS(basicSalary) {
        if (basicSalary <= 1000) return 50.00;
        else if (basicSalary <= 2000) return 100.00;
        else if (basicSalary <= 3000) return 150.00;
        else if (basicSalary <= 4000) return 200.00;
        else if (basicSalary <= 5000) return 250.00;
        else if (basicSalary <= 6000) return 300.00;
        else if (basicSalary <= 7000) return 350.00;
        else if (basicSalary <= 8000) return 400.00;
        else if (basicSalary <= 9000) return 450.00;
        else if (basicSalary <= 10000) return 500.00;
        else return 500.00;
    }

    // Tax calculation (simplified)
    function calculateTax(grossPay) {
        if (grossPay <= 250000) return 0;
        else if (grossPay <= 400000) return (grossPay - 250000) * 0.20;
        else if (grossPay <= 800000) return 30000 + (grossPay - 400000) * 0.25;
        else if (grossPay <= 2000000) return 130000 + (grossPay - 800000) * 0.30;
        else if (grossPay <= 8000000) return 490000 + (grossPay - 2000000) * 0.32;
        else return 2410000 + (grossPay - 8000000) * 0.35;
    }

    // Update payroll display
    function updatePayrollDisplay(data) {
        var display = document.querySelector('.payroll-display');
        if (display) {
            display.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>Earnings</h6>
                        <p>Basic Salary: ₱${data.basicSalary.toFixed(2)}</p>
                        <p>Overtime Pay: ₱${data.overtimePay.toFixed(2)}</p>
                        <p><strong>Gross Pay: ₱${data.grossPay.toFixed(2)}</strong></p>
                    </div>
                    <div class="col-md-6">
                        <h6>Deductions</h6>
                        <p>SSS: ₱${data.sss.toFixed(2)}</p>
                        <p>PhilHealth: ₱${data.philhealth.toFixed(2)}</p>
                        <p>Pag-IBIG: ₱${data.pagibig.toFixed(2)}</p>
                        <p>Tax: ₱${data.tax.toFixed(2)}</p>
                        <p><strong>Total Deductions: ₱${data.totalDeductions.toFixed(2)}</strong></p>
                        <p><strong>Net Pay: ₱${data.netPay.toFixed(2)}</strong></p>
                    </div>
                </div>
            `;
        }
    }

    // Search functionality
    var searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            var searchTerm = this.value.toLowerCase();
            var table = this.closest('.card').querySelector('table');
            
            if (table) {
                var rows = table.querySelectorAll('tbody tr');
                rows.forEach(function(row) {
                    var text = row.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            }
        });
    });

    // Filter change handlers
    var filterSelects = document.querySelectorAll('select[name="period"], select[name="employee"], select[name="status"]');
    filterSelects.forEach(function(select) {
        select.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });

    // Export functionality
    var exportButtons = document.querySelectorAll('.btn-export');
    exportButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var format = this.dataset.format || 'csv';
            var table = this.closest('.card').querySelector('table');
            
            if (table) {
                exportTable(table, format);
            }
        });
    });

    // Print functionality
    var printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            window.print();
        });
    });

    // Sync employees button
    var syncButton = document.querySelector('.btn-sync');
    if (syncButton) {
        syncButton.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('This will sync all employees from the HR system. Continue?')) {
                showLoading(this);
                this.closest('form').submit();
            }
        });
    }

    // Process payroll button
    var processButton = document.querySelector('.btn-process');
    if (processButton) {
        processButton.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('This will process payroll for all employees. Continue?')) {
                showLoading(this);
                this.closest('form').submit();
            }
        });
    }
});

// Export table to CSV
function exportTable(table, format) {
    var csv = [];
    var rows = table.querySelectorAll('tr');
    
    for (var i = 0; i < rows.length; i++) {
        var row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (var j = 0; j < cols.length; j++) {
            var text = cols[j].innerText.replace(/"/g, '""');
            row.push('"' + text + '"');
        }
        
        csv.push(row.join(','));
    }
    
    var csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    var downloadLink = document.createElement('a');
    downloadLink.download = 'payroll_export.csv';
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Show loading spinner
function showLoading(element) {
    var spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.id = 'loading-spinner';
    element.appendChild(spinner);
}

// Hide loading spinner
function hideLoading() {
    var spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Show success message
function showSuccess(message) {
    showAlert(message, 'success');
}

// Show error message
function showError(message) {
    showAlert(message, 'danger');
}

// Show alert message
function showAlert(message, type) {
    var alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-' + type + ' alert-dismissible fade show';
    alertDiv.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    
    var container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-PH', {
        style: 'currency',
        currency: 'PHP'
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString('en-PH', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// AJAX helper function
function makeRequest(url, method, data, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                if (callback) callback(null, response);
            } else {
                if (callback) callback(new Error('Request failed'), null);
            }
        }
    };
    
    if (data) {
        xhr.send(JSON.stringify(data));
    } else {
        xhr.send();
    }
}

// Generate payslip number
function generatePayslipNumber(employeeId, periodStart) {
    var date = new Date(periodStart);
    var year = date.getFullYear();
    var month = (date.getMonth() + 1).toString().padStart(2, '0');
    return 'PS' + year + month + employeeId.toString().padStart(4, '0');
}


