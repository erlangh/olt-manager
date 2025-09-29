#!/usr/bin/env python3
"""
Database initialization script for OLT Manager
Creates tables and inserts default data
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base, User, OLT, ServiceProfile
from core.config import settings
from database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not specific database)
        server_url = settings.DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
        engine = create_engine(server_url)
        
        with engine.connect() as conn:
            # Set autocommit mode
            conn.execute(text("COMMIT"))
            
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.DATABASE_NAME}
            )
            
            if not result.fetchone():
                print(f"Creating database: {settings.DATABASE_NAME}")
                conn.execute(text(f"CREATE DATABASE {settings.DATABASE_NAME}"))
                print("Database created successfully!")
            else:
                print(f"Database {settings.DATABASE_NAME} already exists")
                
    except Exception as e:
        print(f"Error creating database: {e}")
        return False
    
    return True

def create_tables():
    """Create all tables"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

def create_default_user():
    """Create default admin user"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("Default admin user already exists")
            db.close()
            return True
        
        # Create admin user
        hashed_password = pwd_context.hash("admin123")
        admin_user = User(
            username="admin",
            email="admin@oltmanager.local",
            full_name="System Administrator",
            hashed_password=hashed_password,
            role="admin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(admin_user)
        db.commit()
        print("Default admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"Error creating default user: {e}")
        return False

def create_default_service_profiles():
    """Create default service profiles"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Check if service profiles already exist
        existing_profiles = db.query(ServiceProfile).count()
        if existing_profiles > 0:
            print("Service profiles already exist")
            db.close()
            return True
        
        # Create default service profiles
        profiles = [
            {
                "name": "Basic Internet",
                "description": "Basic internet service profile",
                "downstream_bandwidth": 100,  # 100 Mbps
                "upstream_bandwidth": 50,     # 50 Mbps
                "vlan_id": 100,
                "service_type": "internet",
                "qos_profile": "best_effort"
            },
            {
                "name": "Premium Internet",
                "description": "Premium internet service profile",
                "downstream_bandwidth": 500,  # 500 Mbps
                "upstream_bandwidth": 200,    # 200 Mbps
                "vlan_id": 200,
                "service_type": "internet",
                "qos_profile": "guaranteed"
            },
            {
                "name": "IPTV Service",
                "description": "IPTV service profile",
                "downstream_bandwidth": 50,   # 50 Mbps
                "upstream_bandwidth": 10,     # 10 Mbps
                "vlan_id": 300,
                "service_type": "iptv",
                "qos_profile": "video"
            },
            {
                "name": "VoIP Service",
                "description": "Voice over IP service profile",
                "downstream_bandwidth": 2,    # 2 Mbps
                "upstream_bandwidth": 2,      # 2 Mbps
                "vlan_id": 400,
                "service_type": "voip",
                "qos_profile": "voice"
            }
        ]
        
        for profile_data in profiles:
            profile = ServiceProfile(
                **profile_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(profile)
        
        db.commit()
        print(f"Created {len(profiles)} default service profiles")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"Error creating service profiles: {e}")
        return False

def create_sample_olt():
    """Create a sample OLT for testing"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Check if OLT already exists
        existing_olt = db.query(OLT).filter(OLT.name == "Sample-OLT-01").first()
        if existing_olt:
            print("Sample OLT already exists")
            db.close()
            return True
        
        # Create sample OLT
        sample_olt = OLT(
            name="Sample-OLT-01",
            ip_address="192.168.1.100",
            snmp_community="public",
            snmp_version="2c",
            location="Data Center - Rack A1",
            description="Sample ZTE C320 OLT for testing",
            model="ZTE C320",
            firmware_version="V2.1.0",
            max_ports=16,
            status="online",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(sample_olt)
        db.commit()
        print("Sample OLT created successfully!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"Error creating sample OLT: {e}")
        return False

def main():
    """Main initialization function"""
    print("Starting OLT Manager database initialization...")
    print("=" * 50)
    
    # Step 1: Create database if not exists
    print("Step 1: Creating database...")
    if not create_database_if_not_exists():
        print("Failed to create database. Exiting.")
        sys.exit(1)
    
    # Step 2: Create tables
    print("\nStep 2: Creating tables...")
    if not create_tables():
        print("Failed to create tables. Exiting.")
        sys.exit(1)
    
    # Step 3: Create default admin user
    print("\nStep 3: Creating default admin user...")
    if not create_default_user():
        print("Failed to create default user. Exiting.")
        sys.exit(1)
    
    # Step 4: Create default service profiles
    print("\nStep 4: Creating default service profiles...")
    if not create_default_service_profiles():
        print("Failed to create service profiles. Exiting.")
        sys.exit(1)
    
    # Step 5: Create sample OLT
    print("\nStep 5: Creating sample OLT...")
    if not create_sample_olt():
        print("Failed to create sample OLT. Exiting.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Database initialization completed successfully!")
    print("\nDefault credentials:")
    print("Username: admin")
    print("Password: admin123")
    print("\nYou can now start the application.")

if __name__ == "__main__":
    main()