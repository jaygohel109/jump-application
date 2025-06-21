# backend/app/services/hubspot.py
import pickle
import httpx
import time
from typing import List, Dict, Any
from app import config

def get_hubspot_token():
    """Get HubSpot access token from saved file, refresh if expired"""
    try:
        with open("hubspot_tokens.pickle", "rb") as token_file:
            token_data = pickle.load(token_file)
            
            # Check if token is expired (expires_in is in seconds)
            current_time = int(time.time())
            token_expiry = token_data.get("expires_at", 0)  # We'll set this when saving
            
            # If token is expired or will expire in next 5 minutes, refresh it
            if current_time >= (token_expiry - 300):
                return refresh_hubspot_token(token_data.get("refresh_token"))
            
            return token_data.get("access_token")
    except FileNotFoundError:
        return None

def refresh_hubspot_token(refresh_token: str) -> str:
    """Refresh HubSpot access token using refresh token"""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "client_id": config.settings.HUBSPOT_CLIENT_ID,
        "client_secret": config.settings.HUBSPOT_CLIENT_SECRET,
        "refresh_token": refresh_token
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://api.hubapi.com/oauth/v1/token",
                headers=headers,
                data=data
            )
            response.raise_for_status()
            token_data = response.json()
            
            # Add expiry timestamp
            token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 1800)
            
            # Save updated tokens
            with open("hubspot_tokens.pickle", "wb") as token_file:
                pickle.dump(token_data, token_file)
            
            return token_data.get("access_token")
    except Exception as e:
        print(f"Error refreshing HubSpot token: {str(e)}")
        return None

def get_hubspot_contacts() -> List[Dict[str, Any]]:
    """Get recent contacts from HubSpot"""
    token = get_hubspot_token()
    if not token:
        return "HubSpot not connected. Please connect your HubSpot account first."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                params={"limit": 10}
            )
            response.raise_for_status()
            data = response.json()
            
            contacts = []
            for contact in data.get("results", []):
                properties = contact.get("properties", {})
                contacts.append({
                    "id": contact.get("id"),
                    "email": properties.get("email"),
                    "firstname": properties.get("firstname"),
                    "lastname": properties.get("lastname"),
                    "company": properties.get("company")
                })
            
            return contacts
    except Exception as e:
        return f"Error fetching HubSpot contacts: {str(e)}"

def create_hubspot_note(contact_email: str, note_content: str) -> str:
    """Create a note for a HubSpot contact"""
    token = get_hubspot_token()
    if not token:
        return "HubSpot not connected. Please connect your HubSpot account first."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # First, find the contact by email
        with httpx.Client() as client:
            # Search for contact by email
            search_response = client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers=headers,
                json={
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": contact_email
                        }]
                    }]
                }
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("results"):
                return f"No contact found with email: {contact_email}"
            
            contact_id = search_data["results"][0]["id"]
            
            # Create note for the contact
            note_response = client.post(
                "https://api.hubapi.com/crm/v3/objects/notes",
                headers=headers,
                json={
                    "properties": {
                        "hs_note_body": note_content,
                        "hs_timestamp": str(int(time.time() * 1000))
                    },
                    "associations": [{
                        "to": {
                            "id": contact_id
                        },
                        "types": [{
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 1
                        }]
                    }]
                }
            )
            note_response.raise_for_status()
            
            return f"✅ Note created successfully for {contact_email}: {note_content}"
            
    except Exception as e:
        return f"Error creating HubSpot note: {str(e)}"

def get_hubspot_contact_notes(contact_email: str) -> str:
    """Get notes for a specific HubSpot contact"""
    token = get_hubspot_token()
    if not token:
        return "HubSpot not connected. Please connect your HubSpot account first."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client() as client:
            # First find the contact
            search_response = client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers=headers,
                json={
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": contact_email
                        }]
                    }]
                }
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("results"):
                return f"No contact found with email: {contact_email}"
            
            contact_id = search_data["results"][0]["id"]
            
            # Get notes for the contact
            notes_response = client.get(
                f"https://api.hubapi.com/crm/v3/objects/notes",
                headers=headers,
                params={
                    "associations.contact": contact_id,
                    "limit": 10
                }
            )
            notes_response.raise_for_status()
            notes_data = notes_response.json()
            
            notes = []
            for note in notes_data.get("results", []):
                notes.append({
                    "id": note.get("id"),
                    "content": note.get("properties", {}).get("hs_note_body"),
                    "created": note.get("properties", {}).get("hs_timestamp")
                })
            
            return notes
            
    except Exception as e:
        return f"Error fetching HubSpot notes: {str(e)}" 