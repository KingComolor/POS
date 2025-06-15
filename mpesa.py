import requests
import base64
import json
from datetime import datetime
import logging
from flask import current_app
from app import db
from models import Payment, Business, Sale, PaymentStatus, BusinessStatus

class MpesaService:
    def __init__(self):
        self.base_url = "https://sandbox.safaricom.co.ke" if current_app.debug else "https://api.safaricom.co.ke"
        self.consumer_key = None
        self.consumer_secret = None
        self.passkey = None
        self.shortcode = None
        self.till_number = None
        
    def initialize_config(self):
        """Initialize M-Pesa configuration from app config"""
        self.consumer_key = current_app.config.get('MPESA_CONSUMER_KEY')
        self.consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET')
        self.passkey = current_app.config.get('MPESA_PASSKEY')
        self.shortcode = current_app.config.get('MPESA_SHORTCODE')
        self.till_number = current_app.config.get('DEVELOPER_TILL_NUMBER')
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa API"""
        if not self.consumer_key:
            self.initialize_config()
        
        if not self.consumer_key or not self.consumer_secret:
            logging.error("M-Pesa credentials not configured")
            return None
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('access_token')
        
        except Exception as e:
            logging.error(f"Error getting M-Pesa access token: {str(e)}")
            return None
    
    def generate_password(self, timestamp):
        """Generate password for STK push"""
        if not self.shortcode or not self.passkey:
            self.initialize_config()
        
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode()
    
    def initiate_stk_push(self, phone_number, amount, reference_id):
        """Initiate STK push payment"""
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+254'):
            phone_number = phone_number[1:]
        elif phone_number.startswith('254'):
            pass
        else:
            phone_number = '254' + phone_number
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = self.generate_password(timestamp)
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{current_app.config.get('SERVER_URL', 'https://your-app.onrender.com')}/mpesa/callback",
            "AccountReference": f"REF{reference_id}",
            "TransactionDesc": "Comolor POS Payment"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': data.get('CheckoutRequestID'),
                    'merchant_request_id': data.get('MerchantRequestID')
                }
            else:
                return {
                    'success': False,
                    'message': data.get('ResponseDescription', 'STK push failed')
                }
        
        except Exception as e:
            logging.error(f"STK push error: {str(e)}")
            return {'success': False, 'message': 'Failed to initiate payment'}
    
    def process_callback(self, callback_data):
        """Process M-Pesa payment callback"""
        try:
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            logging.info(f"Processing callback - Result Code: {result_code}, Checkout Request ID: {checkout_request_id}")
            
            if result_code == 0:  # Success
                # Extract payment details
                callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                
                payment_details = {}
                for item in callback_metadata:
                    name = item.get('Name')
                    value = item.get('Value')
                    payment_details[name] = value
                
                amount = payment_details.get('Amount')
                mpesa_receipt_number = payment_details.get('MpesaReceiptNumber')
                transaction_date = payment_details.get('TransactionDate')
                phone_number = payment_details.get('PhoneNumber')
                
                # Find the payment record
                # We need to match by amount and phone number since we don't store checkout_request_id
                payment = Payment.query.filter_by(
                    amount=amount,
                    phone_number=str(phone_number),
                    status=PaymentStatus.PENDING
                ).first()
                
                if payment:
                    # Update payment record
                    payment.status = PaymentStatus.COMPLETED
                    payment.mpesa_receipt_number = mpesa_receipt_number
                    payment.mpesa_transaction_id = str(transaction_date)
                    payment.payment_date = datetime.utcnow()
                    
                    # Process based on payment type
                    if payment.payment_type == 'license':
                        self._process_license_payment(payment)
                    elif payment.payment_type == 'sale':
                        self._process_sale_payment(payment)
                    
                    db.session.commit()
                    
                    logging.info(f"Payment processed successfully: {mpesa_receipt_number}")
                    return {'success': True}
                else:
                    logging.warning(f"Payment record not found for callback: Amount={amount}, Phone={phone_number}")
                    return {'success': False, 'message': 'Payment record not found'}
            
            else:  # Failed payment
                logging.info(f"Payment failed: {result_desc}")
                # You might want to update payment status to failed here
                return {'success': True}  # Still return success to acknowledge callback
        
        except Exception as e:
            logging.error(f"Callback processing error: {str(e)}")
            return {'success': False, 'message': 'Error processing callback'}
    
    def _process_license_payment(self, payment):
        """Process license payment and activate business"""
        try:
            business = payment.business
            if not business:
                return
            
            # Determine license duration based on amount
            if payment.amount >= 30000:  # Yearly
                license_duration = 365
                business.subscription_plan = 'yearly'
            else:  # Monthly
                license_duration = 30
                business.subscription_plan = 'monthly'
            
            # Set license expiry date
            from datetime import timedelta
            business.license_expires_at = datetime.utcnow() + timedelta(days=license_duration)
            business.status = BusinessStatus.ACTIVE
            
            logging.info(f"License activated for business {business.id} until {business.license_expires_at}")
            
        except Exception as e:
            logging.error(f"License activation error: {str(e)}")
    
    def _process_sale_payment(self, payment):
        """Process sale payment and update sale status"""
        try:
            sale = payment.sale
            if sale:
                sale.payment_status = PaymentStatus.COMPLETED
                sale.mpesa_transaction_id = payment.mpesa_receipt_number
                
                logging.info(f"Sale {sale.sale_number} payment completed")
                
        except Exception as e:
            logging.error(f"Sale payment processing error: {str(e)}")
    
    def verify_transaction(self, transaction_id):
        """Verify a specific transaction with M-Pesa API"""
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}
        
        url = f"{self.base_url}/mpesa/transactionstatus/v1/query"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "Initiator": "testapi",
            "SecurityCredential": "your_security_credential",
            "CommandID": "TransactionStatusQuery",
            "TransactionID": transaction_id,
            "PartyA": self.shortcode,
            "IdentifierType": "4",
            "ResultURL": f"{current_app.config.get('SERVER_URL')}/mpesa/verify-callback",
            "QueueTimeOutURL": f"{current_app.config.get('SERVER_URL')}/mpesa/verify-timeout",
            "Remarks": "Transaction verification",
            "Occasion": "Verification"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {'success': True, 'data': response.json()}
        
        except Exception as e:
            logging.error(f"Transaction verification error: {str(e)}")
            return {'success': False, 'message': 'Verification failed'}
