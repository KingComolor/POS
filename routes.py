from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import secrets
import logging

from app import app, db, mail
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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
