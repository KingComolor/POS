from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging
from app import app, db
from models import Business, User, BusinessStatus, UserRole
from email_service import EmailService

class LicenseScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.email_service = EmailService()
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            # Check license expiry every day at 9 AM
            self.scheduler.add_job(
                func=self.check_license_expiry,
                trigger=CronTrigger(hour=9, minute=0),
                id='license_expiry_check',
                name='Check license expiry',
                replace_existing=True
            )
            
            # Lock expired licenses every hour
            self.scheduler.add_job(
                func=self.lock_expired_licenses,
                trigger=CronTrigger(minute=0),
                id='lock_expired_licenses',
                name='Lock expired licenses',
                replace_existing=True
            )
            
            self.scheduler.start()
            logging.info("License scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logging.info("License scheduler stopped")
    
    def check_license_expiry(self):
        """Check for licenses expiring in 5 days and send warnings"""
        try:
            with app.app_context():
                warning_date = datetime.utcnow() + timedelta(days=5)
                
                # Find businesses with licenses expiring in 5 days
                businesses = Business.query.filter(
                    Business.status == BusinessStatus.ACTIVE,
                    Business.license_expires_at <= warning_date,
                    Business.license_expires_at > datetime.utcnow()
                ).all()
                
                for business in businesses:
                    days_remaining = business.days_until_expiry()
                    
                    if days_remaining <= 5:
                        # Get business owner
                        owner = User.query.filter_by(
                            business_id=business.id,
                            role=UserRole.BUSINESS_OWNER
                        ).first()
                        
                        if owner:
                            self.email_service.send_license_expiry_warning(
                                owner, business, days_remaining
                            )
                            logging.info(f"License expiry warning sent for business {business.id}")
                
        except Exception as e:
            logging.error(f"License expiry check error: {str(e)}")
    
    def lock_expired_licenses(self):
        """Lock businesses with expired licenses"""
        try:
            with app.app_context():
                # Find businesses with expired licenses
                expired_businesses = Business.query.filter(
                    Business.status == BusinessStatus.ACTIVE,
                    Business.license_expires_at <= datetime.utcnow()
                ).all()
                
                for business in expired_businesses:
                    business.status = BusinessStatus.EXPIRED
                    
                    # Get business owner and send notification
                    owner = User.query.filter_by(
                        business_id=business.id,
                        role=UserRole.BUSINESS_OWNER
                    ).first()
                    
                    if owner:
                        self.email_service.send_license_expired_notification(owner, business)
                    
                    logging.info(f"Business {business.id} license expired and locked")
                
                if expired_businesses:
                    db.session.commit()
                
        except Exception as e:
            logging.error(f"License locking error: {str(e)}")
            db.session.rollback()

# Initialize and start scheduler
license_scheduler = LicenseScheduler()

# Start scheduler when module is imported
with app.app_context():
    license_scheduler.start()
