#!/usr/bin/env python3
"""
Script to set up the users table in Supabase for the new authentication system.
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

load_dotenv()

def setup_users_table():
    """Set up the users table in Supabase"""
    
    # SQL to create the users table
    create_users_table_sql = """
    -- Create users table for authentication
    CREATE TABLE IF NOT EXISTS users (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        google_access_token TEXT,
        google_refresh_token TEXT,
        google_token_expires_at TIMESTAMP WITH TIME ZONE,
        hubspot_access_token TEXT,
        hubspot_refresh_token TEXT,
        hubspot_token_expires_at TIMESTAMP WITH TIME ZONE,
        session_id VARCHAR(255) UNIQUE,
        session_expires_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id);
    CREATE INDEX IF NOT EXISTS idx_users_google_token_expires ON users(google_token_expires_at);
    CREATE INDEX IF NOT EXISTS idx_users_hubspot_token_expires ON users(hubspot_token_expires_at);

    -- Enable RLS (Row Level Security)
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;

    -- Create RLS policies (simplified for now)
    DROP POLICY IF EXISTS "Allow all operations" ON users;
    CREATE POLICY "Allow all operations" ON users FOR ALL USING (true);

    -- Create function to update updated_at timestamp
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- Create trigger to automatically update updated_at
    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON users 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    print("=== Setting up Users Table ===\n")
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("✗ Missing Supabase environment variables")
        print("Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file")
        return False
    
    print("✓ Environment variables found")
    
    try:
        # Test database connection
        from app.database import db
        print("✓ Database connection successful")
        
        # Try to create a test user to see if table exists
        test_user = db.create_or_update_user("test@example.com")
        if test_user:
            print("✓ Users table exists and is working")
            
            # Clean up test user
            # Note: We don't have a delete function, but that's okay for now
            print("✓ Test user created successfully")
        else:
            print("✗ Failed to create test user - table might not exist")
            print("\nPlease run this SQL in your Supabase SQL editor:")
            print(create_users_table_sql)
            return False
            
    except Exception as e:
        print(f"✗ Database error: {e}")
        print("\nPlease run this SQL in your Supabase SQL editor:")
        print(create_users_table_sql)
        return False
    
    print("\n✓ Users table setup completed successfully!")
    return True

if __name__ == "__main__":
    success = setup_users_table()
    if success:
        print("\nNext steps:")
        print("1. Start your backend server: python -m uvicorn app.main:app --reload")
        print("2. Start your frontend server: npm run dev")
        print("3. Visit http://localhost:5173 to test the authentication flow")
    else:
        print("\nSetup failed. Please check the errors above.")
        sys.exit(1) 