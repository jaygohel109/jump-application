#!/usr/bin/env python3
"""
Database setup script for Jump AI Agent
This script helps set up the Supabase database with the required schema.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🚀 Jump AI Agent Database Setup")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY", 
        "SUPABASE_SERVICE_ROLE_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease add these to your .env file:")
        print("SUPABASE_URL=your_supabase_url")
        print("SUPABASE_ANON_KEY=your_supabase_anon_key")
        print("SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key")
        return False
    
    print("✅ Environment variables found")
    
    # Check if database_schema.sql exists
    schema_file = "database_schema.sql"
    if not os.path.exists(schema_file):
        print(f"❌ Schema file {schema_file} not found")
        return False
    
    print(f"✅ Schema file {schema_file} found")
    
    # Instructions for manual setup
    print("\n📋 Database Setup Instructions:")
    print("=" * 50)
    print("1. Go to your Supabase project dashboard")
    print("2. Navigate to the SQL Editor")
    print("3. Copy the contents of database_schema.sql")
    print("4. Paste and execute the SQL in the Supabase SQL Editor")
    print("5. Verify the tables were created successfully")
    
    print("\n🔧 Alternative: Use Supabase CLI")
    print("If you have Supabase CLI installed:")
    print("1. Run: supabase db push")
    print("2. Or copy the schema manually")
    
    print("\n📊 Tables that will be created:")
    print("- tasks (for task management)")
    print("- ongoing_instructions (for remembering user preferences)")
    print("- email_embeddings (for RAG with emails)")
    print("- hubspot_embeddings (for RAG with HubSpot data)")
    print("- conversation_history (for chat history)")
    
    print("\n🔍 After setup, you can test the connection:")
    print("python -c \"from app.database import db; print('Database connected!')\"")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 