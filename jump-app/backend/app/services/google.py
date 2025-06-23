import os
import sys
import time
import base64
sys.path.append("..")
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime, timedelta
import re
from typing import Optional, Dict, Any, List
from ..database import db

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

CREDENTIALS_FILE = "credentials.json"

if os.environ.get("GOOGLE_CREDS") and not os.path.exists(CREDENTIALS_FILE):
    # Create directory if it doesn't exist
    creds_dir = os.path.dirname(CREDENTIALS_FILE)
    if creds_dir:
        os.makedirs(creds_dir, exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        f.write(os.environ["GOOGLE_CREDS"])

def get_google_oauth_url() -> str:
    """Get Google OAuth URL"""
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, 
        SCOPES
    )
    flow.redirect_uri = "http://127.0.0.1:8000/auth/google/callback"
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    return auth_url

async def exchange_google_code(code: str) -> Optional[Dict[str, Any]]:
    """Exchange authorization code for tokens"""
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, 
            SCOPES
        )
        flow.redirect_uri = "http://127.0.0.1:8000/auth/google/callback"
        
        # Fetch token with the code
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        print(f"Successfully exchanged code for tokens. Scopes: {credentials.scopes}")  # Debug log
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": credentials.expiry.timestamp() - time.time() if credentials.expiry else 3600
        }
    except Exception as e:
        print(f"Error exchanging Google code: {e}")
        return None

def get_google_credentials(email: str) -> Optional[Credentials]:
    """Get Google credentials for a user from database"""
    try:
        user = db.get_user_by_email(email)
        if not user or not user.get("google_access_token"):
            return None
        
        # Check if token is expired
        expires_at = user.get("google_token_expires_at")
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=expires_datetime.tzinfo) >= expires_datetime:
                # Token expired, try to refresh
                return refresh_google_credentials(email)
        
        return Credentials(
            token=user["google_access_token"],
            refresh_token=user.get("google_refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=SCOPES
        )
    except Exception as e:
        print(f"Error getting Google credentials: {e}")
        return None

def refresh_google_credentials(email: str) -> Optional[Credentials]:
    """Refresh Google credentials for a user"""
    try:
        user = db.get_user_by_email(email)
        if not user or not user.get("google_refresh_token"):
            return None
        
        credentials = Credentials(
            token=None,
            refresh_token=user["google_refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=SCOPES
        )
        
        # Refresh the token
        credentials.refresh(Request())
        
        # Update database with new tokens
        expires_at = (datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp() - time.time())).isoformat()
        db.update_google_tokens(
            email,
            credentials.token,
            credentials.refresh_token,
            expires_at
        )
        
        return credentials
    except Exception as e:
        print(f"Error refreshing Google credentials: {e}")
        return None

def get_gmail_service(email: str):
    """Get Gmail service for a user"""
    credentials = get_google_credentials(email)
    if not credentials:
        return None
    
    try:
        service = build("gmail", "v1", credentials=credentials)
        return service
    except Exception as e:
        print(f"Error building Gmail service: {e}")
        return None

def get_calendar_service(email: str):
    """Get Google Calendar service for a user"""
    credentials = get_google_credentials(email)
    if not credentials:
        return None
    
    try:
        service = build("calendar", "v3", credentials=credentials)
        return service
    except Exception as e:
        print(f"Error building Calendar service: {e}")
        return None

def get_user_emails(email: str, max_results: int = 100) -> list:
    """Get user's emails from Gmail"""
    service = get_gmail_service(email)
    if not service:
        return []
    
    try:
        # Get messages
        results = service.users().messages().list(
            userId='me', 
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for message in messages:
            msg = service.users().messages().get(
                userId='me', 
                id=message['id'],
                format='full'
            ).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            recipient = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Get email body
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body'].get('data', '')
                        break
            else:
                body = msg['payload']['body'].get('data', '')
            
            # Decode base64 body
            try:
                body = base64.urlsafe_b64decode(body).decode('utf-8')
            except:
                body = 'Unable to decode email body'
            
            emails.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'content': body,
                'date': date
            })
        
        return emails
        
    except Exception as e:
        print(f"Error getting emails: {e}")
        return []

def get_calendar_events(email: str, max_results: int = 100) -> list:
    """Get user's calendar events"""
    service = get_calendar_service(email)
    if not service:
        return []
    
    try:
        # Get events from primary calendar
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        formatted_events = []
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start_time': start,
                'end_time': end,
                'location': event.get('location', ''),
                'attendees': [attendee.get('email', '') for attendee in event.get('attendees', [])]
            })
        
        return formatted_events
        
    except Exception as e:
        print(f"Error getting calendar events: {e}")
        return []

def create_calendar_event(email: str, summary: str, start_time: str, end_time: str, 
                         description: str = '', location: str = '', attendees: list = None) -> dict:
    """Create a calendar event"""
    service = get_calendar_service(email)
    if not service:
        return {"error": "Calendar service not available"}
    
    try:
        event = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        event = service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'
        ).execute()
        
        return {
            "success": True,
            "event_id": event['id'],
            "html_link": event.get('htmlLink', ''),
            "summary": event.get('summary', ''),
            "start_time": event['start'].get('dateTime', ''),
            "end_time": event['end'].get('dateTime', '')
        }
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return {"error": str(e)}

def send_email(email: str, to: str, subject: str, body: str) -> dict:
    """Send email via Gmail"""
    service = get_gmail_service(email)
    if not service:
        return {"error": "Gmail service not available"}
    
    try:
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return {
            "success": True,
            "message_id": sent_message['id'],
            "thread_id": sent_message['threadId']
        }
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return {"error": str(e)}

def parse_email_date(date_string: str) -> str:
    """Parse RFC date string to ISO format"""
    try:
        # Parse RFC date format like "Sun, 22 Jun 2025 17:46:44 +0000 (UTC)"
        dt = parsedate_to_datetime(date_string)
        return dt.isoformat()
    except:
        # Fallback to current time if parsing fails
        return datetime.utcnow().isoformat()

def get_recent_emails(max_results=5):
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me", maxResults=max_results, q="is:inbox"
    ).execute()
    messages = results.get("messages", [])
    email_data = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        date_string = next((h["value"] for h in headers if h["name"] == "Date"), "")
        
        # Parse date to ISO format
        date = parse_email_date(date_string)

        body = ""
        parts = msg_data["payload"].get("parts", [])
        for part in parts:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
        if not body:
            body = msg_data.get("snippet", "")

        # Truncate content to avoid token limits (roughly 6000 characters for safety)
        content = body.strip()[:6000]

        # Return dictionary format with correct field names
        email_dict = {
            "id": msg["id"],  # This matches what save_email_embedding expects
            "subject": subject,
            "sender": sender,
            "recipient": "me",  # Default recipient
            "content": content,
            "date": date
        }
        email_data.append(email_dict)

    return email_data


def get_upcoming_events(email: str, max_results=5):
    service = get_calendar_service(email)
    if not service:
        return []
    
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    upcoming = []
    for event in events:
        # Extract structured data from event
        event_data = {
            "id": event.get('id'),
            "summary": event.get('summary', 'No Title'),
            "description": event.get('description', ''),
            "start_time": event['start'].get('dateTime', event['start'].get('date')),
            "end_time": event['end'].get('dateTime', event['end'].get('date')),
            "location": event.get('location', ''),
            "attendees": [attendee.get('email', '') for attendee in event.get('attendees', []) if 'email' in attendee]
        }
        upcoming.append(event_data)

    return upcoming

def get_calendar_events_for_period(email: str, start_date=None, end_date=None, max_results=20):
    """Get calendar events for a specific time period"""
    service = get_calendar_service(email)
    if not service:
        return []
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        # End of current month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
    
    # Convert to ISO format
    time_min = start_date.isoformat() + 'Z'
    time_max = end_date.isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    calendar_events = []
    for event in events:
        # Extract structured data from event
        event_data = {
            "id": event.get('id'),
            "summary": event.get('summary', 'No Title'),
            "description": event.get('description', ''),
            "start_time": event['start'].get('dateTime', event['start'].get('date')),
            "end_time": event['end'].get('dateTime', event['end'].get('date')),
            "location": event.get('location', ''),
            "attendees": [attendee.get('email', '') for attendee in event.get('attendees', []) if 'email' in attendee]
        }
        calendar_events.append(event_data)

    return calendar_events

from email.mime.text import MIMEText

def reschedule_event(email: str, person: str, new_time: str):
    service = get_calendar_service(email)
    if not service:
        return "Error: Could not get calendar service"

    # Step 1: Parse datetime
    try:
        # Try to parse specific format (you can make this more robust)
        new_dt = datetime.strptime(new_time, "%Y-%m-%d %H:%M")
        new_end = new_dt + timedelta(hours=1)
    except ValueError:
        return f"⚠️ Could not parse new time '{new_time}'. Please use 'YYYY-MM-DD HH:MM'."

    # Step 2: Search for upcoming events with person in attendees or summary
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    for event in events:
        summary = event.get('summary', '').lower()
        attendees = [a['email'].lower() for a in event.get('attendees', []) if 'email' in a]
        if person.lower() in summary or any(person.lower() in a for a in attendees):
            event['start'] = {'dateTime': new_dt.isoformat(), 'timeZone': 'UTC'}
            event['end'] = {'dateTime': new_end.isoformat(), 'timeZone': 'UTC'}

            service.events().update(
                calendarId='primary',
                eventId=event['id'],
                body=event
            ).execute()

            return f"✅ Rescheduled '{event.get('summary', 'the event')}' with {person} to {new_dt.strftime('%Y-%m-%d %H:%M')} UTC."

    return f"⚠️ Could not find any upcoming event with {person} to reschedule."

def parse_natural_date(date_string: str) -> str:
    """Parse natural language date strings into YYYY-MM-DD HH:MM format"""
    try:
        # Get current date and time
        now = datetime.now()
        print(f"Now: {now}")
        
        # Convert to lowercase for easier matching
        date_lower = date_string.lower().strip()
        
        # Extract time (look for patterns like "2pm", "14:00", "2:30pm")
        time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
        time_match = re.search(time_pattern, date_lower)
        
        if not time_match:
            return None
        
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        
        # Convert to 24-hour format
        if ampm:
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
        
        # Determine the date based on natural language
        target_date = now
        
        if 'tomorrow' in date_lower:
            target_date = now + timedelta(days=1)
        elif 'today' in date_lower:
            target_date = now
        elif 'next week' in date_lower:
            target_date = now + timedelta(days=7)
        elif 'next monday' in date_lower:
            days_ahead = 7 - now.weekday()  # Monday is 0
            target_date = now + timedelta(days=days_ahead)
        elif 'next tuesday' in date_lower:
            days_ahead = (8 - now.weekday()) % 7
            target_date = now + timedelta(days=days_ahead)
        elif 'next wednesday' in date_lower:
            days_ahead = (9 - now.weekday()) % 7
            target_date = now + timedelta(days=days_ahead)
        elif 'next thursday' in date_lower:
            days_ahead = (10 - now.weekday()) % 7
            target_date = now + timedelta(days=days_ahead)
        elif 'next friday' in date_lower:
            days_ahead = (11 - now.weekday()) % 7
            target_date = now + timedelta(days=days_ahead)
        elif 'next saturday' in date_lower:
            days_ahead = (12 - now.weekday()) % 7
            target_date = now + timedelta(days=days_ahead)
        elif 'next sunday' in date_lower:
            days_ahead = (13 - now.weekday()) % 7
            target_date = now + timedelta(days=days_ahead)
        
        # Create the final datetime
        final_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Format as YYYY-MM-DD HH:MM
        return final_datetime.strftime("%Y-%m-%d %H:%M")
        
    except Exception as e:
        print(f"Error parsing natural date '{date_string}': {e}")
        return None
