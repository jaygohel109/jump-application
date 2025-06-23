# backend/app/services/hubspot.py
import os
import sys
sys.path.append("..")  
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import time
from app.database import db

HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

def get_hubspot_oauth_url() -> str:
    """Get HubSpot OAuth URL"""
    client_id = os.getenv("HUBSPOT_CLIENT_ID")
    redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI", "http://127.0.0.1:8000/auth/hubspot/callback")
    
    return f"https://app.hubspot.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=crm.objects.contacts.read%20crm.objects.contacts.write"

async def exchange_hubspot_code(code: str) -> Optional[Dict[str, Any]]:
    """Exchange authorization code for HubSpot tokens"""
    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "client_id": os.getenv("HUBSPOT_CLIENT_ID"),
            "client_secret": os.getenv("HUBSPOT_CLIENT_SECRET"),
            "redirect_uri": os.getenv("HUBSPOT_REDIRECT_URI", "http://127.0.0.1:8000/auth/hubspot/callback"),
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(HUBSPOT_TOKEN_URL, headers=headers, data=data)
            resp.raise_for_status()
            token_data = resp.json()
            
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in", 3600)
            }
    except Exception as e:
        print(f"Error exchanging HubSpot code: {e}")
        return None

def get_hubspot_token(email: str) -> Optional[str]:
    """Get HubSpot access token for a user from database"""
    try:
        user = db.get_user_by_email(email)
        if not user or not user.get("hubspot_access_token"):
            return None
        
        # Check if token is expired
        expires_at = user.get("hubspot_token_expires_at")
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=expires_datetime.tzinfo) >= expires_datetime:
                # Token expired, try to refresh
                return refresh_hubspot_token(email)
        
        return user["hubspot_access_token"]
    except Exception as e:
        print(f"Error getting HubSpot token: {e}")
        return None

def refresh_hubspot_token(email: str) -> Optional[str]:
    """Refresh HubSpot token for a user"""
    try:
        user = db.get_user_by_email(email)
        if not user or not user.get("hubspot_refresh_token"):
            return None
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "client_id": os.getenv("HUBSPOT_CLIENT_ID"),
            "client_secret": os.getenv("HUBSPOT_CLIENT_SECRET"),
            "refresh_token": user["hubspot_refresh_token"]
        }
        
        with httpx.Client() as client:
            resp = client.post(HUBSPOT_TOKEN_URL, headers=headers, data=data)
            resp.raise_for_status()
            token_data = resp.json()
            
            # Update database with new tokens
            expires_at = (datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))).isoformat()
            db.update_hubspot_tokens(
                email,
                token_data["access_token"],
                token_data.get("refresh_token", user["hubspot_refresh_token"]),
                expires_at
            )
            
            return token_data["access_token"]
    except Exception as e:
        print(f"Error refreshing HubSpot token: {e}")
        return None

def get_hubspot_contacts(email: str) -> list:
    """Get HubSpot contacts for a user"""
    token = get_hubspot_token(email)
    if not token:
        return []
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                params={
                    "limit": 100,
                    "properties": [
                        "email",
                        "firstname",
                        "lastname",
                        "phone",
                        "mobilephone",
                        "jobtitle",
                        "company",
                        "website",
                        "address",
                        "city",
                        "state",
                        "zip",
                        "country",
                        "lifecyclestage",
                        "leadstatus",
                        "createdate",
                        "lastmodifieddate"
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()
            
            hubspot_data = []
            
            for contact in data.get("results", []):
                properties = contact.get("properties", {})
                contact_id = contact.get("id")
                contact_email = properties.get("email")
                
                # Create contact entry with detailed information
                firstname = properties.get('firstname', '')
                lastname = properties.get('lastname', '')
                contact_name = f"{firstname} {lastname}".strip()
                if not contact_name:
                    contact_name = contact_email or "Unknown Contact"
                
                # Get phone numbers (try multiple fields)
                phone = properties.get('phone') or properties.get('mobilephone') or 'N/A'
                
                # Get job title and company
                job_title = properties.get('jobtitle', 'N/A')
                company = properties.get('company', 'N/A')
                
                # Get address information
                address = properties.get('address', '')
                city = properties.get('city', '')
                state = properties.get('state', '')
                zip_code = properties.get('zip', '')
                country = properties.get('country', '')
                
                # Build full address
                full_address = []
                if address:
                    full_address.append(address)
                if city:
                    full_address.append(city)
                if state:
                    full_address.append(state)
                if zip_code:
                    full_address.append(zip_code)
                if country:
                    full_address.append(country)
                
                address_str = ', '.join(full_address) if full_address else 'N/A'
                
                # Create detailed content string
                content_parts = [
                    f"Contact: {contact_name}",
                    f"Email: {contact_email}",
                    f"Phone: {phone}",
                    f"Job Title: {job_title}",
                    f"Company: {company}",
                    f"Address: {address_str}",
                    f"Website: {properties.get('website', 'N/A')}",
                    f"Lifecycle Stage: {properties.get('lifecyclestage', 'N/A')}",
                    f"Lead Status: {properties.get('leadstatus', 'N/A')}",
                    f"Created: {properties.get('createdate', 'N/A')}",
                    f"Last Modified: {properties.get('lastmodifieddate', 'N/A')}"
                ]
                
                contact_content = '\n'.join(content_parts)
                
                contact_entry = {
                    "id": contact_id,
                    "name": contact_name,
                    "email": contact_email,
                    "content_type": "contact",
                    "content": contact_content,
                    # Add additional fields for easier access
                    "phone": phone,
                    "job_title": job_title,
                    "company": company,
                    "address": address_str,
                    "website": properties.get('website', 'N/A'),
                    "lifecycle_stage": properties.get('lifecyclestage', 'N/A'),
                    "lead_status": properties.get('leadstatus', 'N/A')
                }
                hubspot_data.append(contact_entry)
                
                # Get notes for this contact
                if contact_id:
                    try:
                        notes_response = client.get(
                            f"https://api.hubapi.com/crm/v3/objects/notes",
                            headers=headers,
                            params={
                                "associations.contact": contact_id,
                                "limit": 5
                            }
                        )
                        notes_response.raise_for_status()
                        notes_data = notes_response.json()
                        
                        for note in notes_data.get("results", []):
                            note_content = note.get("properties", {}).get("hs_note_body", "")
                            if note_content:
                                note_entry = {
                                    "id": f"{contact_id}_note_{note.get('id')}",
                                    "name": contact_name,
                                    "email": contact_email,
                                    "content_type": "note",
                                    "content": f"Note for {contact_name}: {note_content}"
                                }
                                hubspot_data.append(note_entry)
                    except Exception as e:
                        print(f"Error fetching notes for contact {contact_id}: {e}")
                        continue
            
            return hubspot_data
            
    except Exception as e:
        print(f"Error fetching HubSpot contacts: {str(e)}")
        return []

def create_hubspot_note(email: str, contact_email: str, note_content: str) -> str:
    """Create a note for a HubSpot contact"""
    token = get_hubspot_token(email)
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
                        "hs_note_body": note_content
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

def get_hubspot_contact_notes(email: str, contact_email: str) -> str:
    """Get notes for a specific HubSpot contact"""
    token = get_hubspot_token(email)
    if not token:
        return "HubSpot not connected. Please connect your HubSpot account first."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client() as client:
            # First, find the contact by email
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
                "https://api.hubapi.com/crm/v3/objects/notes",
                headers=headers,
                params={
                    "associations.contact": contact_id,
                    "limit": 10
                }
            )
            notes_response.raise_for_status()
            notes_data = notes_response.json()
            
            if not notes_data.get("results"):
                return f"No notes found for {contact_email}"
            
            notes_text = f"Notes for {contact_email}:\n\n"
            for note in notes_data["results"]:
                note_content = note.get("properties", {}).get("hs_note_body", "")
                if note_content:
                    notes_text += f"• {note_content}\n\n"
            
            return notes_text
            
    except Exception as e:
        return f"Error getting HubSpot notes: {str(e)}" 