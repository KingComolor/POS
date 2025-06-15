// POS JavaScript - Main Point of Sale functionality
class ComolorPOS {
    constructor() {
        this.cart = [];
        this.products = [];
        this.customers = [];
        this.currentCustomer = null;
        this.taxRate = 0;
        this.discountAmount = 0;
        
        this.initializeEventListeners();
        this.loadInitialData();
    }

    initializeEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('productSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.filterProducts(e.target.value));
        }

        // Category filter
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => this.filterByCategory(e.target.value));
        }

        // Customer selection
        const customerSelect = document.getElementById('customerSelect');
        if (customerSelect) {
            customerSelect.addEventListener('change', (e) => this.selectCustomer(e.target.value));
        }

        // Discount input
        const discountInput = document.getElementById('discountAmount');
        if (discountInput) {
            discountInput.addEventListener('input', (e) => this.updateDiscount(e.target.value));
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    loadInitialData() {
        // Products are loaded from the template
        if (typeof products !== 'undefined') {
            this.products = products;
        }
        
        // Tax rate from template
        if (typeof taxRate !== 'undefined') {
            this.taxRate = taxRate;
        }

        this.updateCartDisplay();
    }

    // Product Management
    addToCart(productId) {
        const product = this.products.find(p => p.id === productId);
        if (!product) {
            this.showAlert('Product not found', 'error');
            return;
        }

        if (product.stock_quantity <= 0) {
            this.showAlert('Product is out of stock', 'warning');
            return;
        }

        const existingItem = this.cart.find(item => item.product_id === productId);
        
        if (existingItem) {
            if (existingItem.quantity >= product.stock_quantity) {
                this.showAlert('Cannot add more items than available in stock', 'warning');
                return;
            }
            existingItem.quantity += 1;
        } else {
            this.cart.push({
                product_id: productId,
                name: product.name,
                price: product.selling_price,
                quantity: 1,
                stock_available: product.stock_quantity
            });
        }

        this.updateCartDisplay();
        this.showAlert(`${product.name} added to cart`, 'success', 2000);
    }

    removeFromCart(productId) {
        this.cart = this.cart.filter(item => item.product_id !== productId);
        this.updateCartDisplay();
    }

    updateCartQuantity(productId, newQuantity) {
        const item = this.cart.find(item => item.product_id === productId);
        if (!item) return;

        newQuantity = Math.max(0, parseInt(newQuantity));
        
        if (newQuantity === 0) {
            this.removeFromCart(productId);
            return;
        }

        if (newQuantity > item.stock_available) {
            this.showAlert('Cannot exceed available stock', 'warning');
            return;
        }

        item.quantity = newQuantity;
        this.updateCartDisplay();
    }

    clearCart() {
        if (this.cart.length === 0) {
            this.showAlert('Cart is already empty', 'info');
            return;
        }

        if (confirm('Are you sure you want to clear the cart?')) {
            this.cart = [];
            this.currentCustomer = null;
            this.discountAmount = 0;
            
            // Reset form values
            const customerSelect = document.getElementById('customerSelect');
            if (customerSelect) customerSelect.value = '';
            
            const discountInput = document.getElementById('discountAmount');
            if (discountInput) discountInput.value = '0';

            this.updateCartDisplay();
            this.showAlert('Cart cleared', 'info');
        }
    }

    // Cart Display
    updateCartDisplay() {
        const cartItemsContainer = document.getElementById('cartItems');
        const emptyCartMsg = document.getElementById('emptyCart');
        const cartCount = document.getElementById('cartCount');
        const checkoutBtn = document.getElementById('checkoutBtn');

        if (!cartItemsContainer) return;

        // Update cart count
        if (cartCount) {
            cartCount.textContent = this.cart.length;
        }

        // Enable/disable checkout button
        if (checkoutBtn) {
            checkoutBtn.disabled = this.cart.length === 0;
        }

        if (this.cart.length === 0) {
            if (emptyCartMsg) emptyCartMsg.style.display = 'block';
            cartItemsContainer.innerHTML = '';
            this.updateTotals();
            return;
        }

        if (emptyCartMsg) emptyCartMsg.style.display = 'none';

        let cartHTML = '';
        this.cart.forEach(item => {
            cartHTML += `
                <div class="cart-item">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${item.name}</h6>
                            <small class="text-muted">KES ${item.price.toFixed(2)} each</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="pos.removeFromCart(${item.product_id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="cart-item-controls">
                            <button class="cart-quantity-btn" onclick="pos.updateCartQuantity(${item.product_id}, ${item.quantity - 1})">
                                <i class="fas fa-minus"></i>
                            </button>
                            <input type="number" class="form-control form-control-sm text-center" 
                                   style="width: 60px;" value="${item.quantity}" min="1" max="${item.stock_available}"
                                   onchange="pos.updateCartQuantity(${item.product_id}, this.value)">
                            <button class="cart-quantity-btn" onclick="pos.updateCartQuantity(${item.product_id}, ${item.quantity + 1})">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="text-end">
                            <strong>KES ${(item.price * item.quantity).toFixed(2)}</strong>
                        </div>
                    </div>
                </div>
            `;
        });

        cartItemsContainer.innerHTML = cartHTML;
        this.updateTotals();
    }

    updateTotals() {
        const subtotal = this.calculateSubtotal();
        const taxAmount = this.calculateTax(subtotal);
        const total = subtotal + taxAmount - this.discountAmount;

        // Update display elements
        const subtotalElement = document.getElementById('subtotal');
        const taxAmountElement = document.getElementById('taxAmount');
        const totalAmountElement = document.getElementById('totalAmount');

        if (subtotalElement) {
            subtotalElement.textContent = `KES ${subtotal.toFixed(2)}`;
        }
        
        if (taxAmountElement) {
            taxAmountElement.textContent = `KES ${taxAmount.toFixed(2)}`;
        }
        
        if (totalAmountElement) {
            totalAmountElement.textContent = `KES ${total.toFixed(2)}`;
        }
    }

    calculateSubtotal() {
        return this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }

    calculateTax(subtotal) {
        return (subtotal - this.discountAmount) * (this.taxRate / 100);
    }

    updateDiscount(amount) {
        this.discountAmount = Math.max(0, parseFloat(amount) || 0);
        this.updateTotals();
    }

    // Search and Filter
    filterProducts(searchTerm = '') {
        const productItems = document.querySelectorAll('.product-item');
        const searchLower = searchTerm.toLowerCase();

        productItems.forEach(item => {
            const name = item.dataset.name || '';
            const sku = item.dataset.sku || '';
            const category = item.dataset.category || '';
            
            const matches = name.includes(searchLower) || 
                          sku.includes(searchLower) || 
                          category.includes(searchLower);
            
            item.style.display = matches ? 'block' : 'none';
        });
    }

    filterByCategory(category = '') {
        const productItems = document.querySelectorAll('.product-item');
        
        productItems.forEach(item => {
            const itemCategory = item.dataset.category || '';
            const matches = !category || itemCategory === category;
            item.style.display = matches ? 'block' : 'none';
        });
    }

    // Customer Management
    selectCustomer(customerId) {
        this.currentCustomer = customerId ? parseInt(customerId) : null;
    }

    // Checkout Process
    showCheckout() {
        if (this.cart.length === 0) {
            this.showAlert('Cart is empty', 'warning');
            return;
        }

        const modal = new bootstrap.Modal(document.getElementById('checkoutModal'));
        this.updateCheckoutSummary();
        modal.show();
    }

    updateCheckoutSummary() {
        const subtotal = this.calculateSubtotal();
        const taxAmount = this.calculateTax(subtotal);
        const total = subtotal + taxAmount - this.discountAmount;

        // Update checkout modal elements
        const elements = {
            'checkoutItemCount': this.cart.length,
            'checkoutSubtotal': `KES ${subtotal.toFixed(2)}`,
            'checkoutDiscount': `KES ${this.discountAmount.toFixed(2)}`,
            'checkoutTax': `KES ${taxAmount.toFixed(2)}`,
            'checkoutTotal': `KES ${total.toFixed(2)}`,
            'cashAmount': total.toFixed(2),
            'mpesaAmount': total.toFixed(2)
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    selectPaymentMethod(method) {
        // Hide all payment method details
        document.querySelectorAll('.payment-method-selector').forEach(el => {
            el.classList.remove('active');
        });

        // Show selected payment method details
        const selectedDetails = document.getElementById(`${method}PaymentDetails`);
        if (selectedDetails) {
            selectedDetails.classList.add('active');
        }

        this.updateCheckoutSummary();
    }

    async processSale() {
        const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked');
        if (!paymentMethod) {
            this.showAlert('Please select a payment method', 'error');
            return;
        }

        const processSaleBtn = document.getElementById('processSaleBtn');
        const originalText = processSaleBtn.innerHTML;
        
        try {
            // Show loading state
            processSaleBtn.disabled = true;
            processSaleBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';

            const saleData = {
                items: this.cart.map(item => ({
                    product_id: item.product_id,
                    quantity: item.quantity,
                    price: item.price
                })),
                customer_id: this.currentCustomer,
                payment_method: paymentMethod.value,
                discount_amount: this.discountAmount
            };

            // Add phone number for M-Pesa payments
            if (paymentMethod.value === 'mpesa') {
                const phoneInput = document.getElementById('customerPhone');
                if (!phoneInput || !phoneInput.value) {
                    throw new Error('Phone number is required for M-Pesa payment');
                }
                saleData.phone = phoneInput.value;
            }

            // Show processing modal
            bootstrap.Modal.getInstance(document.getElementById('checkoutModal')).hide();
            const processingModal = new bootstrap.Modal(document.getElementById('processingModal'));
            processingModal.show();

            const response = await fetch('/pos/process-sale', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(saleData)
            });

            const result = await response.json();

            if (result.success) {
                processingModal.hide();
                this.handleSaleSuccess(result);
            } else {
                throw new Error(result.message || 'Sale processing failed');
            }

        } catch (error) {
            console.error('Sale processing error:', error);
            this.showAlert(error.message || 'Sale processing failed', 'error');
            
            // Hide processing modal if it's open
            const processingModal = bootstrap.Modal.getInstance(document.getElementById('processingModal'));
            if (processingModal) {
                processingModal.hide();
            }
        } finally {
            // Restore button
            processSaleBtn.disabled = false;
            processSaleBtn.innerHTML = originalText;
        }
    }

    handleSaleSuccess(result) {
        if (result.requires_payment) {
            // M-Pesa payment - show payment status
            this.showAlert('M-Pesa payment initiated. Please complete payment on your phone.', 'info');
            // Optionally redirect to payment status page
            // window.location.href = `/pos/payment-status/${result.sale_id}`;
        } else {
            // Cash payment - immediate success
            this.showAlert('Sale completed successfully!', 'success');
            
            // Open receipt in new window
            if (result.sale_id) {
                this.printReceipt(result.sale_id);
            }
        }

        // Clear cart and reset form
        this.clearCart();
        
        // Reset payment method selection
        document.querySelectorAll('input[name="paymentMethod"]').forEach(input => {
            input.checked = false;
        });
        
        document.querySelectorAll('.payment-method-selector').forEach(el => {
            el.classList.remove('active');
        });
    }

    printReceipt(saleId) {
        const receiptWindow = window.open(`/receipt/${saleId}`, '_blank', 'width=400,height=600');
        if (receiptWindow) {
            receiptWindow.focus();
        }
    }

    // Barcode Scanner
    scanBarcode() {
        this.showAlert('Barcode scanner integration coming soon!', 'info');
        // TODO: Implement barcode scanner integration
    }

    // Keyboard Shortcuts
    handleKeyboardShortcuts(e) {
        // F1 - Help
        if (e.key === 'F1') {
            e.preventDefault();
            this.showHelp();
        }
        
        // F2 - Clear cart
        if (e.key === 'F2') {
            e.preventDefault();
            this.clearCart();
        }
        
        // F3 - Focus search
        if (e.key === 'F3') {
            e.preventDefault();
            const searchInput = document.getElementById('productSearch');
            if (searchInput) searchInput.focus();
        }
        
        // Enter - Checkout (if cart has items)
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            if (this.cart.length > 0) {
                this.showCheckout();
            }
        }
        
        // Escape - Close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    }

    showHelp() {
        const helpText = `
Keyboard Shortcuts:
F1 - Show this help
F2 - Clear cart
F3 - Focus search
Ctrl+Enter - Checkout
Escape - Close modals

Mouse Actions:
Click product - Add to cart
Click quantity +/- - Adjust quantity
Click trash icon - Remove from cart
        `;
        alert(helpText);
    }

    // Utility Functions
    showAlert(message, type = 'info', duration = 5000) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '300px';
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        // Auto-remove after duration
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }

    formatCurrency(amount) {
        return `KES ${amount.toFixed(2)}`;
    }

    validatePhoneNumber(phone) {
        // Basic Kenyan phone number validation
        const phoneRegex = /^(254|0)[71]\d{8}$/;
        return phoneRegex.test(phone.replace(/\s+/g, ''));
    }
}

// Initialize POS when DOM is loaded
let pos;

function initializePOS() {
    pos = new ComolorPOS();
    
    // Make functions globally available for onclick handlers
    window.addToCart = (productId) => pos.addToCart(productId);
    window.removeFromCart = (productId) => pos.removeFromCart(productId);
    window.updateCartQuantity = (productId, quantity) => pos.updateCartQuantity(productId, quantity);
    window.clearCart = () => pos.clearCart();
    window.showCheckout = () => pos.showCheckout();
    window.selectPaymentMethod = (method) => pos.selectPaymentMethod(method);
    window.processSale = () => pos.processSale();
    window.scanBarcode = () => pos.scanBarcode();
    
    console.log('Comolor POS initialized successfully');
}

// Auto-initialize if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePOS);
} else {
    initializePOS();
}
