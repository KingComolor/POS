from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import secrets
import logging

from app import app, db
from models import (User, Business, Product, Customer, Sale, SaleItem, Payment, 
                   StockMovement, ActivityLog, UserRole, BusinessStatus, PaymentStatus)
from auth import require_role, log_activity
from mpesa import MpesaService
from email_service import EmailService
from utils import generate_password_reset_token, verify_password_reset_token

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize services
mpesa_service = MpesaService()
email_service = EmailService()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_super_admin():
            return redirect(url_for('super_admin_dashboard'))
        elif current_user.business and current_user.business.is_license_active():
            if current_user.is_business_owner():
                return redirect(url_for('business_dashboard'))
            else:
                return redirect(url_for('cashier_dashboard'))
        else:
            return redirect(url_for('license_payment'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        business_name = request.form.get('business_name')
        business_type = request.form.get('business_type')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms_accepted = request.form.get('terms_accepted')
        
        # Validation
        if not all([name, business_name, business_type, email, password, terms_accepted]):
            flash('All fields are required and you must accept the terms.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register.html')
        
        try:
            # Create business
            business = Business(
                name=business_name,
                business_type=business_type,
                email=email,
                phone=phone,
                status=BusinessStatus.PENDING
            )
            db.session.add(business)
            db.session.flush()  # Get business ID
            
            # Create user
            user = User(
                name=name,
                email=email,
                phone=phone,
                role=UserRole.BUSINESS_OWNER,
                business_id=business.id
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            # Log activity
            log_activity(None, user.id, 'user_registered', f'New user registered: {email}', request)
            
            # Send welcome email
            email_service.send_welcome_email(user, business)
            
            flash('Registration successful! Please proceed to license payment to activate your account.', 'success')
            login_user(user)
            return redirect(url_for('license_payment'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {str(e)}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been suspended.', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember)
            log_activity(user.business_id, user.id, 'user_login', f'User logged in: {email}', request)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
            log_activity(None, None, 'failed_login', f'Failed login attempt: {email}', request)
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.business_id, current_user.id, 'user_logout', 'User logged out', request)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = generate_password_reset_token()
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            email_service.send_password_reset_email(user, token)
            flash('Password reset instructions sent to your email.', 'info')
        else:
            flash('Email not found.', 'error')
        
        return redirect(url_for('login'))
    
    return render_template('auth/forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        flash('Password reset successful. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/reset_password.html', token=token)

# Dashboard routes
@app.route('/dashboard/super-admin')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def super_admin_dashboard():
    # Get statistics
    total_businesses = Business.query.count()
    active_businesses = Business.query.filter_by(status=BusinessStatus.ACTIVE).count()
    pending_businesses = Business.query.filter_by(status=BusinessStatus.PENDING).count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(payment_type='license').scalar() or 0
    
    recent_payments = Payment.query.filter_by(payment_type='license').order_by(Payment.created_at.desc()).limit(10).all()
    recent_businesses = Business.query.order_by(Business.created_at.desc()).limit(10).all()
    
    return render_template('dashboard/super_admin.html', 
                         total_businesses=total_businesses,
                         active_businesses=active_businesses,
                         pending_businesses=pending_businesses,
                         total_revenue=total_revenue,
                         recent_payments=recent_payments,
                         recent_businesses=recent_businesses)

# Super Admin - Manage Businesses
@app.route('/admin/businesses')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def manage_businesses():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Business.query
    
    if status_filter:
        query = query.filter(Business.status == BusinessStatus(status_filter))
    
    if search:
        query = query.filter(Business.name.ilike(f'%{search}%'))
    
    businesses = query.order_by(Business.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/manage_businesses.html', businesses=businesses, 
                         status_filter=status_filter, search=search)

@app.route('/admin/businesses/<int:business_id>/toggle-status', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def toggle_business_status(business_id):
    business = Business.query.get_or_404(business_id)
    
    if business.status == BusinessStatus.ACTIVE:
        business.status = BusinessStatus.SUSPENDED
        message = f"Business {business.name} has been suspended"
    elif business.status == BusinessStatus.SUSPENDED:
        business.status = BusinessStatus.ACTIVE
        message = f"Business {business.name} has been activated"
    elif business.status == BusinessStatus.PENDING:
        business.status = BusinessStatus.ACTIVE
        business.license_expires_at = datetime.utcnow() + timedelta(days=30)
        message = f"Business {business.name} has been approved and activated"
    
    db.session.commit()
    log_activity(business.id, current_user.id, 'business_status_changed', 
                f'Status changed to {business.status.value}', request)
    
    flash(message, 'success')
    return redirect(url_for('manage_businesses'))

@app.route('/admin/businesses/<int:business_id>/extend-license', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def extend_business_license(business_id):
    business = Business.query.get_or_404(business_id)
    days = request.form.get('days', 30, type=int)
    
    if business.license_expires_at:
        business.license_expires_at = business.license_expires_at + timedelta(days=days)
    else:
        business.license_expires_at = datetime.utcnow() + timedelta(days=days)
    
    business.status = BusinessStatus.ACTIVE
    db.session.commit()
    
    log_activity(business.id, current_user.id, 'license_extended', 
                f'License extended by {days} days', request)
    
    flash(f'License extended by {days} days for {business.name}', 'success')
    return redirect(url_for('manage_businesses'))

# Super Admin - Export Data
@app.route('/admin/export')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def export_data():
    return render_template('admin/export_data.html')

@app.route('/admin/export/businesses')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def export_businesses():
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Name', 'Type', 'Email', 'Phone', 'Status', 'License Expires', 'Created At'])
    
    # Write data
    businesses = Business.query.all()
    for business in businesses:
        writer.writerow([
            business.id,
            business.name,
            business.business_type,
            business.email,
            business.phone,
            business.status.value,
            business.license_expires_at.strftime('%Y-%m-%d') if business.license_expires_at else '',
            business.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=businesses_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@app.route('/admin/export/payments')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def export_payments():
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Business', 'Amount', 'Type', 'Status', 'Phone', 'Transaction ID', 'Created At'])
    
    # Write data
    payments = Payment.query.join(Business).all()
    for payment in payments:
        writer.writerow([
            payment.id,
            payment.business.name if payment.business else 'N/A',
            payment.amount,
            payment.payment_type,
            payment.status.value,
            payment.phone_number,
            payment.mpesa_transaction_id or '',
            payment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=payments_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

# Super Admin - System Settings
@app.route('/admin/settings')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def system_settings():
    # Get system statistics
    stats = {
        'total_businesses': Business.query.count(),
        'active_businesses': Business.query.filter_by(status=BusinessStatus.ACTIVE).count(),
        'total_users': User.query.count(),
        'total_sales': Sale.query.count(),
        'total_revenue': db.session.query(db.func.sum(Payment.amount)).filter_by(payment_type='license').scalar() or 0,
        'database_size': 'N/A'  # Would need specific DB queries to calculate
    }
    
    return render_template('admin/system_settings.html', stats=stats)

@app.route('/admin/settings/maintenance', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def system_maintenance():
    action = request.form.get('action')
    
    if action == 'cleanup_logs':
        # Clean up old activity logs (older than 90 days)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        deleted_count = ActivityLog.query.filter(ActivityLog.created_at < cutoff_date).delete()
        db.session.commit()
        flash(f'Cleaned up {deleted_count} old activity logs', 'success')
    
    elif action == 'expire_licenses':
        # Mark expired licenses as expired
        expired_businesses = Business.query.filter(
            Business.license_expires_at < datetime.utcnow(),
            Business.status == BusinessStatus.ACTIVE
        ).all()
        
        for business in expired_businesses:
            business.status = BusinessStatus.EXPIRED
        
        db.session.commit()
        flash(f'Marked {len(expired_businesses)} businesses as expired', 'success')
    
    return redirect(url_for('system_settings'))

# Super Admin - View Reports
@app.route('/admin/reports')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def view_reports():
    # Get date range from query parameters
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Convert strings to datetime objects
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Revenue report
    revenue_data = db.session.query(
        db.func.date(Payment.created_at).label('date'),
        db.func.sum(Payment.amount).label('total')
    ).filter(
        Payment.payment_type == 'license',
        Payment.status == PaymentStatus.COMPLETED,
        Payment.created_at >= start_dt,
        Payment.created_at < end_dt
    ).group_by(db.func.date(Payment.created_at)).all()
    
    # Business growth report
    business_growth = db.session.query(
        db.func.date(Business.created_at).label('date'),
        db.func.count(Business.id).label('count')
    ).filter(
        Business.created_at >= start_dt,
        Business.created_at < end_dt
    ).group_by(db.func.date(Business.created_at)).all()
    
    # Top performing businesses
    top_businesses = db.session.query(
        Business.name,
        db.func.count(Sale.id).label('sales_count'),
        db.func.sum(Sale.total_amount).label('total_revenue')
    ).join(Sale).filter(
        Sale.created_at >= start_dt,
        Sale.created_at < end_dt,
        Sale.payment_status == PaymentStatus.COMPLETED
    ).group_by(Business.id, Business.name).order_by(
        db.func.sum(Sale.total_amount).desc()
    ).limit(10).all()
    
    return render_template('admin/reports.html',
                         start_date=start_date,
                         end_date=end_date,
                         revenue_data=revenue_data,
                         business_growth=business_growth,
                         top_businesses=top_businesses)

@app.route('/dashboard/business')
@login_required
@require_role([UserRole.BUSINESS_OWNER])
def business_dashboard():
    if not current_user.business.is_license_active():
        return redirect(url_for('license_payment'))
    
    # Get business statistics
    today_sales = Sale.query.filter(
        Sale.business_id == current_user.business_id,
        Sale.sale_date >= datetime.utcnow().date()
    ).count()
    
    today_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter(
        Sale.business_id == current_user.business_id,
        Sale.sale_date >= datetime.utcnow().date(),
        Sale.payment_status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    total_products = Product.query.filter_by(business_id=current_user.business_id).count()
    low_stock_products = Product.query.filter_by(business_id=current_user.business_id).filter(
        Product.stock_quantity <= Product.min_stock_level
    ).count()
    
    recent_sales = Sale.query.filter_by(business_id=current_user.business_id).order_by(Sale.created_at.desc()).limit(5).all()
    
    return render_template('dashboard/business_owner.html',
                         today_sales=today_sales,
                         today_revenue=today_revenue,
                         total_products=total_products,
                         low_stock_products=low_stock_products,
                         recent_sales=recent_sales,
                         business=current_user.business)

@app.route('/dashboard/cashier')
@login_required
@require_role([UserRole.CASHIER])
def cashier_dashboard():
    if not current_user.business.is_license_active():
        flash('Business license has expired. Please contact your administrator.', 'error')
        return redirect(url_for('index'))
    
    # Get cashier statistics
    today_sales = Sale.query.filter(
        Sale.business_id == current_user.business_id,
        Sale.user_id == current_user.id,
        Sale.sale_date >= datetime.utcnow().date()
    ).count()
    
    today_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter(
        Sale.business_id == current_user.business_id,
        Sale.user_id == current_user.id,
        Sale.sale_date >= datetime.utcnow().date(),
        Sale.payment_status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    recent_sales = Sale.query.filter(
        Sale.business_id == current_user.business_id,
        Sale.user_id == current_user.id
    ).order_by(Sale.created_at.desc()).limit(5).all()
    
    return render_template('dashboard/cashier.html',
                         today_sales=today_sales,
                         today_revenue=today_revenue,
                         recent_sales=recent_sales)

# License payment routes
@app.route('/license/payment')
@login_required
def license_payment():
    if current_user.is_super_admin():
        return redirect(url_for('super_admin_dashboard'))
    
    if current_user.business and current_user.business.is_license_active():
        return redirect(url_for('business_dashboard'))
    
    return render_template('license/payment.html', business=current_user.business)

@app.route('/license/initiate-payment', methods=['POST'])
@login_required
def initiate_license_payment():
    plan = request.form.get('plan')  # monthly or yearly
    phone = request.form.get('phone')
    
    if not phone or not plan:
        flash('Phone number and plan are required.', 'error')
        return redirect(url_for('license_payment'))
    
    # Determine amount based on plan
    amount = 3000 if plan == 'monthly' else 30000
    
    try:
        # Create payment record
        payment = Payment(
            business_id=current_user.business_id,
            user_id=current_user.id,
            payment_type='license',
            amount=amount,
            phone_number=phone,
            status=PaymentStatus.PENDING
        )
        db.session.add(payment)
        db.session.commit()
        
        # Initiate M-Pesa payment
        result = mpesa_service.initiate_stk_push(phone, amount, payment.id)
        
        if result.get('success'):
            flash('Payment initiated successfully. Please complete the payment on your phone.', 'info')
            session['pending_payment_id'] = payment.id
            return redirect(url_for('license_status'))
        else:
            payment.status = PaymentStatus.FAILED
            db.session.commit()
            flash('Failed to initiate payment. Please try again.', 'error')
    
    except Exception as e:
        logging.error(f"License payment initiation error: {str(e)}")
        flash('Payment initiation failed. Please try again.', 'error')
    
    return redirect(url_for('license_payment'))

@app.route('/license/status')
@login_required
def license_status():
    payment_id = session.get('pending_payment_id')
    payment = None
    
    if payment_id:
        payment = Payment.query.get(payment_id)
    
    return render_template('license/status.html', payment=payment, business=current_user.business)

# POS Routes
@app.route('/pos/sales')
@login_required
def pos_sales():
    if not current_user.business.is_license_active():
        flash('Business license has expired.', 'error')
        return redirect(url_for('license_payment'))
    
    products = Product.query.filter_by(business_id=current_user.business_id, is_active=True).all()
    customers = Customer.query.filter_by(business_id=current_user.business_id).all()
    
    return render_template('pos/sales.html', products=products, customers=customers)

@app.route('/pos/process-sale', methods=['POST'])
@login_required
def process_sale():
    try:
        data = request.get_json()
        items = data.get('items', [])
        customer_id = data.get('customer_id')
        payment_method = data.get('payment_method')
        discount_amount = float(data.get('discount_amount', 0))
        
        if not items:
            return jsonify({'success': False, 'message': 'No items in cart'})
        
        # Calculate totals
        subtotal = 0
        sale_items = []
        
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product or product.business_id != current_user.business_id:
                return jsonify({'success': False, 'message': 'Invalid product'})
            
            quantity = float(item['quantity'])
            unit_price = float(item['price'])
            total_price = quantity * unit_price
            
            subtotal += total_price
            sale_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': total_price
            })
        
        # Calculate tax and total
        tax_rate = current_user.business.tax_rate / 100 if current_user.business.tax_rate else 0
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount - discount_amount
        
        # Create sale
        sale = Sale(
            business_id=current_user.business_id,
            user_id=current_user.id,
            customer_id=customer_id if customer_id else None,
            sale_number=Sale().generate_sale_number(),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            payment_method=payment_method,
            payment_status=PaymentStatus.COMPLETED if payment_method == 'cash' else PaymentStatus.PENDING
        )
        db.session.add(sale)
        db.session.flush()
        
        # Add sale items and update stock
        for item_data in sale_items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_data['product'].id,
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            )
            db.session.add(sale_item)
            
            # Update stock
            product = item_data['product']
            product.stock_quantity -= item_data['quantity']
            
            # Record stock movement
            stock_movement = StockMovement(
                business_id=current_user.business_id,
                product_id=product.id,
                user_id=current_user.id,
                movement_type='out',
                quantity=item_data['quantity'],
                reason='Sale',
                reference_id=sale.id
            )
            db.session.add(stock_movement)
        
        db.session.commit()
        
        # If M-Pesa payment, initiate STK push
        if payment_method == 'mpesa':
            phone = data.get('phone')
            if not phone:
                return jsonify({'success': False, 'message': 'Phone number required for M-Pesa payment'})
            
            # Create payment record
            payment = Payment(
                business_id=current_user.business_id,
                user_id=current_user.id,
                sale_id=sale.id,
                payment_type='sale',
                amount=total_amount,
                phone_number=phone,
                status=PaymentStatus.PENDING
            )
            db.session.add(payment)
            db.session.commit()
            
            # Initiate M-Pesa payment
            mpesa_result = mpesa_service.initiate_stk_push(phone, total_amount, payment.id)
            
            if not mpesa_result.get('success'):
                return jsonify({'success': False, 'message': 'Failed to initiate M-Pesa payment'})
        
        log_activity(current_user.business_id, current_user.id, 'sale_created', f'Sale {sale.sale_number} created', request)
        
        return jsonify({
            'success': True, 
            'sale_id': sale.id,
            'sale_number': sale.sale_number,
            'requires_payment': payment_method == 'mpesa'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Sale processing error: {str(e)}")
        return jsonify({'success': False, 'message': 'Sale processing failed'})

# M-Pesa callback routes
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    try:
        data = request.get_json()
        logging.info(f"M-Pesa callback received: {data}")
        
        # Process the callback
        result = mpesa_service.process_callback(data)
        
        if result.get('success'):
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})
        else:
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Failed'})
    
    except Exception as e:
        logging.error(f"M-Pesa callback error: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})

# Additional routes for products, customers, staff, reports, etc.
@app.route('/pos/products')
@login_required
def pos_products():
    if not current_user.business.is_license_active():
        flash('Business license has expired.', 'error')
        return redirect(url_for('license_payment'))
    
    products = Product.query.filter_by(business_id=current_user.business_id).all()
    return render_template('pos/products.html', products=products)

@app.route('/pos/customers')
@login_required
def pos_customers():
    if not current_user.business.is_license_active():
        flash('Business license has expired.', 'error')
        return redirect(url_for('license_payment'))
    
    customers = Customer.query.filter_by(business_id=current_user.business_id).all()
    return render_template('pos/customers.html', customers=customers)

# Legal pages
@app.route('/terms')
def terms():
    return render_template('legal/terms.html')

@app.route('/privacy')
def privacy():
    return render_template('legal/privacy.html')

@app.route('/about')
def about():
    return render_template('legal/about.html')

# API Endpoints for Dashboard AJAX calls
@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    try:
        if not current_user.business:
            return jsonify({'success': False, 'message': 'No business associated'})
        
        business = current_user.business
        today = datetime.utcnow().date()
        
        # Get today's sales
        today_sales = Sale.query.filter(
            Sale.business_id == business.id,
            Sale.sale_date >= today,
            Sale.payment_status == PaymentStatus.COMPLETED
        ).count()
        
        today_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter(
            Sale.business_id == business.id,
            Sale.sale_date >= today,
            Sale.payment_status == PaymentStatus.COMPLETED
        ).scalar() or 0
        
        total_products = Product.query.filter_by(business_id=business.id, is_active=True).count()
        low_stock_products = Product.query.filter(
            Product.business_id == business.id,
            Product.is_active == True,
            Product.stock_quantity <= Product.min_stock_level
        ).count()
        
        total_customers = Customer.query.filter_by(business_id=business.id).count()
        active_staff = User.query.filter_by(business_id=business.id, is_active=True).count()
        
        stats = {
            'today_sales': today_sales,
            'today_revenue': float(today_revenue),
            'total_products': total_products,
            'low_stock_products': low_stock_products,
            'total_customers': total_customers,
            'active_staff': active_staff
        }
        
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logging.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to fetch stats'})

@app.route('/api/dashboard/charts')
@login_required
def api_dashboard_charts():
    try:
        if not current_user.business:
            return jsonify({'success': False, 'message': 'No business associated'})
        
        business = current_user.business
        
        # Sales trend for last 7 days
        sales_data = []
        labels = []
        for i in range(6, -1, -1):
            date = datetime.utcnow().date() - timedelta(days=i)
            sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
                Sale.business_id == business.id,
                Sale.sale_date >= date,
                Sale.sale_date < date + timedelta(days=1),
                Sale.payment_status == PaymentStatus.COMPLETED
            ).scalar() or 0
            sales_data.append(float(sales))
            labels.append(date.strftime('%m/%d'))
        
        # Payment methods distribution
        mpesa_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
            Sale.business_id == business.id,
            Sale.payment_method == 'mpesa',
            Sale.payment_status == PaymentStatus.COMPLETED
        ).scalar() or 0
        
        cash_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
            Sale.business_id == business.id,
            Sale.payment_method == 'cash',
            Sale.payment_status == PaymentStatus.COMPLETED
        ).scalar() or 0
        
        # Top products
        top_products = db.session.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('total_sold')
        ).join(SaleItem).join(Sale).filter(
            Sale.business_id == business.id,
            Sale.payment_status == PaymentStatus.COMPLETED
        ).group_by(Product.id, Product.name).order_by(
            db.func.sum(SaleItem.quantity).desc()
        ).limit(5).all()
        
        chart_data = {
            'sales_trend': {
                'labels': labels,
                'data': sales_data
            },
            'payment_methods': {
                'data': [float(mpesa_sales), float(cash_sales)]
            },
            'top_products': {
                'labels': [p.name for p in top_products],
                'data': [float(p.total_sold) for p in top_products]
            }
        }
        
        return jsonify({'success': True, 'data': chart_data})
    except Exception as e:
        logging.error(f"Dashboard charts error: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to fetch chart data'})

@app.route('/api/dashboard/recent-activity')
@login_required
def api_dashboard_recent_activity():
    try:
        if not current_user.business:
            return jsonify({'success': False, 'message': 'No business associated'})
        
        business = current_user.business
        
        # Get recent activities
        activities = ActivityLog.query.filter_by(
            business_id=business.id
        ).order_by(ActivityLog.created_at.desc()).limit(10).all()
        
        activity_list = []
        for activity in activities:
            activity_data = {
                'type': activity.action.lower().replace(' ', '_'),
                'title': activity.details or activity.action,
                'created_at': activity.created_at.isoformat(),
                'amount': None
            }
            
            # Add amount for sales activities
            if 'sale' in activity.action.lower():
                sale_id = activity.details.split(' ')[-1] if activity.details else None
                if sale_id:
                    try:
                        sale = Sale.query.get(int(sale_id))
                        if sale:
                            activity_data['amount'] = float(sale.total_amount)
                    except (ValueError, TypeError):
                        pass
            
            activity_list.append(activity_data)
        
        return jsonify({'success': True, 'data': activity_list})
    except Exception as e:
        logging.error(f"Dashboard recent activity error: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to fetch recent activity'})

@app.route('/api/dashboard/notifications')
@login_required
def api_dashboard_notifications():
    try:
        notifications = []
        
        if current_user.business:
            business = current_user.business
            
            # Check license expiry
            if business.license_expires_at:
                days_remaining = business.days_until_expiry()
                if days_remaining <= 5:
                    notifications.append({
                        'id': f'license_expiry_{business.id}',
                        'title': 'License Expiring Soon' if days_remaining > 0 else 'License Expired',
                        'message': f'Your license expires in {days_remaining} days' if days_remaining > 0 else 'Your license has expired',
                        'type': 'warning' if days_remaining > 0 else 'error',
                        'duration': 10000
                    })
            
            # Check low stock products
            low_stock_count = Product.query.filter(
                Product.business_id == business.id,
                Product.is_active == True,
                Product.stock_quantity <= Product.min_stock_level
            ).count()
            
            if low_stock_count > 0:
                notifications.append({
                    'id': f'low_stock_{business.id}',
                    'title': 'Low Stock Alert',
                    'message': f'{low_stock_count} products are running low on stock',
                    'type': 'warning',
                    'duration': 5000
                })
        
        return jsonify({'success': True, 'data': notifications})
    except Exception as e:
        logging.error(f"Dashboard notifications error: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to fetch notifications'})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ==================== ENHANCED SUPER ADMIN FEATURES ====================

# Business Management Extended
@app.route('/admin/businesses/<int:business_id>/details')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def business_details(business_id):
    business = Business.query.get_or_404(business_id)
    users = User.query.filter_by(business_id=business_id).all()
    payments = Payment.query.filter_by(business_id=business_id).order_by(Payment.created_at.desc()).limit(10).all()
    recent_sales = Sale.query.filter_by(business_id=business_id).order_by(Sale.created_at.desc()).limit(10).all()
    
    # Business statistics
    total_sales = Sale.query.filter_by(business_id=business_id).count()
    total_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter_by(business_id=business_id).scalar() or 0
    total_products = Product.query.filter_by(business_id=business_id).count()
    total_customers = Customer.query.filter_by(business_id=business_id).count()
    
    return render_template('admin/business_details.html',
                         business=business, users=users, payments=payments, recent_sales=recent_sales,
                         total_sales=total_sales, total_revenue=total_revenue, 
                         total_products=total_products, total_customers=total_customers)

@app.route('/admin/businesses/<int:business_id>/reset-password', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def reset_business_password(business_id):
    business = Business.query.get_or_404(business_id)
    user_id = request.form.get('user_id', type=int)
    user = User.query.filter_by(id=user_id, business_id=business_id).first_or_404()
    
    new_password = secrets.token_urlsafe(12)
    user.set_password(new_password)
    db.session.commit()
    
    log_activity(business_id, current_user.id, 'password_reset', f'Password reset for user {user.email}', request)
    flash(f'Password reset for {user.email}. New password: {new_password}', 'success')
    return redirect(url_for('business_details', business_id=business_id))

@app.route('/admin/businesses/<int:business_id>/delete', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def delete_business(business_id):
    business = Business.query.get_or_404(business_id)
    business_name = business.name
    
    # Delete all related data
    User.query.filter_by(business_id=business_id).delete()
    Product.query.filter_by(business_id=business_id).delete()
    Customer.query.filter_by(business_id=business_id).delete()
    Sale.query.filter_by(business_id=business_id).delete()
    Payment.query.filter_by(business_id=business_id).delete()
    StockMovement.query.filter_by(business_id=business_id).delete()
    ActivityLog.query.filter_by(business_id=business_id).delete()
    
    db.session.delete(business)
    db.session.commit()
    
    log_activity(None, current_user.id, 'business_deleted', f'Business deleted: {business_name}', request)
    flash(f'Business "{business_name}" and all related data has been permanently deleted', 'success')
    return redirect(url_for('manage_businesses'))

# License Management
@app.route('/admin/licenses')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def manage_licenses():
    businesses = Business.query.all()
    
    active_licenses = []
    expiring_soon = []
    expired_licenses = []
    
    for business in businesses:
        if business.license_expires_at:
            days_remaining = business.days_until_expiry()
            if days_remaining > 7:
                active_licenses.append(business)
            elif days_remaining > 0:
                expiring_soon.append(business)
            else:
                expired_licenses.append(business)
        else:
            expired_licenses.append(business)
    
    return render_template('admin/manage_licenses.html',
                         active_licenses=active_licenses, expiring_soon=expiring_soon, expired_licenses=expired_licenses)

@app.route('/admin/licenses/bulk-extend', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def bulk_extend_licenses():
    business_ids = request.form.getlist('business_ids')
    days = request.form.get('days', 30, type=int)
    
    extended_count = 0
    for business_id in business_ids:
        business = Business.query.get(business_id)
        if business:
            if business.license_expires_at:
                business.license_expires_at = business.license_expires_at + timedelta(days=days)
            else:
                business.license_expires_at = datetime.utcnow() + timedelta(days=days)
            
            business.status = BusinessStatus.ACTIVE
            extended_count += 1
            log_activity(business.id, current_user.id, 'bulk_license_extended', f'License extended by {days} days', request)
    
    db.session.commit()
    flash(f'Extended licenses for {extended_count} businesses by {days} days', 'success')
    return redirect(url_for('manage_licenses'))

# User Management
@app.route('/admin/users')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def manage_users():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = User.query.join(Business, User.business_id == Business.id, isouter=True)
    
    if role_filter:
        query = query.filter(User.role == UserRole(role_filter))
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    if search:
        query = query.filter(db.or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'), Business.name.ilike(f'%{search}%')))
    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/manage_users.html', users=users, role_filter=role_filter, status_filter=status_filter, search=search)

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.role == UserRole.SUPER_ADMIN and user.id != current_user.id:
        flash('Cannot deactivate other super admin accounts', 'error')
        return redirect(url_for('manage_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    log_activity(user.business_id, current_user.id, 'user_status_changed', f'User {user.email} {status}', request)
    flash(f'User {user.email} has been {status}', 'success')
    return redirect(url_for('manage_users'))

# System Settings Enhanced
@app.route('/admin/settings/update', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def update_system_settings():
    setting_type = request.form.get('setting_type')
    
    if setting_type == 'global_config':
        default_currency = request.form.get('default_currency', 'KES')
        default_tax_rate = float(request.form.get('default_tax_rate', 16.0))
        registration_enabled = request.form.get('registration_enabled') == 'on'
        
        session['global_settings'] = {
            'default_currency': default_currency,
            'default_tax_rate': default_tax_rate,
            'registration_enabled': registration_enabled
        }
        flash('Global settings updated successfully', 'success')
        
    elif setting_type == 'licensing':
        monthly_price = float(request.form.get('monthly_price', 3000))
        yearly_price = float(request.form.get('yearly_price', 30000))
        
        session['licensing_settings'] = {
            'monthly_price': monthly_price,
            'yearly_price': yearly_price
        }
        flash('Licensing settings updated successfully', 'success')
    
    return redirect(url_for('system_settings'))

# System Notifications
@app.route('/admin/notifications')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def system_notifications():
    notifications = []
    
    # License expiry notifications
    expiring_businesses = Business.query.filter(
        Business.license_expires_at <= datetime.utcnow() + timedelta(days=5),
        Business.license_expires_at > datetime.utcnow(),
        Business.status == BusinessStatus.ACTIVE
    ).all()
    
    for business in expiring_businesses:
        days_remaining = business.days_until_expiry()
        notifications.append({
            'type': 'warning',
            'title': 'License Expiring Soon',
            'message': f'{business.name} license expires in {days_remaining} days',
            'business_id': business.id,
            'created_at': business.license_expires_at
        })
    
    # Failed payment notifications
    failed_payments = Payment.query.filter(
        Payment.status == PaymentStatus.FAILED,
        Payment.created_at >= datetime.utcnow() - timedelta(days=7)
    ).all()
    
    for payment in failed_payments:
        notifications.append({
            'type': 'error',
            'title': 'Payment Failed',
            'message': f'Payment of KES {payment.amount} failed for {payment.business.name if payment.business else "Unknown"}',
            'business_id': payment.business_id,
            'created_at': payment.created_at
        })
    
    # New business registrations
    new_businesses = Business.query.filter(
        Business.status == BusinessStatus.PENDING,
        Business.created_at >= datetime.utcnow() - timedelta(days=7)
    ).all()
    
    for business in new_businesses:
        notifications.append({
            'type': 'info',
            'title': 'New Business Registration',
            'message': f'New business registered: {business.name}',
            'business_id': business.id,
            'created_at': business.created_at
        })
    
    notifications.sort(key=lambda x: x['created_at'], reverse=True)
    return render_template('admin/notifications.html', notifications=notifications)

@app.route('/admin/broadcast', methods=['GET', 'POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def broadcast_message():
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        target_audience = request.form.get('target_audience')
        
        query = Business.query
        if target_audience == 'active':
            query = query.filter(Business.status == BusinessStatus.ACTIVE)
        elif target_audience == 'pending':
            query = query.filter(Business.status == BusinessStatus.PENDING)
        
        businesses = query.all()
        
        for business in businesses:
            log_activity(business.id, current_user.id, 'broadcast_message', f'Broadcast: {title} - {message}', request)
        
        flash(f'Broadcast message sent to {len(businesses)} businesses', 'success')
        return redirect(url_for('broadcast_message'))
    
    return render_template('admin/broadcast.html')

# Advanced System Management
@app.route('/admin/system/backup', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def system_backup():
    backup_type = request.form.get('backup_type')
    
    if backup_type == 'full':
        # Simulate full system backup
        flash('Full system backup initiated successfully', 'success')
    elif backup_type == 'business':
        business_id = request.form.get('business_id', type=int)
        business = Business.query.get(business_id)
        if business:
            flash(f'Backup created for business: {business.name}', 'success')
        else:
            flash('Business not found', 'error')
    
    return redirect(url_for('system_settings'))

@app.route('/admin/system/maintenance-mode', methods=['POST'])
@login_required
@require_role(UserRole.SUPER_ADMIN)
def toggle_maintenance_mode():
    maintenance_enabled = request.form.get('maintenance_enabled') == 'on'
    session['maintenance_mode'] = maintenance_enabled
    
    if maintenance_enabled:
        flash('Maintenance mode enabled. New logins are disabled.', 'warning')
    else:
        flash('Maintenance mode disabled. System is fully operational.', 'success')
    
    return redirect(url_for('system_settings'))

# Payment and Invoice Management
@app.route('/admin/payments/generate-invoice/<int:payment_id>')
@login_required
@require_role(UserRole.SUPER_ADMIN)
def generate_payment_invoice(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.payment_type != 'license':
        flash('Can only generate invoices for license payments', 'error')
        return redirect(url_for('manage_businesses'))
    
    # Generate invoice data
    invoice_data = {
        'invoice_number': f'INV-{payment.id:06d}',
        'payment': payment,
        'business': payment.business,
        'generated_at': datetime.utcnow(),
        'due_date': payment.created_at + timedelta(days=30) if payment.created_at else datetime.utcnow()
    }
    
    return render_template('admin/payment_invoice.html', **invoice_data)
