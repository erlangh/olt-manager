#!/usr/bin/env python3
"""
Database Initialization Script for OLT Manager
Membuat tabel users dan user admin default
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_database():
    """Initialize database with users table and default admin user"""
    try:
        # Database connection parameters
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'olt_manager'),
            'user': os.getenv('DB_USER', 'oltmanager'),
            'password': os.getenv('DB_PASSWORD', 'oltmanager123'),
            'port': os.getenv('DB_PORT', '5432')
        }
        
        print(f"Connecting to database: {db_config['database']} at {db_config['host']}:{db_config['port']}")
        
        # Connect to database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Connected to database successfully")
        
        # Create users table if not exists
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        
        cursor.execute(create_table_query)
        print("Users table created/verified successfully")
        
        # Check if admin user exists
        cursor.execute('SELECT id, username, role FROM users WHERE username = %s', ('admin',))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"Admin user already exists: ID={existing_user['id']}, Role={existing_user['role']}")
        else:
            # Create admin user with default password
            admin_password = 'admin123'
            password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            insert_user_query = '''
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, username, role
            '''
            
            cursor.execute(insert_user_query, (
                'admin',
                'admin@oltmanager.com',
                password_hash,
                'admin',
                True
            ))
            
            new_user = cursor.fetchone()
            print(f"Admin user created successfully: ID={new_user['id']}, Username={new_user['username']}, Role={new_user['role']}")
            print(f"Default password: {admin_password}")
        
        # Create indexes for better performance
        index_queries = [
            'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)',
            'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
            'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
            'CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)'
        ]
        
        for query in index_queries:
            cursor.execute(query)
        
        print("Database indexes created/verified successfully")
        
        # Commit all changes
        conn.commit()
        
        # Verify the setup
        cursor.execute('SELECT COUNT(*) as user_count FROM users')
        user_count = cursor.fetchone()['user_count']
        print(f"Total users in database: {user_count}")
        
        cursor.close()
        conn.close()
        
        print("Database initialization completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'olt_manager'),
            'user': os.getenv('DB_USER', 'oltmanager'),
            'password': os.getenv('DB_PASSWORD', 'oltmanager123'),
            'port': os.getenv('DB_PORT', '5432')
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        print(f"PostgreSQL version: {version}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

if __name__ == '__main__':
    print("=== OLT Manager Database Initialization ===")
    print()
    
    # Test connection first
    print("Testing database connection...")
    if not test_connection():
        print("Database connection failed. Please check your configuration.")
        sys.exit(1)
    
    print("Database connection successful!")
    print()
    
    # Initialize database
    print("Initializing database...")
    if init_database():
        print()
        print("=== Initialization Complete ===")
        print("You can now start the OLT Manager application.")
        print("Default login credentials:")
        print("  Username: admin")
        print("  Password: admin123")
    else:
        print("Database initialization failed!")
        sys.exit(1)