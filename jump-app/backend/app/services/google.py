import os
import pickle
import base64
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app import config
from typing import List
import re

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

TOKEN_FILE = "token.pickle"
CREDENTIALS_FILE = "credentials.json"

if os.environ.get("GOOGLE_CREDS") and not os.path.exists(CREDENTIALS_FILE):
    # Create directory if it doesn't exist
    creds_dir = os.path.dirname(CREDENTIALS_FILE)
    if creds_dir:
        os.makedirs(creds_dir, exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        f.write(os.environ["GOOGLE_CREDS"])

if os.environ.get("GOOGLE_TOKEN") and not os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "wb") as f:
        f.write(base64.b64decode(os.environ["GOOGLE_TOKEN"]))

def get_gmail_service():
    return build("gmail", "v1", credentials=get_credentials())


def get_calendar_service():
    return build("calendar", "v3", credentials=get_credentials())

def build_flow():
    return Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=os.environ["GOOGLE_REDIRECT_URI"]
    )

def handle_google_callback(request, code):
    if "google_oauth_flow" not in request.session:
        raise Exception("OAuth flow not found in session.")

    flow_serialized = request.session["google_oauth_flow"]
    flow = pickle.loads(flow_serialized.encode("latin1"))

    flow.fetch_token(code=code)
    creds = flow.credentials

    with open(TOKEN_FILE, "wb") as token:
        pickle.dump(creds, token)

    return creds

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Missing valid credentials. Please log in via Google OAuth.")
    return creds

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


def get_upcoming_events(max_results=5):
    service = get_calendar_service()
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

def get_calendar_events_for_period(start_date=None, end_date=None, max_results=20):
    """Get calendar events for a specific time period"""
    service = get_calendar_service()
    
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

def send_email(to_email: str, subject: str, body: str):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def reschedule_event(person: str, new_time: str):
    service = get_calendar_service()

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

def create_calendar_event(summary: str, start_time: str, end_time: str = None, description: str = "", location: str = "", attendees: List[str] = None):
    """Create a new calendar event"""
    service = get_calendar_service()
    
    try:
        # Parse start time
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        
        # Set end time (default to 1 hour later if not provided)
        if end_time:
            end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        # Prepare event data
        event_data = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC',
            },
        }
        
        # Add attendees if provided
        if attendees:
            event_data['attendees'] = [{'email': email.strip()} for email in attendees if email.strip()]
        
        # Create the event
        event = service.events().insert(
            calendarId='primary',
            body=event_data
        ).execute()
        
        # Format response
        event_link = event.get('htmlLink', '')
        start_formatted = start_dt.strftime('%Y-%m-%d %H:%M')
        end_formatted = end_dt.strftime('%H:%M')
        
        response = f"✅ Calendar event created successfully!\n\n"
        response += f"📅 **{summary}**\n"
        response += f"🕐 **{start_formatted} - {end_formatted}**\n"
        if location:
            response += f"📍 **{location}**\n"
        if attendees:
            response += f"👥 **Attendees:** {', '.join(attendees)}\n"
        if description:
            response += f"📝 **Description:** {description}\n"
        response += f"\n🔗 [View in Calendar]({event_link})"
        
        return response
        
    except ValueError as e:
        return f"⚠️ Invalid date/time format. Please use 'YYYY-MM-DD HH:MM' format. Error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating calendar event: {str(e)}"

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
