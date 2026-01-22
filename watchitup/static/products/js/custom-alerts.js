/**
 * Custom Alert Notification System
 * Usage: showAlert(message, type, duration)
 */

(function() {
    'use strict';
    
    // Create alert container if it doesn't exist
    function createAlertContainer() {
        let container = document.getElementById('custom-alert-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'custom-alert-container';
            container.className = 'alert-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    // Get icon for alert type
    function getAlertIcon(type) {
        const icons = {
            'success': '✓',
            'error': '✕',
            'danger': '✕',
            'warning': '!',
            'info': 'i'
        };
        return icons[type] || 'i';
    }
    
    // Get title for alert type
    function getAlertTitle(type) {
        const titles = {
            'success': 'Success',
            'error': 'Error',
            'danger': 'Error',
            'warning': 'Warning',
            'info': 'Information'
        };
        return titles[type] || 'Notification';
    }
    
    // Show alert
    function showAlert(message, type = 'info', duration = 5000) {
        const container = createAlertContainer();
        
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `custom-alert alert-${type}`;
        
        const icon = getAlertIcon(type);
        const title = getAlertTitle(type);
        
        alert.innerHTML = `
            <div class="alert-icon">${icon}</div>
            <div class="alert-content">
                <div class="alert-title">${title}</div>
                <div class="alert-message">${message}</div>
            </div>
            <button class="alert-close" aria-label="Close">&times;</button>
            <div class="alert-progress"></div>
        `;
        
        // Add to container
        container.appendChild(alert);
        
        // Close button handler
        const closeBtn = alert.querySelector('.alert-close');
        closeBtn.addEventListener('click', () => {
            removeAlert(alert);
        });
        
        // Auto remove after duration
        const timeout = setTimeout(() => {
            removeAlert(alert);
        }, duration);
        
        // Pause on hover
        alert.addEventListener('mouseenter', () => {
            clearTimeout(timeout);
            const progress = alert.querySelector('.alert-progress');
            if (progress) {
                progress.style.animationPlayState = 'paused';
            }
        });
        
        alert.addEventListener('mouseleave', () => {
            const newTimeout = setTimeout(() => {
                removeAlert(alert);
            }, 2000); // Give 2 more seconds
        });
        
        // Limit number of alerts
        const alerts = container.querySelectorAll('.custom-alert');
        if (alerts.length > 5) {
            removeAlert(alerts[0]);
        }
        
        return alert;
    }
    
    // Remove alert with animation
    function removeAlert(alert) {
        if (!alert || !alert.parentNode) return;
        
        alert.classList.add('removing');
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 400);
    }
    
    // Make globally available
    window.showAlert = showAlert;
    
    // Process Django messages on page load
    document.addEventListener('DOMContentLoaded', function() {
        const djangoMessages = document.querySelectorAll('.django-messages .alert');
        
        djangoMessages.forEach(function(msg) {
            const type = msg.classList.contains('alert-success') ? 'success' :
                        msg.classList.contains('alert-danger') ? 'error' :
                        msg.classList.contains('alert-warning') ? 'warning' :
                        msg.classList.contains('alert-info') ? 'info' : 'info';
            
            const message = msg.textContent.trim();
            
            if (message) {
                showAlert(message, type);
            }
        });
        
        // Hide Django messages container after processing
        const djangoContainer = document.querySelector('.django-messages');
        if (djangoContainer) {
            djangoContainer.style.display = 'none';
        }
    });
    
})();

// Backward compatibility - replace old showMessage function
if (typeof showMessage === 'undefined') {
    window.showMessage = function(message, type) {
        window.showAlert(message, type);
    };
}