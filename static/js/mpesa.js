// M-Pesa Integration JavaScript
class MpesaHandler {
    constructor() {
        this.pollInterval = null;
        this.maxPollAttempts = 60; // 5 minutes with 5-second intervals
        this.currentPollAttempts = 0;
        this.isPolling = false;
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Listen for M-Pesa payment initiation
        document.addEventListener('mpesa:payment:initiated', (e) => {
            this.handlePaymentInitiated(e.detail);
        });

        // Listen for payment status updates
        document.addEventListener('mpesa:payment:status', (e) => {
            this.handlePaymentStatus(e.detail);
        });

        // Handle STK push timeout
        document.addEventListener('mpesa:payment:timeout', (e) => {
            this.handlePaymentTimeout(e.detail);
        });
    }

    // Initialize STK Push payment
    async initiateSTKPush(phoneNumber, amount, reference, description = 'Comolor POS Payment') {
        try {
            this.showPaymentProcessing();
            
            const response = await fetch('/mpesa/stk-push', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone_number: this.formatPhoneNumber(phoneNumber),
                    amount: parseFloat(amount),
                    reference: reference,
                    description: description
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.handleSTKPushSuccess(result);
                return result;
            } else {
                throw new Error(result.message || 'Failed to initiate M-Pesa payment');
            }
        } catch (error) {
            this.handleSTKPushError(error);
            throw error;
        }
    }

    // Handle successful STK push initiation
    handleSTKPushSuccess(result) {
        this.showSTKPushPrompt(result);
        
        // Start polling for payment status
        this.startPaymentStatusPolling(result.checkout_request_id || result.reference);
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('mpesa:stk:success', {
            detail: result
        }));
    }

    // Handle STK push error
    handleSTKPushError(error) {
        console.error('STK Push Error:', error);
        this.hidePaymentProcessing();
        this.showPaymentError(error.message);
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('mpesa:stk:error', {
            detail: { error: error.message }
        }));
    }

    // Start polling for payment status
    startPaymentStatusPolling(checkoutRequestId) {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.currentPollAttempts = 0;
        
        this.pollInterval = setInterval(() => {
            this.checkPaymentStatus(checkoutRequestId);
        }, 5000); // Poll every 5 seconds
    }

    // Stop polling for payment status
    stopPaymentStatusPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
        this.currentPollAttempts = 0;
    }

    // Check payment status
    async checkPaymentStatus(checkoutRequestId) {
        try {
            this.currentPollAttempts++;
            
            if (this.currentPollAttempts > this.maxPollAttempts) {
                this.stopPaymentStatusPolling();
                this.handlePaymentTimeout();
                return;
            }

            const response = await fetch(`/mpesa/status/${checkoutRequestId}`);
            const result = await response.json();
            
            if (result.status === 'completed') {
                this.stopPaymentStatusPolling();
                this.handlePaymentSuccess(result);
            } else if (result.status === 'failed') {
                this.stopPaymentStatusPolling();
                this.handlePaymentFailure(result);
            }
            // Continue polling for pending status
            
        } catch (error) {
            console.error('Payment status check error:', error);
            // Continue polling unless max attempts reached
        }
    }

    // Handle payment success
    handlePaymentSuccess(result) {
        this.hidePaymentProcessing();
        this.showPaymentSuccess(result);
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('mpesa:payment:success', {
            detail: result
        }));
        
        // Auto-redirect or refresh after success
        setTimeout(() => {
            if (result.redirect_url) {
                window.location.href = result.redirect_url;
            } else {
                location.reload();
            }
        }, 3000);
    }

    // Handle payment failure
    handlePaymentFailure(result) {
        this.hidePaymentProcessing();
        this.showPaymentError(result.message || 'Payment was cancelled or failed');
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('mpesa:payment:failure', {
            detail: result
        }));
    }

    // Handle payment timeout
    handlePaymentTimeout() {
        this.hidePaymentProcessing();
        this.showPaymentTimeout();
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('mpesa:payment:timeout', {
            detail: { message: 'Payment request timed out' }
        }));
    }

    // UI Methods
    showPaymentProcessing() {
        // Show processing modal or overlay
        const processingModal = document.getElementById('mpesaProcessingModal');
        if (processingModal) {
            const modal = new bootstrap.Modal(processingModal);
            modal.show();
        } else {
            this.createProcessingOverlay();
        }
    }

    hidePaymentProcessing() {
        // Hide processing modal or overlay
        const processingModal = document.getElementById('mpesaProcessingModal');
        if (processingModal) {
            const modal = bootstrap.Modal.getInstance(processingModal);
            if (modal) modal.hide();
        }
        
        const overlay = document.getElementById('mpesaProcessingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    showSTKPushPrompt(result) {
        this.showNotification(
            'M-Pesa Payment Initiated',
            'Please check your phone and enter your M-Pesa PIN to complete the payment.',
            'info',
            10000
        );
    }

    showPaymentSuccess(result) {
        this.showNotification(
            'Payment Successful!',
            `Payment of KES ${result.amount} completed successfully. Reference: ${result.receipt_number}`,
            'success',
            5000
        );
    }

    showPaymentError(message) {
        this.showNotification(
            'Payment Failed',
            message,
            'error',
            8000
        );
    }

    showPaymentTimeout() {
        this.showNotification(
            'Payment Timeout',
            'The payment request has timed out. Please try again.',
            'warning',
            5000
        );
    }

    createProcessingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'mpesaProcessingOverlay';
        overlay.className = 'mpesa-processing-overlay';
        overlay.innerHTML = `
            <div class="mpesa-processing-content">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5>Processing M-Pesa Payment...</h5>
                <p>Please check your phone for the STK push notification and enter your M-Pesa PIN.</p>
                <div class="progress mt-3">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Animate progress bar
        const progressBar = overlay.querySelector('.progress-bar');
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 2;
            progressBar.style.width = Math.min(progress, 95) + '%';
            
            if (progress >= 100) {
                clearInterval(progressInterval);
            }
        }, 1000);
    }

    // Utility Methods
    formatPhoneNumber(phone) {
        // Remove all non-numeric characters
        let cleaned = phone.replace(/\D/g, '');
        
        // Convert to 254 format
        if (cleaned.startsWith('0')) {
            cleaned = '254' + cleaned.substring(1);
        } else if (cleaned.startsWith('+254')) {
            cleaned = cleaned.substring(1);
        } else if (!cleaned.startsWith('254')) {
            cleaned = '254' + cleaned;
        }
        
        return cleaned;
    }

    validatePhoneNumber(phone) {
        const formatted = this.formatPhoneNumber(phone);
        // Kenyan phone number validation (Safaricom, Airtel, Telkom)
        const kenyaPhoneRegex = /^254[71]\d{8}$/;
        return kenyaPhoneRegex.test(formatted);
    }

    showNotification(title, message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show mpesa-notification`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '350px';
        notification.style.maxWidth = '400px';
        
        notification.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="me-3">
                    <i class="fas fa-${this.getNotificationIcon(type)} fa-lg"></i>
                </div>
                <div class="flex-grow-1">
                    <h6 class="alert-heading mb-1">${title}</h6>
                    <p class="mb-0">${message}</p>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);

        return notification;
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Business-specific methods
    async initiateLicensePayment(plan, phoneNumber) {
        const amounts = {
            'monthly': 3000,
            'yearly': 30000
        };
        
        const amount = amounts[plan];
        if (!amount) {
            throw new Error('Invalid subscription plan');
        }
        
        return await this.initiateSTKPush(
            phoneNumber,
            amount,
            `LICENSE_${plan.toUpperCase()}_${Date.now()}`,
            `Comolor POS ${plan} license`
        );
    }

    async initiateSalePayment(saleId, amount, phoneNumber) {
        return await this.initiateSTKPush(
            phoneNumber,
            amount,
            `SALE_${saleId}_${Date.now()}`,
            `Comolor POS Sale #${saleId}`
        );
    }

    // Till number validation
    validateTillNumber(tillNumber) {
        // Basic till number validation (5-7 digits)
        const tillRegex = /^\d{5,7}$/;
        return tillRegex.test(tillNumber);
    }

    // Paybill validation
    validatePaybill(paybill) {
        // Basic paybill validation (5-7 digits)
        const paybillRegex = /^\d{5,7}$/;
        return paybillRegex.test(paybill);
    }
}

// Transaction status checker
class MpesaTransactionChecker {
    constructor() {
        this.checkInterval = null;
    }

    startChecking(transactionId, callback, interval = 5000, maxAttempts = 60) {
        let attempts = 0;
        
        this.checkInterval = setInterval(async () => {
            attempts++;
            
            if (attempts > maxAttempts) {
                clearInterval(this.checkInterval);
                callback({ status: 'timeout', message: 'Transaction check timed out' });
                return;
            }

            try {
                const response = await fetch(`/mpesa/transaction/${transactionId}/status`);
                const result = await response.json();
                
                if (result.status !== 'pending') {
                    clearInterval(this.checkInterval);
                    callback(result);
                }
            } catch (error) {
                console.error('Transaction status check error:', error);
            }
        }, interval);
    }

    stop() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }
}

// Global M-Pesa helper functions
window.MpesaHelpers = {
    formatKenyaPhone: (phone) => {
        const mpesa = new MpesaHandler();
        return mpesa.formatPhoneNumber(phone);
    },
    
    validateKenyaPhone: (phone) => {
        const mpesa = new MpesaHandler();
        return mpesa.validatePhoneNumber(phone);
    },
    
    formatCurrency: (amount) => {
        return new Intl.NumberFormat('en-KE', {
            style: 'currency',
            currency: 'KES'
        }).format(amount);
    }
};

// Initialize M-Pesa handler when DOM is ready
let mpesaHandler;
let transactionChecker;

document.addEventListener('DOMContentLoaded', function() {
    mpesaHandler = new MpesaHandler();
    transactionChecker = new MpesaTransactionChecker();
    
    // Make globally available
    window.mpesaHandler = mpesaHandler;
    window.transactionChecker = transactionChecker;
    
    console.log('M-Pesa handler initialized');
});

// Add M-Pesa specific CSS
const mpesaCSS = `
.mpesa-processing-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.mpesa-processing-content {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    text-align: center;
    max-width: 400px;
    width: 90%;
    color: #333;
}

.mpesa-notification {
    animation: slideInRight 0.3s ease;
}

@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.mpesa-phone-input {
    position: relative;
}

.mpesa-phone-input::before {
    content: "+254";
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #6c757d;
    z-index: 1;
}

.mpesa-phone-input input {
    padding-left: 50px;
}

.mpesa-status-pending {
    color: #ffc107;
}

.mpesa-status-success {
    color: #198754;
}

.mpesa-status-failed {
    color: #dc3545;
}

.mpesa-logo {
    height: 24px;
    vertical-align: middle;
}
`;

// Inject CSS
const style = document.createElement('style');
style.textContent = mpesaCSS;
document.head.appendChild(style);
