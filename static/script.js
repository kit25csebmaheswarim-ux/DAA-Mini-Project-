// script.js - Resource Allocation System JavaScript

// -------------------------------------------------------
// TAB SWITCHING (Admin Panel)
// -------------------------------------------------------
function showTab(tabId, clickedBtn) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    // Remove active from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    // Show the selected tab
    const target = document.getElementById(tabId);
    if (target) target.classList.add('active');
    // Activate the clicked button
    if (clickedBtn) clickedBtn.classList.add('active');
}

// -------------------------------------------------------
// AVAILABILITY CHECKER
// Calls /api/check-availability and displays the result
// -------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {

    const checkBtn = document.getElementById('checkAvailBtn');
    const resultDiv = document.getElementById('availability-result');

    if (checkBtn) {
        checkBtn.addEventListener('click', function () {
            const resourceId = document.getElementById('resource_id').value;
            const date       = document.getElementById('date').value;
            const startTime  = document.getElementById('start_time').value;
            const endTime    = document.getElementById('end_time').value;

            // --- Basic validation before calling the API ---
            if (!resourceId) {
                showResult('Please select a resource first.', false);
                return;
            }
            if (!date) {
                showResult('Please select a date first.', false);
                return;
            }
            if (!startTime || !endTime) {
                showResult('Please enter both start time and end time.', false);
                return;
            }
            if (endTime <= startTime) {
                showResult('End time must be after start time.', false);
                return;
            }

            // --- Show loading state ---
            resultDiv.style.display = 'block';
            resultDiv.className = 'availability-result';
            resultDiv.textContent = '⏳ Checking availability...';

            // --- Call the Flask API ---
            const url = `/api/check-availability?resource_id=${resourceId}&date=${date}&start_time=${startTime}&end_time=${endTime}`;

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.available) {
                        showResult('✅ ' + data.message, true);
                    } else {
                        showResult('❌ ' + data.message, false);
                    }
                })
                .catch(error => {
                    showResult('⚠️ Could not check availability. Please try again.', false);
                });
        });
    }

    // Helper to display availability result
    function showResult(message, isAvailable) {
        if (!resultDiv) return;
        resultDiv.style.display = 'block';
        resultDiv.textContent = message;
        resultDiv.className = 'availability-result ' + (isAvailable ? 'avail-yes' : 'avail-no');
    }

    // -------------------------------------------------------
    // AUTO-DISMISS ALERTS after 5 seconds
    // -------------------------------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // -------------------------------------------------------
    // FORM VALIDATION: End time > Start time
    // -------------------------------------------------------
    const requestForm = document.getElementById('requestForm');
    if (requestForm) {
        requestForm.addEventListener('submit', function (e) {
            const startTime = document.getElementById('start_time').value;
            const endTime   = document.getElementById('end_time').value;

            if (startTime && endTime && endTime <= startTime) {
                e.preventDefault();
                alert('End time must be after start time!');
            }
        });
    }

    // -------------------------------------------------------
    // Set minimum date for date input (today)
    // -------------------------------------------------------
    const dateInput = document.getElementById('date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
    }

});
