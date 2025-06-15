# Comolor POS

## Overview

Comolor POS is a multi-tenant, web-based Point of Sale system specifically designed for Kenyan businesses. Built with Python Flask, PostgreSQL, and modern web technologies, it provides a comprehensive solution for business management with integrated M-Pesa payments and automated licensing.

## System Architecture

### Backend Architecture
- **Framework**: Python Flask with SQLAlchemy ORM
- **Database**: PostgreSQL with multi-tenant design using business_id isolation
- **Authentication**: Flask-Login with role-based access control
- **Session Management**: Server-side sessions with secure cookie handling
- **API Structure**: RESTful endpoints with JSON responses
- **Background Tasks**: APScheduler for license monitoring and automated tasks

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 dark theme
- **CSS Framework**: Bootstrap 5 with custom Comolor styling
- **JavaScript**: Vanilla ES6+ with modular class-based components
- **Icons**: Font Awesome 6
- **Charts**: Chart.js for analytics and reporting
- **Responsive Design**: Mobile-first approach with progressive enhancement

### Multi-Tenant Design
- Business isolation through `business_id` foreign keys in all relevant tables
- Super admin can access all tenants while business users see only their data
- Shared infrastructure with tenant-aware queries and data access patterns

## Key Components

### User Management
- **User Roles**: Super Admin, Business Owner, Cashier with granular permissions
- **Authentication**: Secure password hashing with Werkzeug
- **Authorization**: Decorator-based role checking (`@require_role`, `@require_business_license`)
- **Password Reset**: Token-based reset system with email verification

### Business Management
- **Registration**: Multi-step business onboarding with terms acceptance
- **License System**: Monthly/yearly subscription model with automated expiry tracking
- **Business Settings**: Configurable business information, tax rates, and preferences
- **Staff Management**: Multi-user support with role assignment

### Point of Sale
- **Product Management**: Full CRUD operations with inventory tracking
- **Customer Management**: Customer database with purchase history
- **Sales Processing**: Real-time cart management with receipt generation
- **Payment Integration**: M-Pesa STK Push with transaction verification
- **Receipt System**: Printable thermal receipt templates

### Reporting & Analytics
- **Sales Reports**: Daily, weekly, monthly revenue analytics
- **Inventory Reports**: Stock levels, low stock alerts, movement tracking
- **Customer Analytics**: Purchase patterns and customer insights
- **Staff Performance**: Individual cashier sales tracking

## Data Flow

### User Registration Flow
1. User submits registration form with business details
2. System creates User and Business records
3. Email verification sent (optional)
4. User redirected to license payment
5. Upon payment success, business activated

### Sales Transaction Flow
1. Cashier selects products and adds to cart
2. Customer information captured (optional)
3. Payment method selected (M-Pesa/Cash)
4. For M-Pesa: STK Push initiated and status polled
5. Sale record created with line items
6. Receipt generated and inventory updated
7. Customer notification sent (if email provided)

### License Management Flow
1. Scheduler runs daily to check license expiry
2. Warning emails sent 5 days before expiry
3. Expired licenses automatically lock business access
4. Payment verification unlocks access and extends license
5. Admin can manually override license status

## External Dependencies

### Core Dependencies
- **Flask 3.1.1**: Web framework
- **SQLAlchemy 2.0.41**: Database ORM
- **PostgreSQL**: Primary database (psycopg2-binary driver)
- **Flask-Login 0.6.3**: User session management
- **Flask-Mail 0.10.0**: Email service integration
- **APScheduler 3.11.0**: Background task scheduling
- **Requests 2.32.4**: HTTP client for M-Pesa API
- **Gunicorn 23.0.0**: WSGI server for production

### Third-Party Integrations
- **M-Pesa Daraja API**: Payment processing with STK Push
- **SMTP Email Service**: Configurable email provider (Gmail default)
- **Bootstrap CDN**: Frontend styling framework
- **Font Awesome CDN**: Icon library
- **Chart.js CDN**: Analytics visualization

### Development Dependencies
- **Email-validator**: Email format validation
- **PyJWT**: JSON Web Token handling
- **Werkzeug**: Security utilities and development server

## Deployment Strategy

### Production Environment
- **Platform**: Replit with autoscale deployment
- **WSGI Server**: Gunicorn with multiple workers
- **Database**: PostgreSQL with connection pooling
- **Environment Variables**: Secure configuration management
- **SSL/TLS**: HTTPS enforcement with proxy headers

### Configuration Management
- Database URL and credentials via environment variables
- M-Pesa API credentials securely stored
- Email service configuration with fallback options
- Session secrets and security keys properly configured

### Scaling Considerations
- Multi-tenant database design supports horizontal scaling
- Background task scheduler can be moved to separate instances
- File uploads and static assets ready for CDN integration
- API endpoints designed for potential mobile app integration

## Changelog

- June 15, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.