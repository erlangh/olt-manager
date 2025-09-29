"""
Simple test script to verify the FastAPI application structure.
This script tests the application without requiring database or external dependencies.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Test if all modules can be imported successfully."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from fastapi import FastAPI
        print("✓ FastAPI imported successfully")
        
        # Test if our modules can be imported
        from api.schemas.auth import LoginRequest, UserResponse
        print("✓ Auth schemas imported successfully")
        
        from api.schemas.olt import OLTBase, OLTResponse
        print("✓ OLT schemas imported successfully")
        
        from api.schemas.ont import ONTBase, ONTResponse
        print("✓ ONT schemas imported successfully")
        
        from api.schemas.monitoring import AlarmBase, PerformanceDataBase
        print("✓ Monitoring schemas imported successfully")
        
        print("\n✅ All schema imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_schema_validation():
    """Test basic schema validation."""
    print("\nTesting schema validation...")
    
    try:
        from api.schemas.auth import LoginRequest, UserResponse
        from api.schemas.olt import OLTCreate, OLTResponse
        from datetime import datetime
        
        # Test LoginRequest validation
        login_data = LoginRequest(username="testuser", password="testpass123")
        print(f"✓ LoginRequest validation: {login_data.username}")
        
        # Test OLTCreate validation
        olt_data = OLTCreate(
            name="Test OLT",
            ip_address="192.168.1.100",
            snmp_community="public",
            location="Test Location"
        )
        print(f"✓ OLTCreate validation: {olt_data.name}")
        
        print("\n✅ Schema validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        return False

def test_api_structure():
    """Test API router structure."""
    print("\nTesting API structure...")
    
    try:
        from api.auth import router as auth_router
        from api.olt import router as olt_router
        from api.ont import router as ont_router
        from api.monitoring import router as monitoring_router
        from api.users import router as users_router
        from api.websocket import router as websocket_router
        
        print(f"✓ Auth router: {len(auth_router.routes)} routes")
        print(f"✓ OLT router: {len(olt_router.routes)} routes")
        print(f"✓ ONT router: {len(ont_router.routes)} routes")
        print(f"✓ Monitoring router: {len(monitoring_router.routes)} routes")
        print(f"✓ Users router: {len(users_router.routes)} routes")
        print(f"✓ WebSocket router: {len(websocket_router.routes)} routes")
        
        print("\n✅ API structure tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ API structure error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting OLT Manager Application Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_schema_validation,
        test_api_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application structure is correct.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)