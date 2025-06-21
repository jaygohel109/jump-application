import pytest
from app.tools import get_recent_emails, get_upcoming_events, send_email, reschedule_event

@pytest.fixture
def mock_email_data():
    return [
        {"subject": "Meeting Reminder", "sender": "john@example.com", "date": "2025-06-08"},
        {"subject": "Project Update", "sender": "jane@example.com", "date": "2025-06-07"},
    ]

@pytest.fixture
def mock_event_data():
    return [
        {"title": "Team Meeting", "date": "2025-06-10", "time": "10:00 AM"},
        {"title": "Client Call", "date": "2025-06-11", "time": "2:00 PM"},
    ]

def test_get_recent_emails(mock_email_data):
    emails = get_recent_emails()
    assert len(emails) == 5
    assert emails[0]["subject"] == "Meeting Reminder"

def test_get_upcoming_events(mock_event_data):
    events = get_upcoming_events()
    assert len(events) == 5
    assert events[0]["title"] == "Team Meeting"

def test_send_email():
    response = send_email("recipient@example.com", "Subject", "Body")
    assert response["status"] == "success"

def test_reschedule_event():
    response = reschedule_event("event_id", "2025-06-12", "3:00 PM")
    assert response["status"] == "success"