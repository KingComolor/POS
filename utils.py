import secrets
import string
from datetime import datetime
import hashlib

def generate_password_reset_token():
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)

def verify_password_reset_token(token):
    """Verify password reset token (basic implementation)"""
    # In a production environment, you might want to use JWT tokens
    # with expiration and proper verification
    return len(token) == 43  # URL-safe base64 tokens are 43 chars for 32 bytes

def generate_sale_number():
    """Generate a unique sale number"""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"SALE{timestamp}{random_suffix}"

def format_currency(amount, currency='KES'):
    """Format currency amount"""
    return f"{currency} {amount:,.2f}"

def format_phone_number(phone):
    """Format phone number for M-Pesa"""
    if phone.startswith('0'):
        return '254' + phone[1:]
    elif phone.startswith('+254'):
        return phone[1:]
    elif phone.startswith('254'):
        return phone
    else:
        return '254' + phone

def generate_reference_number():
    """Generate a unique reference number"""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"REF{timestamp}{random_suffix}"

def calculate_tax(amount, tax_rate):
    """Calculate tax amount"""
    return amount * (tax_rate / 100) if tax_rate else 0

def hash_string(text):
    """Create SHA256 hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()

def is_valid_email(email):
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone):
    """Basic phone number validation for Kenyan numbers"""
    import re
    # Remove spaces and special characters
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Check various Kenyan phone formats
    patterns = [
        r'^254[71][0-9]{8}$',  # +254 7xx xxx xxx or +254 1xx xxx xxx
        r'^0[71][0-9]{8}$',    # 07xx xxx xxx or 01xx xxx xxx
        r'^[71][0-9]{8}$'      # 7xx xxx xxx or 1xx xxx xxx
    ]
    
    return any(re.match(pattern, clean_phone) for pattern in patterns)

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-')

def paginate_query(query, page, per_page=20):
    """Helper function for pagination"""
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def get_business_stats(business_id):
    """Get basic business statistics"""
    from models import Sale, Product, Customer, PaymentStatus
    from sqlalchemy import func
    
    stats = {}
    
    # Total sales count and revenue
    sales_data = db.session.query(
        func.count(Sale.id).label('total_sales'),
        func.sum(Sale.total_amount).label('total_revenue')
    ).filter_by(business_id=business_id, payment_status=PaymentStatus.COMPLETED).first()
    
    stats['total_sales'] = sales_data.total_sales or 0
    stats['total_revenue'] = sales_data.total_revenue or 0
    
    # Product and customer counts
    stats['total_products'] = Product.query.filter_by(business_id=business_id).count()
    stats['total_customers'] = Customer.query.filter_by(business_id=business_id).count()
    
    # Low stock products
    stats['low_stock_products'] = Product.query.filter_by(business_id=business_id).filter(
        Product.stock_quantity <= Product.min_stock_level
    ).count()
    
    return stats

def get_date_range_sales(business_id, start_date, end_date):
    """Get sales data for a specific date range"""
    from models import Sale, PaymentStatus
    from sqlalchemy import func
    
    return db.session.query(
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total'),
        func.avg(Sale.total_amount).label('average')
    ).filter(
        Sale.business_id == business_id,
        Sale.payment_status == PaymentStatus.COMPLETED,
        Sale.sale_date >= start_date,
        Sale.sale_date <= end_date
    ).first()
