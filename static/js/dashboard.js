// Dashboard JavaScript - Handles dashboard functionality and real-time updates
class DashboardManager {
    constructor() {
        this.refreshInterval = null;
        this.chartInstances = {};
        this.notifications = [];
        this.isVisible = true;
        
        this.initializeVisibilityHandling();
        this.initializeAutoRefresh();
        this.initializeNotifications();
        this.initializeCharts();
        this.initializeWidgets();
    }

    // Visibility handling for tab switching
    initializeVisibilityHandling() {
        document.addEventListener('visibilitychange', () => {
            this.isVisible = !document.hidden;
            if (this.isVisible) {
                this.refreshDashboard();
            }
        });
    }

    // Auto-refresh functionality
    initializeAutoRefresh() {
        // Refresh every 2 minutes when visible
        this.refreshInterval = setInterval(() => {
            if (this.isVisible) {
                this.refreshDashboard();
            }
        }, 120000);
    }

    // Initialize notification system
    initializeNotifications() {
        this.checkForNotifications();
        
        // Check for new notifications every 30 seconds
        setInterval(() => {
            this.checkForNotifications();
        }, 30000);
    }

    // Initialize charts if Chart.js is available
    initializeCharts() {
        if (typeof Chart === 'undefined') {
            console.log('Chart.js not loaded, skipping chart initialization');
            return;
        }

        this.initializeSalesChart();
        this.initializeRevenueChart();
        this.initializeProductChart();
    }

    // Initialize dashboard widgets
    initializeWidgets() {
        this.initializeStatsCards();
        this.initializeLicenseStatus();
        this.initializeQuickActions();
        this.initializeRecentActivity();
    }

    // Refresh dashboard data
    async refreshDashboard() {
        try {
            await Promise.all([
                this.refreshStats(),
                this.refreshCharts(),
                this.refreshRecentActivity(),
                this.refreshLicenseStatus()
            ]);
            
            this.updateLastRefreshTime();
        } catch (error) {
            console.error('Dashboard refresh error:', error);
        }
    }

    // Refresh statistics
    async refreshStats() {
        try {
            const response = await fetch('/api/dashboard/stats');
            const stats = await response.json();
            
            if (stats.success) {
                this.updateStatsDisplay(stats.data);
            }
        } catch (error) {
            console.error('Error refreshing stats:', error);
        }
    }

    // Update statistics display
    updateStatsDisplay(stats) {
        const statElements = {
            'today_sales': stats.today_sales || 0,
            'today_revenue': this.formatCurrency(stats.today_revenue || 0),
            'total_products': stats.total_products || 0,
            'low_stock_products': stats.low_stock_products || 0,
            'total_customers': stats.total_customers || 0,
            'active_staff': stats.active_staff || 0
        };

        Object.entries(statElements).forEach(([key, value]) => {
            const element = document.getElementById(key);
            if (element) {
                this.animateNumberChange(element, value);
            }
        });
    }

    // Animate number changes
    animateNumberChange(element, newValue) {
        const currentValue = element.textContent;
        const isNumeric = !isNaN(parseFloat(currentValue));
        
        if (isNumeric && !isNaN(parseFloat(newValue))) {
            const start = parseFloat(currentValue);
            const end = parseFloat(newValue);
            const duration = 1000;
            const startTime = performance.now();
            
            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                const currentNum = start + (end - start) * this.easeOutCubic(progress);
                element.textContent = Math.round(currentNum).toLocaleString();
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            };
            
            requestAnimationFrame(animate);
        } else {
            element.textContent = newValue;
        }
    }

    // Easing function
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    // Initialize sales chart
    initializeSalesChart() {
        const salesChartCanvas = document.getElementById('salesChart');
        if (!salesChartCanvas) return;

        const ctx = salesChartCanvas.getContext('2d');
        
        this.chartInstances.salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Daily Sales',
                    data: [],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'KES ' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Initialize revenue chart
    initializeRevenueChart() {
        const revenueChartCanvas = document.getElementById('revenueChart');
        if (!revenueChartCanvas) return;

        const ctx = revenueChartCanvas.getContext('2d');
        
        this.chartInstances.revenueChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['M-Pesa', 'Cash'],
                datasets: [{
                    data: [60, 40],
                    backgroundColor: ['#198754', '#6c757d']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // Initialize product chart
    initializeProductChart() {
        const productChartCanvas = document.getElementById('productChart');
        if (!productChartCanvas) return;

        const ctx = productChartCanvas.getContext('2d');
        
        this.chartInstances.productChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Units Sold',
                    data: [],
                    backgroundColor: '#0dcaf0'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Refresh charts data
    async refreshCharts() {
        try {
            const response = await fetch('/api/dashboard/charts');
            const chartData = await response.json();
            
            if (chartData.success) {
                this.updateChartsData(chartData.data);
            }
        } catch (error) {
            console.error('Error refreshing charts:', error);
        }
    }

    // Update charts data
    updateChartsData(data) {
        // Update sales chart
        if (this.chartInstances.salesChart && data.sales_trend) {
            this.chartInstances.salesChart.data.labels = data.sales_trend.labels;
            this.chartInstances.salesChart.data.datasets[0].data = data.sales_trend.data;
            this.chartInstances.salesChart.update();
        }

        // Update revenue chart
        if (this.chartInstances.revenueChart && data.payment_methods) {
            this.chartInstances.revenueChart.data.datasets[0].data = data.payment_methods.data;
            this.chartInstances.revenueChart.update();
        }

        // Update product chart
        if (this.chartInstances.productChart && data.top_products) {
            this.chartInstances.productChart.data.labels = data.top_products.labels;
            this.chartInstances.productChart.data.datasets[0].data = data.top_products.data;
            this.chartInstances.productChart.update();
        }
    }

    // Initialize statistics cards
    initializeStatsCards() {
        const statCards = document.querySelectorAll('.stat-card');
        
        statCards.forEach(card => {
            card.addEventListener('click', () => {
                const action = card.dataset.action;
                if (action) {
                    this.handleStatCardClick(action);
                }
            });
        });
    }

    // Handle stat card clicks
    handleStatCardClick(action) {
        const actions = {
            'view_sales': '/pos/sales',
            'view_products': '/pos/products',
            'view_customers': '/pos/customers',
            'view_reports': '/pos/reports'
        };

        if (actions[action]) {
            window.location.href = actions[action];
        }
    }

    // Initialize license status
    initializeLicenseStatus() {
        this.updateLicenseStatusDisplay();
    }

    // Update license status display
    updateLicenseStatusDisplay() {
        const licenseStatusElement = document.querySelector('.license-status');
        if (!licenseStatusElement) return;

        const daysRemaining = parseInt(licenseStatusElement.dataset.daysRemaining);
        
        if (daysRemaining <= 5) {
            this.showLicenseWarning(daysRemaining);
        }
    }

    // Show license warning
    showLicenseWarning(daysRemaining) {
        if (daysRemaining <= 0) {
            this.showNotification(
                'License Expired',
                'Your license has expired. Please renew to continue using Comolor POS.',
                'error',
                0,
                [{
                    text: 'Renew Now',
                    action: () => window.location.href = '/license/payment'
                }]
            );
        } else if (daysRemaining <= 5) {
            this.showNotification(
                'License Expiring Soon',
                `Your license expires in ${daysRemaining} day${daysRemaining === 1 ? '' : 's'}. Renew now to avoid interruption.`,
                'warning',
                10000,
                [{
                    text: 'Renew',
                    action: () => window.location.href = '/license/payment'
                }]
            );
        }
    }

    // Initialize quick actions
    initializeQuickActions() {
        const quickActionButtons = document.querySelectorAll('.quick-action-btn');
        
        quickActionButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const action = button.dataset.action;
                this.handleQuickAction(action, e);
            });
        });
    }

    // Handle quick actions
    handleQuickAction(action, event) {
        event.preventDefault();
        
        const actions = {
            'new_sale': () => window.location.href = '/pos/sales',
            'add_product': () => this.showAddProductModal(),
            'add_customer': () => this.showAddCustomerModal(),
            'view_reports': () => window.location.href = '/pos/reports',
            'backup_data': () => this.initiateDataBackup(),
            'export_data': () => this.showExportOptions()
        };

        if (actions[action]) {
            actions[action]();
        }
    }

    // Initialize recent activity
    initializeRecentActivity() {
        this.refreshRecentActivity();
    }

    // Refresh recent activity
    async refreshRecentActivity() {
        try {
            const response = await fetch('/api/dashboard/recent-activity');
            const activity = await response.json();
            
            if (activity.success) {
                this.updateRecentActivityDisplay(activity.data);
            }
        } catch (error) {
            console.error('Error refreshing recent activity:', error);
        }
    }

    // Update recent activity display
    updateRecentActivityDisplay(activities) {
        const activityContainer = document.getElementById('recentActivity');
        if (!activityContainer) return;

        if (activities.length === 0) {
            activityContainer.innerHTML = '<p class="text-muted text-center">No recent activity</p>';
            return;
        }

        let activityHTML = '';
        activities.forEach(activity => {
            activityHTML += `
                <div class="activity-item d-flex align-items-center mb-3">
                    <div class="activity-icon me-3">
                        <i class="fas fa-${this.getActivityIcon(activity.type)} text-${this.getActivityColor(activity.type)}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="activity-title">${activity.title}</div>
                        <small class="text-muted">${this.formatTimeAgo(activity.created_at)}</small>
                    </div>
                    ${activity.amount ? `<div class="activity-amount text-success">KES ${activity.amount.toLocaleString()}</div>` : ''}
                </div>
            `;
        });

        activityContainer.innerHTML = activityHTML;
    }

    // Get activity icon
    getActivityIcon(type) {
        const icons = {
            'sale': 'shopping-cart',
            'payment': 'credit-card',
            'product_added': 'plus-circle',
            'customer_added': 'user-plus',
            'login': 'sign-in-alt',
            'logout': 'sign-out-alt',
            'report_generated': 'chart-bar'
        };
        return icons[type] || 'info-circle';
    }

    // Get activity color
    getActivityColor(type) {
        const colors = {
            'sale': 'success',
            'payment': 'primary',
            'product_added': 'info',
            'customer_added': 'info',
            'login': 'success',
            'logout': 'secondary',
            'report_generated': 'warning'
        };
        return colors[type] || 'secondary';
    }

    // Check for notifications
    async checkForNotifications() {
        try {
            const response = await fetch('/api/dashboard/notifications');
            const notifications = await response.json();
            
            if (notifications.success) {
                this.processNotifications(notifications.data);
            }
        } catch (error) {
            console.error('Error checking notifications:', error);
        }
    }

    // Process notifications
    processNotifications(notifications) {
        notifications.forEach(notification => {
            if (!this.notifications.find(n => n.id === notification.id)) {
                this.notifications.push(notification);
                this.showNotification(
                    notification.title,
                    notification.message,
                    notification.type,
                    notification.duration || 5000
                );
            }
        });
    }

    // Show notification
    showNotification(title, message, type = 'info', duration = 5000, actions = []) {
        const notificationId = 'notification_' + Date.now();
        
        const notification = document.createElement('div');
        notification.id = notificationId;
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show dashboard-notification`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '350px';
        notification.style.maxWidth = '400px';
        
        let actionsHTML = '';
        if (actions.length > 0) {
            actionsHTML = '<div class="mt-2">';
            actions.forEach(action => {
                actionsHTML += `<button class="btn btn-sm btn-outline-${type} me-2" onclick="(${action.action.toString()})(); document.getElementById('${notificationId}').remove();">${action.text}</button>`;
            });
            actionsHTML += '</div>';
        }

        notification.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="me-3">
                    <i class="fas fa-${this.getNotificationIcon(type)} fa-lg"></i>
                </div>
                <div class="flex-grow-1">
                    <h6 class="alert-heading mb-1">${title}</h6>
                    <p class="mb-0">${message}</p>
                    ${actionsHTML}
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after duration (if duration > 0)
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }

        return notification;
    }

    // Get notification icon
    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Update last refresh time
    updateLastRefreshTime() {
        const lastRefreshElement = document.getElementById('lastRefresh');
        if (lastRefreshElement) {
            lastRefreshElement.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
        }
    }

    // Utility methods
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-KE', {
            style: 'currency',
            currency: 'KES'
        }).format(amount);
    }

    formatTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);

        if (diffInSeconds < 60) {
            return 'Just now';
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} hour${hours === 1 ? '' : 's'} ago`;
        } else {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days} day${days === 1 ? '' : 's'} ago`;
        }
    }

    // Modal methods
    showAddProductModal() {
        const modal = document.getElementById('addProductModal');
        if (modal) {
            new bootstrap.Modal(modal).show();
        } else {
            window.location.href = '/pos/products';
        }
    }

    showAddCustomerModal() {
        const modal = document.getElementById('addCustomerModal');
        if (modal) {
            new bootstrap.Modal(modal).show();
        } else {
            window.location.href = '/pos/customers';
        }
    }

    showExportOptions() {
        this.showNotification(
            'Export Options',
            'Choose what data to export:',
            'info',
            0,
            [
                { text: 'Products', action: () => window.location.href = '/pos/products/export' },
                { text: 'Customers', action: () => window.location.href = '/pos/customers/export' },
                { text: 'Sales', action: () => window.location.href = '/pos/sales/export' }
            ]
        );
    }

    async initiateDataBackup() {
        try {
            this.showNotification('Backup Started', 'Creating data backup...', 'info', 3000);
            
            const response = await fetch('/api/dashboard/backup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Backup Complete', 'Data backup created successfully.', 'success');
                // Trigger download
                if (result.download_url) {
                    window.location.href = result.download_url;
                }
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.showNotification('Backup Failed', error.message || 'Failed to create backup.', 'error');
        }
    }

    // Cleanup
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        Object.values(this.chartInstances).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Dashboard utilities
window.DashboardUtils = {
    refreshStats: () => {
        if (window.dashboard) {
            window.dashboard.refreshStats();
        }
    },
    
    refreshCharts: () => {
        if (window.dashboard) {
            window.dashboard.refreshCharts();
        }
    },
    
    showQuickSale: () => {
        window.location.href = '/pos/sales';
    },
    
    formatCurrency: (amount) => {
        return new Intl.NumberFormat('en-KE', {
            style: 'currency',
            currency: 'KES'
        }).format(amount);
    }
};

// Initialize dashboard when DOM is ready
let dashboard;

document.addEventListener('DOMContentLoaded', function() {
    dashboard = new DashboardManager();
    window.dashboard = dashboard;
    
    console.log('Dashboard manager initialized');
    
    // Handle page unload
    window.addEventListener('beforeunload', () => {
        if (dashboard) {
            dashboard.destroy();
        }
    });
});

// Add dashboard-specific CSS
const dashboardCSS = `
.dashboard-notification {
    animation: slideInRight 0.3s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-card {
    transition: all 0.3s ease;
    cursor: pointer;
}

.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.activity-item {
    transition: background-color 0.2s ease;
    padding: 0.5rem;
    border-radius: 6px;
}

.activity-item:hover {
    background-color: rgba(0, 0, 0, 0.05);
}

.activity-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: rgba(0, 0, 0, 0.05);
    display: flex;
    align-items: center;
    justify-content: center;
}

.quick-action-btn {
    transition: all 0.2s ease;
}

.quick-action-btn:hover {
    transform: translateY(-1px);
}

.license-status.warning {
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.7; }
    100% { opacity: 1; }
}

.chart-container {
    position: relative;
    height: 300px;
}

@media (max-width: 768px) {
    .dashboard-notification {
        right: 10px;
        left: 10px;
        min-width: auto;
        max-width: none;
    }
    
    .chart-container {
        height: 250px;
    }
}
`;

// Inject dashboard CSS
const dashboardStyle = document.createElement('style');
dashboardStyle.textContent = dashboardCSS;
document.head.appendChild(dashboardStyle);
