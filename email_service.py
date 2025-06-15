from flask import render_template, current_app
from flask_mail import Message
from app import mail
import logging

class EmailService:
    
    def send_welcome_email(self, user, business):
        """Send welcome email to new user"""
        try:
            subject = "Welcome to Comolor POS"
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=render_template('emails/welcome.html', user=user, business=business),
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            logging.info(f"Welcome email sent to {user.email}")
            
        except Exception as e:
            logging.error(f"Failed to send welcome email to {user.email}: {str(e)}")
    
    def send_license_expiry_warning(self, user, business, days_remaining):
        """Send license expiry warning email"""
        try:
            subject = f"License Expires in {days_remaining} Days - Comolor POS"
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=render_template('emails/license_expiry.html', 
                                   user=user, 
                                   business=business, 
                                   days_remaining=days_remaining),
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            logging.info(f"License expiry warning sent to {user.email}")
            
        except Exception as e:
            logging.error(f"Failed to send license expiry warning to {user.email}: {str(e)}")
    
    def send_license_expired_notification(self, user, business):
        """Send license expired notification"""
        try:
            subject = "License Expired - Comolor POS"
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=render_template('emails/license_expired.html', user=user, business=business),
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            logging.info(f"License expired notification sent to {user.email}")
            
        except Exception as e:
            logging.error(f"Failed to send license expired notification to {user.email}: {str(e)}")
    
    def send_password_reset_email(self, user, reset_token):
        """Send password reset email"""
        try:
            subject = "Password Reset - Comolor POS"
            
            reset_url = f"{current_app.config.get('SERVER_URL', 'http://localhost:5000')}/reset-password/{reset_token}"
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=render_template('emails/password_reset.html', user=user, reset_url=reset_url),
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            logging.info(f"Password reset email sent to {user.email}")
            
        except Exception as e:
            logging.error(f"Failed to send password reset email to {user.email}: {str(e)}")
    
    def send_business_approval_notification(self, user, business):
        """Send business approval notification"""
        try:
            subject = "Business Approved - Comolor POS"
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=render_template('emails/business_approved.html', user=user, business=business),
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            logging.info(f"Business approval notification sent to {user.email}")
            
        except Exception as e:
            logging.error(f"Failed to send business approval notification to {user.email}: {str(e)}")
    
    def send_license_activation_notification(self, user, business):
        """Send license activation notification"""
        try:
            subject = "License Activated - Comolor POS"
            
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=render_template('emails/license_activated.html', user=user, business=business),
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            logging.info(f"License activation notification sent to {user.email}")
            
        except Exception as e:
            logging.error(f"Failed to send license activation notification to {user.email}: {str(e)}")
