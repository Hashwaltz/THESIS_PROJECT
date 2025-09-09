#!/usr/bin/env python3
"""
Test script for Norzagaray HR & Payroll System
This script tests the basic functionality of both systems
"""

import sys
import os
import requests
import json
from datetime import datetime, date

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_hr_system():
    """Test HR System functionality"""
    print("🧪 Testing HR System...")
    
    try:
        # Test health check
        response = requests.get('http://localhost:5001/api/hr/health', timeout=5)
        if response.status_code == 200:
            print("✅ HR System health check passed")
        else:
            print("❌ HR System health check failed")
            return False
        
        # Test employees endpoint
        response = requests.get('http://localhost:5001/api/hr/employees', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ HR System employees endpoint working - {data.get('count', 0)} employees")
            else:
                print("❌ HR System employees endpoint returned error")
                return False
        else:
            print("❌ HR System employees endpoint failed")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ HR System not running on port 5001")
        return False
    except Exception as e:
        print(f"❌ HR System test failed: {e}")
        return False

def test_payroll_system():
    """Test Payroll System functionality"""
    print("🧪 Testing Payroll System...")
    
    try:
        # Test health check
        response = requests.get('http://localhost:5002/api/payroll/health', timeout=5)
        if response.status_code == 200:
            print("✅ Payroll System health check passed")
        else:
            print("❌ Payroll System health check failed")
            return False
        
        # Test employees endpoint
        response = requests.get('http://localhost:5002/api/payroll/employees', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Payroll System employees endpoint working - {data.get('count', 0)} employees")
            else:
                print("❌ Payroll System employees endpoint returned error")
                return False
        else:
            print("❌ Payroll System employees endpoint failed")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Payroll System not running on port 5002")
        return False
    except Exception as e:
        print(f"❌ Payroll System test failed: {e}")
        return False

def test_main_app():
    """Test Main Application"""
    print("🧪 Testing Main Application...")
    
    try:
        # Test main dashboard
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Main application dashboard accessible")
        else:
            print("❌ Main application dashboard failed")
            return False
        
        # Test HR redirect
        response = requests.get('http://localhost:5000/hr', timeout=5)
        if response.status_code in [200, 302]:  # 302 for redirect to login
            print("✅ HR system redirect working")
        else:
            print("❌ HR system redirect failed")
            return False
        
        # Test Payroll redirect
        response = requests.get('http://localhost:5000/payroll', timeout=5)
        if response.status_code in [200, 302]:  # 302 for redirect to login
            print("✅ Payroll system redirect working")
        else:
            print("❌ Payroll system redirect failed")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Main application not running on port 5000")
        return False
    except Exception as e:
        print(f"❌ Main application test failed: {e}")
        return False

def test_database_creation():
    """Test database creation"""
    print("🧪 Testing Database Creation...")
    
    try:
        # Check if database files exist
        hr_db = os.path.exists('hr_system/hr_system.db')
        payroll_db = os.path.exists('payroll_system/payroll_system.db')
        main_db = os.path.exists('main_app/norzagaray_hr_payroll.db')
        
        if hr_db:
            print("✅ HR System database created")
        else:
            print("❌ HR System database not found")
        
        if payroll_db:
            print("✅ Payroll System database created")
        else:
            print("❌ Payroll System database not found")
        
        if main_db:
            print("✅ Main application database created")
        else:
            print("❌ Main application database not found")
        
        return hr_db and payroll_db and main_db
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Norzagaray HR & Payroll System Tests")
    print("=" * 50)
    
    # Test database creation
    db_test = test_database_creation()
    print()
    
    # Test main application
    main_test = test_main_app()
    print()
    
    # Test HR system
    hr_test = test_hr_system()
    print()
    
    # Test Payroll system
    payroll_test = test_payroll_system()
    print()
    
    # Summary
    print("=" * 50)
    print("📊 Test Results Summary:")
    print(f"Database Creation: {'✅ PASS' if db_test else '❌ FAIL'}")
    print(f"Main Application: {'✅ PASS' if main_test else '❌ FAIL'}")
    print(f"HR System: {'✅ PASS' if hr_test else '❌ FAIL'}")
    print(f"Payroll System: {'✅ PASS' if payroll_test else '❌ FAIL'}")
    
    all_tests_passed = db_test and main_test and hr_test and payroll_test
    
    if all_tests_passed:
        print("\n🎉 All tests passed! The system is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the system configuration.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


