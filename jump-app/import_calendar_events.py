#!/usr/bin/env python3
"""
Import calendar events with embeddings
This script will fetch calendar events from Google Calendar and store them with embeddings
"""

import os
import sys
sys.path.append('backend')

from app.database import db
from app.services.embeddings import embedding_service
from app.services.google import get_calendar_events_for_period
from datetime import datetime, timedelta

def clear_existing_calendar_embeddings():
    """Clear existing calendar embeddings"""
    print("🗑️ Clearing existing calendar embeddings...")
    try:
        result = db.supabase.table("calendar_embeddings").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"   Cleared {len(result.data) if result.data else 0} calendar embeddings")
        return True
    except Exception as e:
        print(f"❌ Error clearing calendar embeddings: {e}")
        return False

def import_calendar_events():
    """Import calendar events with embeddings"""
    print("\n📅 Importing calendar events with embeddings...")
    try:
        # Get default user for system-wide operations
        default_user = db.get_default_user()
        if not default_user:
            print("   ❌ No default user found with Google tokens")
            return False
        
        user_email = default_user["email"]
        print(f"   Using user: {user_email}")
        
        # Get events for current month
        current_month_events = get_calendar_events_for_period(user_email, max_results=50)
        print(f"   Found {len(current_month_events)} events for current month")
        
        # Get events for next month
        next_month_start = datetime.utcnow().replace(day=1) + timedelta(days=32)
        next_month_start = next_month_start.replace(day=1)
        next_month_end = next_month_start.replace(month=next_month_start.month + 1) - timedelta(days=1)
        
        next_month_events = get_calendar_events_for_period(
            user_email,
            start_date=next_month_start,
            end_date=next_month_end,
            max_results=50
        )
        print(f"   Found {len(next_month_events)} events for next month")
        
        all_events = current_month_events + next_month_events
        
        if not all_events:
            print("   ⚠️ No calendar events found")
            return False
        
        # Import with embeddings
        result = embedding_service.bulk_import_calendar_events(all_events)
        print(f"   ✅ Successfully imported {result['success']} calendar events")
        print(f"   ❌ Failed to import {result['errors']} calendar events")
        
        return result['success'] > 0
        
    except Exception as e:
        print(f"❌ Error importing calendar events: {e}")
        return False

def test_calendar_search():
    """Test the calendar search functionality"""
    print("\n🔍 Testing calendar search functionality...")
    try:
        # Test queries
        test_queries = [
            "this month events",
            "next month events",
            "meeting with vijay",
            "team standup",
            "client call"
        ]
        
        for query in test_queries:
            print(f"\n   Testing query: '{query}'")
            
            # Test calendar search
            events = embedding_service.search_similar_calendar_events(query, 3, 0.3)
            print(f"     📅 Found {len(events)} calendar events")
            for i, event in enumerate(events[:2]):
                print(f"       {i+1}. {event.get('summary', 'No summary')}: {event.get('start_time', 'TBD')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing calendar search: {e}")
        return False

def show_calendar_events():
    """Show what calendar events are in the database"""
    print("\n📋 Calendar events in database:")
    try:
        events = db.get_recent_calendar_events(10)
        if events:
            for i, event in enumerate(events):
                print(f"  {i+1}. {event.get('summary', 'No summary')}")
                print(f"     Time: {event.get('start_time', 'TBD')}")
                print(f"     Attendees: {', '.join(event.get('attendees', []))}")
                print()
        else:
            print("  No calendar events found in database")
        
        return len(events) > 0
        
    except Exception as e:
        print(f"❌ Error showing calendar events: {e}")
        return False

def main():
    """Main import function"""
    print("🚀 IMPORTING CALENDAR EVENTS WITH EMBEDDINGS")
    print("=" * 60)
    print("This script will:")
    print("1. Clear existing calendar embeddings")
    print("2. Import calendar events from Google Calendar")
    print("3. Create embeddings for semantic search")
    print("4. Test the search functionality")
    print()
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        return
    
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        print("❌ Supabase environment variables not set")
        return
    
    # Step 1: Clear existing calendar embeddings
    if not clear_existing_calendar_embeddings():
        print("❌ Failed to clear existing calendar embeddings")
        return
    
    # Step 2: Import calendar events
    if not import_calendar_events():
        print("❌ Failed to import calendar events")
        return
    
    # Step 3: Show what was imported
    show_calendar_events()
    
    # Step 4: Test search functionality
    test_calendar_search()
    
    print("\n✅ Calendar import completed!")
    print("\n📊 SUMMARY:")
    print("- Calendar events are now stored with embeddings")
    print("- You can search for events by date, attendee, or description")
    print("- Try queries like 'this month events' or 'meeting with vijay'")

if __name__ == "__main__":
    main() 