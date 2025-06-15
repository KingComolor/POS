#!/usr/bin/env python3
"""
Create test data for Comolor POS system
Run this script to populate the database with sample users and businesses
"""

from app import app, db
from models import User, Business, Product, Customer, UserRole, BusinessStatus
from datetime import datetime, timedelta
import logging

def create_test_data():
    """Create test users and businesses"""
    
    with app.app_context():
        try:
            # Create Super Admin
            super_admin = User.query.filter_by(email='admin@comolor.com').first()
            if not super_admin:
                super_admin = User(
                    name='Super Admin',
                    email='admin@comolor.com',
                    role=UserRole.SUPER_ADMIN,
                    is_active=True,
                    email_verified=True
                )
                super_admin.set_password('admin123')
                db.session.add(super_admin)
                print("✓ Created Super Admin: admin@comolor.com / admin123")
            
            # Create Test Business 1
            test_business1 = Business.query.filter_by(email='shop@test.com').first()
            if not test_business1:
                test_business1 = Business(
                    name='Test Electronics Shop',
                    business_type='Electronics',
                    email='shop@test.com',
                    phone='+254712345678',
                    address='Nairobi CBD, Kenya',
                    till_number='5076965',
                    currency='KES',
                    tax_rate=16.0,
                    status=BusinessStatus.ACTIVE,
                    license_expires_at=datetime.utcnow() + timedelta(days=30),
                    subscription_plan='monthly'
                )
                db.session.add(test_business1)
                db.session.flush()
                
                # Create Business Owner for Test Business 1
                owner1 = User(
                    name='John Doe',
                    email='owner@test.com',
                    phone='+254712345678',
                    role=UserRole.BUSINESS_OWNER,
                    business_id=test_business1.id,
                    is_active=True,
                    email_verified=True
                )
                owner1.set_password('owner123')
                db.session.add(owner1)
                
                # Create Cashier for Test Business 1
                cashier1 = User(
                    name='Jane Smith',
                    email='cashier@test.com',
                    phone='+254712345679',
                    role=UserRole.CASHIER,
                    business_id=test_business1.id,
                    is_active=True,
                    email_verified=True
                )
                cashier1.set_password('cashier123')
                db.session.add(cashier1)
                
                print("✓ Created Test Business 1: Test Electronics Shop")
                print("  - Owner: owner@test.com / owner123")
                print("  - Cashier: cashier@test.com / cashier123")
            
            # Create Test Business 2
            test_business2 = Business.query.filter_by(email='grocery@test.com').first()
            if not test_business2:
                test_business2 = Business(
                    name='Fresh Grocery Store',
                    business_type='Grocery',
                    email='grocery@test.com',
                    phone='+254723456789',
                    address='Westlands, Nairobi',
                    till_number='5076966',
                    currency='KES',
                    tax_rate=16.0,
                    status=BusinessStatus.ACTIVE,
                    license_expires_at=datetime.utcnow() + timedelta(days=15),
                    subscription_plan='yearly'
                )
                db.session.add(test_business2)
                db.session.flush()
                
                # Create Business Owner for Test Business 2
                owner2 = User(
                    name='Mary Johnson',
                    email='mary@grocery.com',
                    phone='+254723456789',
                    role=UserRole.BUSINESS_OWNER,
                    business_id=test_business2.id,
                    is_active=True,
                    email_verified=True
                )
                owner2.set_password('mary123')
                db.session.add(owner2)
                
                print("✓ Created Test Business 2: Fresh Grocery Store")
                print("  - Owner: mary@grocery.com / mary123")
            
            # Add sample products for Test Business 1
            if not Product.query.filter_by(business_id=test_business1.id).first():
                products1 = [
                    Product(
                        business_id=test_business1.id,
                        name='Samsung Galaxy Phone',
                        description='Latest Samsung smartphone',
                        sku='PHONE001',
                        barcode='1234567890123',
                        cost_price=25000.0,
                        selling_price=35000.0,
                        stock_quantity=10,
                        min_stock_level=3,
                        category='Phones'
                    ),
                    Product(
                        business_id=test_business1.id,
                        name='Laptop Charger',
                        description='Universal laptop charger',
                        sku='CHAR001',
                        cost_price=1500.0,
                        selling_price=2500.0,
                        stock_quantity=25,
                        min_stock_level=5,
                        category='Accessories'
                    ),
                    Product(
                        business_id=test_business1.id,
                        name='USB Cable',
                        description='Type-C USB cable',
                        sku='USB001',
                        cost_price=200.0,
                        selling_price=500.0,
                        stock_quantity=2,  # Low stock for testing alerts
                        min_stock_level=5,
                        category='Accessories'
                    )
                ]
                for product in products1:
                    db.session.add(product)
                print("✓ Added sample products for Test Electronics Shop")
            
            # Add sample products for Test Business 2
            if not Product.query.filter_by(business_id=test_business2.id).first():
                products2 = [
                    Product(
                        business_id=test_business2.id,
                        name='Fresh Milk 1L',
                        description='Fresh cow milk',
                        sku='MILK001',
                        cost_price=80.0,
                        selling_price=120.0,
                        stock_quantity=50,
                        min_stock_level=10,
                        category='Dairy'
                    ),
                    Product(
                        business_id=test_business2.id,
                        name='Bread Loaf',
                        description='Whole wheat bread',
                        sku='BREAD001',
                        cost_price=45.0,
                        selling_price=70.0,
                        stock_quantity=30,
                        min_stock_level=5,
                        category='Bakery'
                    )
                ]
                for product in products2:
                    db.session.add(product)
                print("✓ Added sample products for Fresh Grocery Store")
            
            # Add sample customers
            if not Customer.query.filter_by(business_id=test_business1.id).first():
                customers = [
                    Customer(
                        business_id=test_business1.id,
                        name='Alice Wanjiku',
                        email='alice@example.com',
                        phone='+254701234567',
                        address='Kiambu Road, Nairobi'
                    ),
                    Customer(
                        business_id=test_business1.id,
                        name='Bob Mwangi',
                        phone='+254702345678'
                    )
                ]
                for customer in customers:
                    db.session.add(customer)
                print("✓ Added sample customers")
            
            db.session.commit()
            print("\n🎉 Test data created successfully!")
            print("\n" + "="*50)
            print("TEST CREDENTIALS")
            print("="*50)
            print("\n🔑 SUPER ADMIN:")
            print("   Email: admin@comolor.com")
            print("   Password: admin123")
            print("   Access: Full system access, manage all businesses")
            
            print("\n🏢 BUSINESS 1 - Test Electronics Shop:")
            print("   Owner Email: owner@test.com")
            print("   Owner Password: owner123")
            print("   Cashier Email: cashier@test.com") 
            print("   Cashier Password: cashier123")
            print("   License Status: Active (30 days remaining)")
            
            print("\n🏪 BUSINESS 2 - Fresh Grocery Store:")
            print("   Owner Email: mary@grocery.com")
            print("   Owner Password: mary123")
            print("   License Status: Active (15 days remaining)")
            
            print("\n📱 Test Features:")
            print("   - Multi-tenant data isolation")
            print("   - Role-based access control")
            print("   - Low stock alerts (USB Cable)")
            print("   - License expiry warnings")
            print("   - Sample products and customers")
            print("="*50)
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating test data: {str(e)}")
            logging.error(f"Test data creation failed: {str(e)}")

if __name__ == '__main__':
    create_test_data()