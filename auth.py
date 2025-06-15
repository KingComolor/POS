from functools import wraps
from flask import request, abort, flash, redirect, url_for
from flask_login import current_user
from datetime import datetime
from models import ActivityLog, UserRole
from app import db

def require_role(roles):
    """Decorator to require specific user roles"""
    if not isinstance(roles, list):
        roles = [roles]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_business_license(f):
    """Decorator to require active business license"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        if current_user.is_super_admin():
            return f(*args, **kwargs)
        
        if not current_user.business or not current_user.business.is_license_active():
            flash('Your business license has expired. Please renew to continue.', 'error')
            return redirect(url_for('license_payment'))
        
        return f(*args, **kwargs)
    return decorated_function

def require_same_business(f):
    """Decorator to ensure users can only access their own business data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Super admin can access everything
        if current_user.is_super_admin():
            return f(*args, **kwargs)
        
        # Check if business_id in kwargs matches user's business
        business_id = kwargs.get('business_id')
        if business_id and business_id != current_user.business_id:
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def log_activity(business_id, user_id, action, details, request_obj):
    """Log user activity"""
    try:
        activity = ActivityLog(
            business_id=business_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=request_obj.remote_addr,
            user_agent=request_obj.headers.get('User-Agent', '')[:500]
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Don't raise exception for logging failures
        pass
