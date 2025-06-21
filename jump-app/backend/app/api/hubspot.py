# backend/app/api/hubspot.py
from fastapi import APIRouter, HTTPException
from app.services.hubspot import get_hubspot_contacts, create_hubspot_note, get_hubspot_contact_notes, get_hubspot_token
from typing import List, Dict, Any

router = APIRouter()

@router.get("/contacts")
async def get_contacts():
    """Get HubSpot contacts using saved tokens"""
    try:
        contacts = get_hubspot_contacts()
        if isinstance(contacts, str) and "not connected" in contacts.lower():
            raise HTTPException(status_code=401, detail="HubSpot not connected. Please authenticate first.")
        return {"contacts": contacts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notes")
async def create_note(contact_email: str, note_content: str):
    """Create a note for a HubSpot contact"""
    try:
        result = create_hubspot_note(contact_email, note_content)
        if "not connected" in result.lower():
            raise HTTPException(status_code=401, detail="HubSpot not connected. Please authenticate first.")
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notes/{contact_email}")
async def get_contact_notes(contact_email: str):
    """Get notes for a specific HubSpot contact"""
    try:
        notes = get_hubspot_contact_notes(contact_email)
        if isinstance(notes, str) and "not connected" in notes.lower():
            raise HTTPException(status_code=401, detail="HubSpot not connected. Please authenticate first.")
        return {"notes": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token-status")
async def check_token_status():
    """Check if HubSpot token is available and valid"""
    try:
        token = get_hubspot_token()
        if token:
            return {"status": "connected", "message": "HubSpot token is available"}
        else:
            return {"status": "disconnected", "message": "HubSpot not connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)} 