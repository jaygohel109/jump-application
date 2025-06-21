import os
import pickle
import base64
from datetime import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
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

def get_recent_emails(max_results=5):
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me", maxResults=max_results, q="is:inbox"
    ).execute()
    messages = results.get("messages", [])
    email_summaries = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")

        body = ""
        parts = msg_data["payload"].get("parts", [])
        for part in parts:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
        if not body:
            body = msg_data.get("snippet", "")

        summary = (
            f"From: {sender}\n"
            f"Date: {date}\n"
            f"Subject: {subject}\n"
            f"Body: {body.strip()[:1000]}"
        )
        email_summaries.append(summary)

    return [f"Email #{i+1}:\n{email}" for i, email in enumerate(email_summaries)]


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
        start = event['start'].get('dateTime', event['start'].get('date'))
        upcoming.append(f"{event.get('summary', 'No Title')} at {start}")

    return upcoming

from email.mime.text import MIMEText

def send_email(to_email: str, body: str):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = "Message from your advisor"
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
