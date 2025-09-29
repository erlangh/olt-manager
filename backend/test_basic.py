"""
Basic test script to verify the FastAPI application can start without database.
This script creates a minimal version of the app for testing.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_basic_app():
    """Test if we can create a basic FastAPI app."""
    print("Testing basic FastAPI application...")
    
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        
        # Create a minimal app
        app = FastAPI(
            title="OLT Manager API",
            description="Optical Line Terminal Management System",
            version="1.0.0"
        )
        
        @app.get("/")
        async def root():
            return {"message": "OLT Manager API is running"}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "olt-manager"}
        
        print("✓ Basic FastAPI app created successfully")
        print(f"✓ App title: {app.title}")
        print(f"✓ App version: {app.version}")
        print(f"✓ Routes count: {len(app.routes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic app test failed: {e}")
        return False

def test_pydantic_models():
    """Test basic Pydantic models."""
    print("\nTesting basic Pydantic models...")
    
    try:
        from pydantic import BaseModel, Field
        from typing import Optional
        from datetime import datetime
        
        # Test basic models
        class TestUser(BaseModel):
            username: str = Field(..., min_length=3, max_length=50)
            email: str
            is_active: bool = True
            created_at: Optional[datetime] = None
        
        class TestOLT(BaseModel):
            name: str = Field(..., min_length=1, max_length=100)
            ip_address: str
            location: Optional[str] = None
        
        # Test model validation
        user = TestUser(username="testuser", email="test@example.com")
        olt = TestOLT(name="Test OLT", ip_address="192.168.1.100")
        
        print(f"✓ User model: {user.username} ({user.email})")
        print(f"✓ OLT model: {olt.name} ({olt.ip_address})")
        
        return True
        
    except Exception as e:
        print(f"❌ Pydantic models test failed: {e}")
        return False

def test_uvicorn_import():
    """Test if uvicorn can be imported."""
    print("\nTesting Uvicorn import...")
    
    try:
        import uvicorn
        print(f"✓ Uvicorn imported successfully (version: {uvicorn.__version__})")
        return True
        
    except Exception as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False

def main():
    """Run all basic tests."""
    print("🚀 Starting Basic OLT Manager Tests")
    print("=" * 50)
    
    tests = [
        test_basic_app,
        test_pydantic_models,
        test_uvicorn_import
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
        print("🎉 All basic tests passed! FastAPI is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Install database dependencies (SQLAlchemy, etc.)")
        print("   2. Set up PostgreSQL database")
        print("   3. Run database migrations")
        print("   4. Test full application with all features")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)