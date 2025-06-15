# Comolor POS - Deployment Guide

## Table of Contents
1. [Deployment Overview](#deployment-overview)
2. [Replit Deployment](#replit-deployment)
3. [Alternative Cloud Deployment](#alternative-cloud-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [M-Pesa Configuration](#m-pesa-configuration)
7. [Email Service Setup](#email-service-setup)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

## Deployment Overview

Comolor POS is designed for cloud deployment with PostgreSQL database support. The application is currently running on Replit with full functionality, including multi-tenant architecture and M-Pesa integration.

### Deployment Requirements
- PostgreSQL database (12+)
- Python 3.11+ runtime
- WSGI server (Gunicorn)
- HTTPS support
- Environment variable management

## Replit Deployment

### Current Status
✅ **Successfully Deployed**: The application is currently running on Replit with full functionality.

### Key Components Set Up
- **Database**: PostgreSQL database configured and operational
- **Session Management**: Secure session secret configured via environment variables
- **Multi-tenant Architecture**: Full data isolation between businesses implemented
- **Background Tasks**: APScheduler configured for license monitoring
- **Payment Integration**: M-Pesa API integration ready (requires API credentials)
- **Email Service**: Email notifications configured (requires SMTP credentials)

### Required Environment Variables
```bash
# Essential (Already Configured)
DATABASE_URL=postgresql://...
SESSION_SECRET=your_secure_secret_key

# Optional (For Full Functionality)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=noreply@yourcompany.com

# M-Pesa Integration (For Payment Processing)
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=your_shortcode
DEVELOPER_TILL_NUMBER=your_till_number
```

### Accessing Your Application
- Your POS system is accessible at your Replit URL
- Admin can register new businesses and manage the system
- Each business operates independently with secure data isolation

## Alternative Cloud Deployment

For deployment to other platforms like Render.com, Heroku, or DigitalOcean:

### Step 1: Repository Setup
1. Push your code to GitHub/GitLab
2. Ensure all files are committed including:
   - `pyproject.toml` (Python dependencies)
   - `main.py` (application entry point)
   - All Python modules and templates

### Step 2: Platform-Specific Configuration

#### Render.com
```yaml
Name: comolor-pos
Environment: Python 3
Region: Choose closest to your users
Branch: main
Build Command: pip install -r requirements.txt
Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 2 main:app
```

#### Heroku
```bash
# Procfile
web: gunicorn --bind 0.0.0.0:$PORT main:app
```

### Step 3: Database Setup
1. Create PostgreSQL database on your chosen platform
2. Configure database:
   - Name: `comolor-pos-db`
   - Database: `comolor_pos`
   - User: `comolor_user`
   - Region: Same as web service

3. Note the connection details provided by Render

### Step 4: Environment Variables
In your Render web service settings, add these environment variables:

```bash
# Database (automatically provided by Render PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# Session Security
SESSION_SECRET=your-secure-random-string-min-32-chars

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
MAIL_PASSWORD=your-gmail-app-password

# Application Settings
FLASK_ENV=production
```

## Environment Configuration

### Required Environment Variables

#### Database Configuration
```bash
DATABASE_URL=postgresql://username:password@host:port/database_name
```

#### Security Settings
```bash
SESSION_SECRET=your-super-secure-session-secret-key
```
*Generate using: `python -c "import secrets; print(secrets.token_hex(32))"`*

#### M-Pesa API Configuration
```bash
MPESA_CONSUMER_KEY=your_consumer_key_from_daraja
MPESA_CONSUMER_SECRET=your_consumer_secret_from_daraja
MPESA_PASSKEY=your_passkey_from_daraja
MPESA_SHORTCODE=your_business_shortcode
DEVELOPER_TILL_NUMBER=your_till_number_for_license_payments
```

#### Email Service Configuration
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_business_email@gmail.com
MAIL_PASSWORD=your_gmail_app_password
```

### Optional Environment Variables
```bash
FLASK_ENV=production
DEBUG=False
MAX_CONTENT_LENGTH=16777216  # 16MB file upload limit
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
```

## Database Setup

### Automatic Table Creation
The application automatically creates database tables on startup:

```python
# In app.py
with app.app_context():
    import models
    db.create_all()
```

### Manual Database Initialization
If needed, you can manually initialize the database:

```bash
# Connect to your database
psql $DATABASE_URL

# Or using Python
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"
```

### Database Migrations
For schema updates, use the following approach:

1. **Add new columns/tables** in `models.py`
2. **Deploy the application** - new tables/columns are created automatically
3. **For data migrations**, create a script:

```python
# migration_script.py
from app import app, db
from models import User, Business

with app.app_context():
    # Example: Update existing data
    businesses = Business.query.all()
    for business in businesses:
        if not business.subscription_plan:
            business.subscription_plan = 'monthly'
    
    db.session.commit()
    print("Migration completed")
```

## M-Pesa Configuration

### Daraja API Setup
1. **Register at Safaricom Daraja**
   - Visit [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
   - Create account and verify

2. **Create Application**
   - Go to "My Apps" → "Add a new app"
   - Select "Lipa Na M-Pesa Online"
   - Fill in application details

3. **Get Credentials**
   - Consumer Key
   - Consumer Secret
   - Passkey (for STK Push)

### Sandbox vs Production
```python
# In mpesa.py
def initialize_config(self):
    # Sandbox for testing
    if current_app.debug:
        self.base_url = "https://sandbox.safaricom.co.ke"
    else:
        # Production
        self.base_url = "https://api.safaricom.co.ke"
```

### Callback URL Configuration
Set your callback URL in Daraja console:
```
Production: https://your-domain.com/mpesa/callback
Sandbox: https://your-render-app.onrender.com/mpesa/callback
```

## Email Service Setup

### Gmail Configuration
1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification
   - App passwords → Generate new password
   - Use this password in `MAIL_PASSWORD`

### Alternative Email Providers

#### SendGrid
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=your_sendgrid_api_key
```

#### Mailgun
```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USERNAME=postmaster@your-domain.mailgun.org
MAIL_PASSWORD=your_mailgun_password
```

## Domain and SSL

### Custom Domain Setup
1. **In Render Dashboard**:
   - Go to your service → Settings
   - Add custom domain
   - Follow DNS configuration instructions

2. **DNS Configuration**:
   ```
   Type: CNAME
   Name: www (or your subdomain)
   Value: your-app.onrender.com
   ```

### SSL Certificate
Render automatically provides SSL certificates for:
- `.onrender.com` subdomains
- Custom domains (Let's Encrypt)

## Monitoring and Maintenance

### Application Monitoring
1. **Render Dashboard**:
   - Monitor service health
   - View application logs
   - Track resource usage

2. **Database Monitoring**:
   - Connection count
   - Query performance
   - Storage usage

### Log Management
```python
# In app.py - Configure logging
import logging

if not app.debug:
    # Production logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )
```

### Backup Strategy
1. **Database Backups**:
   - Render PostgreSQL includes automatic backups
   - Consider additional backup solutions for critical data

2. **Application Backups**:
   - Code is backed up in version control
   - Environment variables documented securely

### Performance Optimization
```python
# gunicorn.conf.py
bind = "0.0.0.0:10000"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
```

## Troubleshooting

### Common Deployment Issues

#### 1. Build Failures
```bash
# Check requirements.txt
pip freeze > requirements.txt

# Verify Python version
python --version

# Check for missing dependencies
pip install -r requirements.txt
```

#### 2. Database Connection Issues
```bash
# Test database connection
python -c "
import os
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('Database connection successful')
"
```

#### 3. Environment Variable Issues
```bash
# Verify environment variables are set
python -c "
import os
required_vars = ['DATABASE_URL', 'SESSION_SECRET', 'MPESA_CONSUMER_KEY']
for var in required_vars:
    if var in os.environ:
        print(f'{var}: Set')
    else:
        print(f'{var}: MISSING')
"
```

#### 4. M-Pesa Integration Issues
- Verify callback URL is accessible
- Check API credentials are correct
- Ensure phone number format is correct (254XXXXXXXXX)
- Test with sandbox first

#### 5. Email Service Issues
- Verify SMTP settings
- Check app password for Gmail
- Test email sending manually

### Debug Mode
For debugging in production (temporary):
```python
# In app.py
import os
if os.environ.get('DEBUG_MODE') == 'true':
    app.debug = True
    logging.basicConfig(level=logging.DEBUG)
```

### Health Check Endpoint
Add a health check for monitoring:
```python
@app.route('/health')
def health_check():
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503
```

### Rollback Strategy
1. **Keep previous deployment branch**
2. **Test changes in staging environment**
3. **Monitor application after deployment**
4. **Have rollback plan ready**

```bash
# Quick rollback
git revert <commit-hash>
git push origin main
```

## Security Considerations

### Production Security Checklist
- [ ] All secrets stored as environment variables
- [ ] HTTPS enforced for all endpoints
- [ ] Database connections encrypted
- [ ] Session cookies secure and HTTP-only
- [ ] Input validation on all forms
- [ ] SQL injection protection (SQLAlchemy ORM)
- [ ] CSRF protection enabled
- [ ] Rate limiting implemented
- [ ] Error messages don't leak sensitive information

### Regular Maintenance
- Update dependencies regularly
- Monitor security advisories
- Review access logs
- Update API keys periodically
- Monitor for unusual activity

---

For development setup, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
For database details, see [DATABASE_GUIDE.md](DATABASE_GUIDE.md)