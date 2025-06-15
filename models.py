from datetime import datetime, timedelta
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum

class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    BUSINESS_OWNER = "business_owner"
    CASHIER = "cashier"

class BusinessStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.BUSINESS_OWNER)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = db.relationship('Business', backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN
    
    def is_business_owner(self):
        return self.role == UserRole.BUSINESS_OWNER
    
    def is_cashier(self):
        return self.role == UserRole.CASHIER

class Business(db.Model):
    __tablename__ = 'businesses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    till_number = db.Column(db.String(20), nullable=True)
    currency = db.Column(db.String(3), default='KES')
    tax_rate = db.Column(db.Float, default=0.0)
    status = db.Column(db.Enum(BusinessStatus), default=BusinessStatus.PENDING)
    license_expires_at = db.Column(db.DateTime, nullable=True)
    subscription_plan = db.Column(db.String(50), default='monthly')  # monthly, yearly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_license_active(self):
        if not self.license_expires_at:
            return False
        return self.license_expires_at > datetime.utcnow()
    
    def days_until_expiry(self):
        if not self.license_expires_at:
            return 0
        delta = self.license_expires_at - datetime.utcnow()
        return max(0, delta.days)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sku = db.Column(db.String(100), nullable=True)
    barcode = db.Column(db.String(100), nullable=True)
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    selling_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=5)
    category = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = db.relationship('Business', backref='products')
    
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.Text, nullable=True)
    credit_limit = db.Column(db.Float, default=0.0)
    current_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = db.relationship('Business', backref='customers')

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    sale_number = db.Column(db.String(50), unique=True, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, mpesa
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    mpesa_transaction_id = db.Column(db.String(100), nullable=True)
    receipt_printed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    business = db.relationship('Business', backref='sales')
    user = db.relationship('User', backref='sales')
    customer = db.relationship('Customer', backref='sales')
    
    def generate_sale_number(self):
        import random
        import string
        prefix = f"S{datetime.utcnow().strftime('%Y%m%d')}"
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}{suffix}"

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    sale = db.relationship('Sale', backref='items')
    product = db.relationship('Product', backref='sale_items')

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    payment_type = db.Column(db.String(20), nullable=False)  # license, sale
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    mpesa_transaction_id = db.Column(db.String(100), nullable=True)
    mpesa_receipt_number = db.Column(db.String(100), nullable=True)
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    business = db.relationship('Business', backref='payments')
    user = db.relationship('User', backref='payments')
    sale = db.relationship('Sale', backref='payment_records')

class StockMovement(db.Model):
    __tablename__ = 'stock_movements'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # in, out, adjustment
    quantity = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)  # sale_id for sales
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    business = db.relationship('Business', backref='stock_movements')
    product = db.relationship('Product', backref='stock_movements')
    user = db.relationship('User', backref='stock_movements')

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    business = db.relationship('Business', backref='activity_logs')
    user = db.relationship('User', backref='activity_logs')
