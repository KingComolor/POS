# Comolor POS - Developer Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Development Setup](#development-setup)
4. [Database Design](#database-design)
5. [API Endpoints](#api-endpoints)
6. [Authentication & Authorization](#authentication--authorization)
7. [M-Pesa Integration](#m-pesa-integration)
8. [Testing](#testing)
9. [Code Structure](#code-structure)
10. [Contributing](#contributing)

## Project Overview

Comolor POS is a multi-tenant, web-based Point of Sale system specifically designed for Kenyan businesses. It provides comprehensive business management capabilities with integrated M-Pesa payments and automated licensing.

### Key Features
- Multi-tenant architecture with business isolation
- Role-based access control (Super Admin, Business Owner, Cashier)
- M-Pesa STK Push payment integration
- Automated license management and expiry handling
- Real-time inventory tracking
- Sales reporting and analytics
- Email notifications
- Receipt generation

## Architecture

### Backend Stack
- **Framework**: Python Flask 3.1.1
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login with session management
- **Background Tasks**: APScheduler for automated tasks
- **Payment Processing**: M-Pesa Daraja API integration
- **Email Service**: Flask-Mail with SMTP

### Frontend Stack
- **Template Engine**: Jinja2
- **CSS Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla ES6+ with modular components
- **Icons**: Font Awesome 6
- **Charts**: Chart.js for analytics

### Multi-Tenant Design
- Business isolation through `business_id` foreign keys
- Shared infrastructure with tenant-aware queries
- Super admin global access with business-specific data isolation

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Git

### Local Installation
```bash
# Clone the repository
git clone <repository-url>
cd comolor-pos

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run the application
python main.py
```

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://username:password@localhost/comolor_pos

# Session Security
SESSION_SECRET=your-secure-session-secret

# M-Pesa Configuration
MPESA_CONSUMER_KEY=your-mpesa-consumer-key
MPESA_CONSUMER_SECRET=your-mpesa-consumer-secret
MPESA_PASSKEY=your-mpesa-passkey
MPESA_SHORTCODE=your-business-shortcode
DEVELOPER_TILL_NUMBER=your-developer-till-number

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## Database Design

### Core Tables

#### Users Table
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Businesses Table
```python
class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.Enum(BusinessStatus), default=BusinessStatus.PENDING)
    license_expires_at = db.Column(db.DateTime, nullable=True)
    subscription_plan = db.Column(db.String(50), default='monthly')
```

#### Sales Table
```python
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    sale_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.Enum(PaymentStatus))
```

### Relationships
- One-to-Many: Business → Users, Products, Sales, Customers
- Many-to-Many: Sales ↔ Products (through SaleItems)
- One-to-Many: Sales → Payments, ActivityLogs

## API Endpoints

### Authentication Endpoints
```
POST /register          - User registration
POST /login             - User login
POST /logout            - User logout
POST /forgot-password   - Password reset request
POST /reset-password    - Password reset confirmation
```

### Dashboard API
```
GET /api/dashboard/stats           - Business statistics
GET /api/dashboard/charts          - Chart data for analytics
GET /api/dashboard/recent-activity - Recent business activity
GET /api/dashboard/notifications   - System notifications
```

### POS Endpoints
```
GET /pos/sales          - Sales interface
POST /pos/sales/process - Process new sale
GET /pos/products       - Product management
GET /pos/customers      - Customer management
GET /pos/reports        - Business reports
```

### M-Pesa Endpoints
```
POST /license/payment/initiate - Initiate license payment
POST /mpesa/callback          - M-Pesa payment callback
GET /license/status           - License status check
```

## Authentication & Authorization

### User Roles
1. **Super Admin**
   - Global system access
   - Business approval and management
   - System-wide analytics
   - User management across all businesses

2. **Business Owner**
   - Full access to their business data
   - Staff management
   - Business settings
   - Financial reports

3. **Cashier**
   - Sales processing
   - Customer management
   - Limited inventory access
   - Basic reporting

### Role-Based Decorators
```python
@require_role(['super_admin'])
def admin_only_function():
    pass

@require_business_license
def licensed_business_function():
    pass

@require_same_business
def business_isolated_function():
    pass
```

## M-Pesa Integration

### STK Push Flow
1. User initiates payment
2. System validates business license status
3. STK Push request sent to M-Pesa API
4. User receives payment prompt on phone
5. Payment confirmation via callback
6. License activation or sale completion

### Configuration
```python
class MpesaService:
    def __init__(self):
        self.base_url = "https://sandbox.safaricom.co.ke"  # Sandbox
        # self.base_url = "https://api.safaricom.co.ke"    # Production
        
    def initiate_stk_push(self, phone_number, amount, reference_id):
        # Implementation details in mpesa.py
```

### Callback Handling
```python
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    callback_data = request.get_json()
    result = mpesa_service.process_callback(callback_data)
    return jsonify(result)
```

## Testing

### Unit Tests
```bash
# Run unit tests
python -m pytest tests/unit/

# Run with coverage
python -m pytest tests/unit/ --cov=app --cov-report=html
```

### Integration Tests
```bash
# Test M-Pesa integration
python -m pytest tests/integration/test_mpesa.py

# Test API endpoints
python -m pytest tests/integration/test_api.py
```

### Manual Testing Checklist
- [ ] User registration and login
- [ ] License payment flow
- [ ] Sales processing
- [ ] Inventory management
- [ ] Report generation
- [ ] Email notifications
- [ ] Role-based access control

## Code Structure

```
comolor-pos/
├── app.py              # Flask application factory
├── main.py             # Application entry point
├── models.py           # Database models
├── routes.py           # URL routes and views
├── auth.py             # Authentication utilities
├── mpesa.py            # M-Pesa integration
├── email_service.py    # Email functionality
├── scheduler.py        # Background tasks
├── utils.py            # Utility functions
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── auth/
│   ├── dashboard/
│   ├── pos/
│   ├── legal/
│   └── emails/
└── docs/
    ├── DEVELOPER_GUIDE.md
    ├── DEPLOYMENT_GUIDE.md
    └── DATABASE_GUIDE.md
```

### Code Standards
- Follow PEP 8 for Python code style
- Use meaningful variable and function names
- Document complex functions with docstrings
- Implement proper error handling
- Use type hints where appropriate

### Database Migrations
```python
# When adding new models or fields
from app import app, db

with app.app_context():
    db.create_all()  # Creates new tables/columns
```

## Contributing

### Development Workflow
1. Create feature branch from main
2. Implement changes with tests
3. Run test suite
4. Update documentation
5. Submit pull request
6. Code review and merge

### Git Commit Convention
```
feat: add new feature
fix: bug fix
docs: documentation changes
style: code style changes
refactor: code refactoring
test: test additions/changes
chore: maintenance tasks
```

### Code Review Checklist
- [ ] Code follows project standards
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] Security considerations reviewed
- [ ] Performance impact assessed
- [ ] Database migrations tested

## Troubleshooting

### Common Issues
1. **Database Connection Errors**
   - Check DATABASE_URL format
   - Verify PostgreSQL service is running
   - Check user permissions

2. **M-Pesa Integration Issues**
   - Verify API credentials
   - Check sandbox vs production URLs
   - Review callback URL configuration

3. **Email Service Problems**
   - Confirm SMTP settings
   - Check app password for Gmail
   - Verify firewall settings

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Flask debug mode (development only)
app.debug = True
```

## Performance Optimization

### Database Optimization
- Use database indexes on frequently queried columns
- Implement query pagination for large datasets
- Use database connection pooling
- Regular VACUUM and ANALYZE operations

### Caching Strategies
- Session-based caching for user data
- Query result caching for reports
- Static asset caching
- Redis integration for advanced caching

### Monitoring
- Application performance monitoring
- Database query performance
- Error tracking and logging
- User activity analytics

---

For deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
For database details, see [DATABASE_GUIDE.md](DATABASE_GUIDE.md)