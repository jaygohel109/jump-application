from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.ai_agent import ai_agent
from app.services.google import get_recent_emails, get_upcoming_events
from app.services.hubspot import get_hubspot_contacts
import json
import os

router = APIRouter()

class WebhookRequest(BaseModel):
    type: str
    data: Dict[str, Any]

@router.post("/gmail")
async def gmail_webhook(request: Request):
    """Handle Gmail webhook notifications"""
    try:
        # Get the webhook payload
        payload = await request.json()
        
        # Extract email data
        email_data = extract_email_from_webhook(payload)
        
        if email_data:
            # Process the email proactively
            result = ai_agent.process_incoming_email(email_data)
            return {"status": "success", "message": result}
        else:
            return {"status": "no_email_data", "message": "No email data found in webhook"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendar")
async def calendar_webhook(request: Request):
    """Handle Google Calendar webhook notifications"""
    try:
        # Get the webhook payload
        payload = await request.json()
        
        # Extract event data
        event_data = extract_event_from_webhook(payload)
        
        if event_data:
            # Process the calendar event proactively
            result = ai_agent.process_calendar_event(event_data)
            return {"status": "success", "message": result}
        else:
            return {"status": "no_event_data", "message": "No event data found in webhook"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hubspot")
async def hubspot_webhook(request: Request):
    """Handle HubSpot webhook notifications"""
    try:
        # Get the webhook payload
        payload = await request.json()
        
        # Extract HubSpot data
        hubspot_data = extract_hubspot_from_webhook(payload)
        
        if hubspot_data:
            # Process the HubSpot data proactively
            result = process_hubspot_webhook(hubspot_data)
            return {"status": "success", "message": result}
        else:
            return {"status": "no_hubspot_data", "message": "No HubSpot data found in webhook"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/poll")
async def poll_for_updates():
    """Poll for updates from Gmail, Calendar, and HubSpot"""
    try:
        results = {}
        
        # Poll for new emails
        try:
            emails = get_recent_emails(5)
            if emails:
                for email in emails:
                    ai_agent.process_incoming_email(email)
                results["emails"] = f"Processed {len(emails)} emails"
        except Exception as e:
            results["emails"] = f"Error processing emails: {str(e)}"
        
        # Poll for new calendar events
        try:
            events = get_upcoming_events(5)
            if events:
                for event in events:
                    ai_agent.process_calendar_event(event)
                results["calendar"] = f"Processed {len(events)} events"
        except Exception as e:
            results["calendar"] = f"Error processing calendar events: {str(e)}"
        
        # Poll for new HubSpot data
        try:
            contacts = get_hubspot_contacts()
            if contacts:
                # Process new contacts
                results["hubspot"] = f"Found {len(contacts)} contacts"
        except Exception as e:
            results["hubspot"] = f"Error processing HubSpot data: {str(e)}"
        
        return {"status": "success", "results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def extract_email_from_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract email data from Gmail webhook payload"""
    try:
        # This is a simplified extraction - real Gmail webhooks have more complex structure
        if "message" in payload:
            message = payload["message"]
            return {
                "id": message.get("id"),
                "subject": message.get("subject", ""),
                "sender": message.get("from", ""),
                "recipient": message.get("to", ""),
                "content": message.get("body", ""),
                "date": message.get("date", "")
            }
        return None
    except Exception as e:
        print(f"Error extracting email from webhook: {e}")
        return None

def extract_event_from_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract event data from Calendar webhook payload"""
    try:
        # This is a simplified extraction - real Calendar webhooks have more complex structure
        if "event" in payload:
            event = payload["event"]
            return {
                "id": event.get("id"),
                "summary": event.get("summary", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
                "attendees": event.get("attendees", []),
                "description": event.get("description", "")
            }
        return None
    except Exception as e:
        print(f"Error extracting event from webhook: {e}")
        return None

def extract_hubspot_from_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract HubSpot data from webhook payload"""
    try:
        # This is a simplified extraction - real HubSpot webhooks have more complex structure
        if "contact" in payload:
            contact = payload["contact"]
            return {
                "id": contact.get("id"),
                "email": contact.get("email", ""),
                "name": contact.get("name", ""),
                "content_type": "contact",
                "content": f"Contact: {contact.get('name', '')} - {contact.get('email', '')}"
            }
        elif "note" in payload:
            note = payload["note"]
            return {
                "id": note.get("id"),
                "contact_id": note.get("contact_id"),
                "content_type": "note",
                "content": note.get("content", "")
            }
        return None
    except Exception as e:
        print(f"Error extracting HubSpot data from webhook: {e}")
        return None

def process_hubspot_webhook(hubspot_data: Dict[str, Any]) -> str:
    """Process HubSpot webhook data"""
    try:
        from app.services.embeddings import embedding_service
        
        # Create embedding for the HubSpot data
        embedding_service.create_hubspot_embedding(hubspot_data)
        
        return f"✅ HubSpot {hubspot_data.get('content_type', 'data')} processed and stored"
        
    except Exception as e:
        return f"Error processing HubSpot data: {str(e)}"

@router.get("/health")
async def webhook_health():
    """Health check for webhooks"""
    return {"status": "healthy", "message": "Webhook endpoints are working"} 