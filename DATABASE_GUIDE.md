# Comolor POS - Database Guide

## Table of Contents
1. [Database Overview](#database-overview)
2. [Schema Design](#schema-design)
3. [Multi-Tenant Architecture](#multi-tenant-architecture)
4. [Table Specifications](#table-specifications)
5. [Relationships](#relationships)
6. [Indexes and Performance](#indexes-and-performance)
7. [Data Migration](#data-migration)
8. [Backup and Recovery](#backup-and-recovery)
9. [Security](#security)

## Database Overview

Comolor POS uses PostgreSQL as its primary database with SQLAlchemy ORM for Python integration. The database implements a multi-tenant architecture where multiple businesses share the same database infrastructure while maintaining complete data isolation.

### Key Features
- Multi-tenant data isolation using `business_id` foreign keys
- ACID compliance for financial transactions
- Automated timestamp tracking for audit trails
- Enum types for consistent data validation
- Foreign key constraints for data integrity

### Database Configuration
```python
# Database connection settings
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
```

## Schema Design

### Core Entities
1. **Users** - System users with role-based access
2. **Businesses** - Tenant organizations
3. **Products** - Inventory items
4. **Customers** - Business clients
5. **Sales** - Transaction records
6. **Payments** - Payment processing records
7. **Activity Logs** - Audit trail

### Entity Relationship Diagram
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Users     │────│ Businesses  │────│  Products   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Sales    │────│  Customers  │    │ Sale Items  │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │
       ▼
┌─────────────┐
│  Payments   │
│             │
└─────────────┘
```

## Multi-Tenant Architecture

### Tenant Isolation Strategy
Each business operates as an isolated tenant within the shared database:

```python
# Business isolation through foreign keys
class Product(db.Model):
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    
# Queries automatically filter by business
products = Product.query.filter_by(business_id=current_user.business_id).all()
```

### Super Admin Access
Super administrators can access cross-tenant data:

```python
# Super admin can query across all businesses
if current_user.is_super_admin():
    all_sales = Sale.query.all()  # Cross-tenant access
else:
    business_sales = Sale.query.filter_by(business_id=current_user.business_id).all()
```

## Table Specifications

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    phone VARCHAR(15),
    role user_role NOT NULL DEFAULT 'business_owner',
    business_id INTEGER REFERENCES businesses(id),
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    reset_token VARCHAR(100),
    reset_token_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Businesses Table
```sql
CREATE TABLE businesses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    business_type VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(15),
    address TEXT,
    logo_url VARCHAR(500),
    till_number VARCHAR(20),
    currency VARCHAR(3) DEFAULT 'KES',
    tax_rate FLOAT DEFAULT 0.0,
    status business_status DEFAULT 'pending',
    license_expires_at TIMESTAMP,
    subscription_plan VARCHAR(50) DEFAULT 'monthly',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Products Table
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    sku VARCHAR(100),
    barcode VARCHAR(100),
    cost_price FLOAT NOT NULL DEFAULT 0.0,
    selling_price FLOAT NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    min_stock_level INTEGER DEFAULT 5,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sales Table
```sql
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    customer_id INTEGER REFERENCES customers(id),
    sale_number VARCHAR(50) UNIQUE NOT NULL,
    subtotal FLOAT NOT NULL,
    tax_amount FLOAT DEFAULT 0.0,
    discount_amount FLOAT DEFAULT 0.0,
    total_amount FLOAT NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    payment_status payment_status DEFAULT 'pending',
    mpesa_transaction_id VARCHAR(100),
    receipt_printed BOOLEAN DEFAULT FALSE,
    notes TEXT,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sale Items Table
```sql
CREATE TABLE sale_items (
    id SERIAL PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity FLOAT NOT NULL,
    unit_price FLOAT NOT NULL,
    total_price FLOAT NOT NULL
);
```

### Customers Table
```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(120),
    phone VARCHAR(15),
    address TEXT,
    credit_limit FLOAT DEFAULT 0.0,
    current_balance FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Payments Table
```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    user_id INTEGER REFERENCES users(id),
    sale_id INTEGER REFERENCES sales(id),
    payment_type VARCHAR(20) NOT NULL,
    amount FLOAT NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    mpesa_transaction_id VARCHAR(100),
    mpesa_receipt_number VARCHAR(100),
    status payment_status DEFAULT 'pending',
    payment_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Stock Movements Table
```sql
CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    movement_type VARCHAR(20) NOT NULL,
    quantity FLOAT NOT NULL,
    reason VARCHAR(200),
    reference_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Activity Logs Table
```sql
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Enum Types
```sql
-- User roles
CREATE TYPE user_role AS ENUM ('super_admin', 'business_owner', 'cashier');

-- Business status
CREATE TYPE business_status AS ENUM ('pending', 'active', 'suspended', 'expired');

-- Payment status
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed');
```

## Relationships

### One-to-Many Relationships
```python
# Business → Users
business = db.relationship('Business', backref='users')

# Business → Products
business = db.relationship('Business', backref='products')

# Business → Sales
business = db.relationship('Business', backref='sales')

# Sale → Sale Items
sale = db.relationship('Sale', backref='items')
```

### Many-to-Many Relationships
```python
# Sales ↔ Products (through SaleItem)
# Implemented via intermediate table sale_items
```

### Foreign Key Constraints
```sql
-- Ensure data integrity
ALTER TABLE users ADD CONSTRAINT fk_users_business 
    FOREIGN KEY (business_id) REFERENCES businesses(id);

ALTER TABLE products ADD CONSTRAINT fk_products_business 
    FOREIGN KEY (business_id) REFERENCES businesses(id);

-- Cascade deletes where appropriate
ALTER TABLE sale_items ADD CONSTRAINT fk_sale_items_sale 
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE;
```

## Indexes and Performance

### Primary Indexes
```sql
-- Business isolation optimization
CREATE INDEX idx_products_business_id ON products(business_id);
CREATE INDEX idx_sales_business_id ON sales(business_id);
CREATE INDEX idx_customers_business_id ON customers(business_id);

-- Query optimization
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_payment_status ON sales(payment_status);
CREATE INDEX idx_products_active ON products(is_active);
CREATE INDEX idx_users_email ON users(email);

-- Composite indexes
CREATE INDEX idx_sales_business_date ON sales(business_id, sale_date);
CREATE INDEX idx_products_business_active ON products(business_id, is_active);
```

### Performance Monitoring
```sql
-- Query performance analysis
EXPLAIN ANALYZE SELECT * FROM sales 
WHERE business_id = 1 AND sale_date >= '2025-01-01';

-- Index usage statistics
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes;
```

## Data Migration

### Adding New Columns
```python
# Migration script example
from app import app, db

with app.app_context():
    # Add new column to existing table
    db.engine.execute('ALTER TABLE businesses ADD COLUMN logo_url VARCHAR(500);')
    
    # Update existing records if needed
    businesses = Business.query.all()
    for business in businesses:
        if not business.logo_url:
            business.logo_url = '/static/images/default-logo.png'
    
    db.session.commit()
    print("Migration completed successfully")
```

### Data Transformation
```python
# Example: Convert phone number format
with app.app_context():
    users = User.query.all()
    for user in users:
        if user.phone and user.phone.startswith('0'):
            user.phone = '254' + user.phone[1:]
    
    db.session.commit()
```

### Version Control for Schema
```python
# Track schema versions
class SchemaVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
```

## Backup and Recovery

### Automated Backups
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="comolor_pos_backup_$DATE.sql"

pg_dump $DATABASE_URL > $BACKUP_FILE
gzip $BACKUP_FILE

# Upload to cloud storage
aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/
```

### Point-in-Time Recovery
```bash
# Restore from backup
gunzip comolor_pos_backup_20250615_120000.sql.gz
psql $DATABASE_URL < comolor_pos_backup_20250615_120000.sql
```

### Data Export
```python
# Export business data
def export_business_data(business_id):
    with app.app_context():
        business = Business.query.get(business_id)
        data = {
            'business': business.to_dict(),
            'products': [p.to_dict() for p in business.products],
            'customers': [c.to_dict() for c in business.customers],
            'sales': [s.to_dict() for s in business.sales]
        }
        
        with open(f'business_{business_id}_export.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
```

## Security

### Access Control
```python
# Row-level security implementation
@require_same_business
def get_business_data():
    # Automatically filters by current user's business
    return Product.query.filter_by(business_id=current_user.business_id).all()
```

### Data Encryption
```python
# Sensitive data encryption
from werkzeug.security import generate_password_hash, check_password_hash

# Password hashing
user.password_hash = generate_password_hash(password)

# Verification
is_valid = check_password_hash(user.password_hash, password)
```

### SQL Injection Prevention
```python
# Always use parameterized queries
# GOOD - SQLAlchemy ORM automatically parameterizes
products = Product.query.filter(Product.name.like(f'%{search_term}%')).all()

# GOOD - Manual parameterization
result = db.session.execute(
    text("SELECT * FROM products WHERE name LIKE :search"),
    {"search": f"%{search_term}%"}
)

# BAD - Never do this
# query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
```

### Audit Trail
```python
# Track all data changes
def log_activity(business_id, user_id, action, details):
    log = ActivityLog(
        business_id=business_id,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    db.session.commit()
```

### Database Connection Security
```python
# Secure connection settings
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'echo': False,  # Disable SQL logging in production
    'connect_args': {
        'sslmode': 'require',  # Force SSL
        'application_name': 'comolor_pos'
    }
}
```

### Data Validation
```python
# Model-level validation
class Product(db.Model):
    selling_price = db.Column(db.Float, nullable=False)
    
    def __init__(self, **kwargs):
        super(Product, self).__init__(**kwargs)
        if self.selling_price < 0:
            raise ValueError("Selling price cannot be negative")
```

---

For development setup, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
For deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)