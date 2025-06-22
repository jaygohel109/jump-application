from openai import OpenAI
from typing import List, Dict, Any
import os
from app.database import db

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EmbeddingService:
    def __init__(self):
        self.client = client
        self.model = "text-embedding-3-small"  # Using the smaller, faster model
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text string"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return []
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in batch"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            return [[] for _ in texts]
    
    def create_email_embedding(self, email_data: Dict[str, Any]) -> bool:
        """Create and store embedding for an email"""
        try:
            # Create improved text representation of email with better structure
            sender = email_data.get('sender', '').lower()
            recipient = email_data.get('recipient', '').lower()
            subject = email_data.get('subject', '').lower()
            content = email_data.get('content', '').lower()
            date = email_data.get('date', '')
            
            # Extract email addresses and names from sender/recipient
            sender_email = sender
            sender_name = sender
            if '<' in sender and '>' in sender:
                sender_name = sender.split('<')[0].strip()
                sender_email = sender.split('<')[1].split('>')[0].strip()
            
            recipient_email = recipient
            recipient_name = recipient
            if '<' in recipient and '>' in recipient:
                recipient_name = recipient.split('<')[0].strip()
                recipient_email = recipient.split('<')[1].split('>')[0].strip()
            
            email_text = (
                f"EMAIL RECORD\n"
                f"FROM: {sender_name} {sender_email}\n"
                f"TO: {recipient_name} {recipient_email}\n"
                f"SUBJECT: {subject}\n"
                f"DATE: {date}\n"
                f"BODY: {content}\n"
            )
            
            # Get embedding
            embedding = self.get_embedding(email_text.strip())
            if not embedding:
                return False
            
            # Store in database
            result = db.save_email_embedding(email_data, embedding)
            return result is not None
            
        except Exception as e:
            print(f"Error creating email embedding: {e}")
            return False
    
    def create_hubspot_embedding(self, contact_data: Dict[str, Any]) -> bool:
        """Create and store embedding for HubSpot data"""
        try:
            print(f"Creating HubSpot embedding for: {contact_data}")
            # Create improved text representation of HubSpot data
            # Handle None values by converting to empty strings first
            name = (contact_data.get('name') or '').lower()
            email = (contact_data.get('email') or '').lower()
            content_type = (contact_data.get('content_type') or '').lower()
            content = (contact_data.get('content') or '').lower()
            phone = (contact_data.get('phone') or '').lower()
            company = (contact_data.get('company') or '').lower()
            job_title = (contact_data.get('job_title') or '').lower()
            address = (contact_data.get('address') or '').lower()
            website = (contact_data.get('website') or '').lower()
            
            # Extract name and email if they're combined
            contact_name = name
            contact_email = email
            if '@' in name and ' ' not in name:
                contact_email = name
                contact_name = name.split('@')[0]
            
            hubspot_text = (
                f"HUBSPOT RECORD\n"
                f"CONTACT NAME: {contact_name}\n"
                f"CONTACT EMAIL: {contact_email}\n"
                f"RECORD TYPE: {content_type}\n"
                f"CONTENT: {content}\n"
                f"PHONE: {phone}\n"
                f"COMPANY: {company}\n"
                f"JOB TITLE: {job_title}\n"
                f"ADDRESS: {address}\n"
                f"WEBSITE: {website}\n"
            )
            
            # Get embedding
            embedding = self.get_embedding(hubspot_text.strip())
            if not embedding:
                return False
            
            # Store in database
            result = db.save_hubspot_embedding(contact_data, embedding)
            return result is not None
            
        except Exception as e:
            print(f"Error creating HubSpot embedding: {e}")
            print(f"Contact data that caused error: {contact_data}")
            return False
    
    def create_calendar_embedding(self, event_data: Dict[str, Any]) -> bool:
        """Create and store embedding for calendar event"""
        try:
            # Create improved text representation of calendar event
            summary = event_data.get('summary', '').lower()
            description = event_data.get('description', '').lower()
            start_time = event_data.get('start_time', '')
            end_time = event_data.get('end_time', '')
            location = event_data.get('location', '').lower()
            attendees = event_data.get('attendees', [])
            
            # Format attendees
            attendee_text = ", ".join(attendees) if attendees else "no attendees"
            
            # Enhanced calendar text format for better semantic understanding
            calendar_text = (
                f"Calendar event '{summary}' from {start_time} to {end_time}. "
                f"Location: {location}. Attendees: {attendee_text}. "
                f"Description: {description}"
            )
            
            # Get embedding
            embedding = self.get_embedding(calendar_text.strip())
            if not embedding:
                return False
            
            # Store in database
            result = db.save_calendar_embedding(event_data, embedding)
            return result is not None
            
        except Exception as e:
            print(f"Error creating calendar embedding: {e}")
            return False
    
    def search_similar_emails(self, query: str, limit: int = 5, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search for similar emails using RAG"""
        try:
            # Get embedding for query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # Search in database
            results = db.search_emails(query_embedding, limit, threshold)
            return results
            
        except Exception as e:
            print(f"Error searching emails: {e}")
            return []
    
    def search_similar_hubspot_data(self, query: str, limit: int = 5, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search for similar HubSpot data using RAG"""
        try:
            # Get embedding for query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # Search in database
            results = db.search_hubspot_data(query_embedding, limit, threshold)
            return results
            
        except Exception as e:
            print(f"Error searching HubSpot data: {e}")
            return []
    
    def search_similar_calendar_events(self, query: str, limit: int = 5, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search for similar calendar events using RAG"""
        try:
            # Get embedding for query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # Search in database
            results = db.search_calendar_events(query_embedding, limit, threshold)
            return results
            
        except Exception as e:
            print(f"Error searching calendar events: {e}")
            return []
    
    def bulk_import_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk import emails with embeddings"""
        success_count = 0
        error_count = 0
        
        for email in emails:
            if self.create_email_embedding(email):
                success_count += 1
            else:
                error_count += 1
        
        return {
            "success": success_count,
            "errors": error_count,
            "total": len(emails)
        }
    
    def bulk_import_hubspot_data(self, contacts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk import HubSpot data with embeddings"""
        success_count = 0
        error_count = 0
        
        for contact in contacts:
            if self.create_hubspot_embedding(contact):
                success_count += 1
            else:
                error_count += 1
        
        return {
            "success": success_count,
            "errors": error_count,
            "total": len(contacts)
        }
    
    def bulk_import_calendar_events(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk import calendar events with embeddings"""
        success_count = 0
        error_count = 0
        
        for event in events:
            if self.create_calendar_embedding(event):
                success_count += 1
            else:
                error_count += 1
        
        return {
            "success": success_count,
            "errors": error_count,
            "total": len(events)
        }
    
    def hybrid_search_emails(self, query: str, limit: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Hybrid search: Combine vector search with keyword search for emails"""
        try:
            results = []
            
            # 1. Vector search
            vector_results = self.search_similar_emails(query, limit * 2, threshold)
            results.extend(vector_results)
            
            # 2. Keyword search for specific patterns
            query_lower = query.lower()
            
            # Extract potential names/emails from query
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_in_query = re.findall(email_pattern, query_lower)
            
            # Extract potential names (words that could be names)
            words = query_lower.split()
            potential_names = [word for word in words if len(word) > 2 and word not in ['from', 'to', 'email', 'about', 'with', 'the', 'and', 'for']]
            
            # Keyword search in database
            if emails_in_query or potential_names:
                keyword_results = db.keyword_search_emails(emails_in_query, potential_names, limit)
                results.extend(keyword_results)
            
            # 3. Remove duplicates and rank results
            seen_ids = set()
            unique_results = []
            for result in results:
                result_id = result.get('id') or result.get('email_id')
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"Error in hybrid email search: {e}")
            # Fallback to vector search only
            return self.search_similar_emails(query, limit, threshold)
    
    def hybrid_search_hubspot_data(self, query: str, limit: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Hybrid search: Combine vector search with keyword search for HubSpot data"""
        try:
            # Debug logging
            print(f"\n🔍 DEBUG: Hybrid HubSpot Search")
            print(f"Query: '{query}'")
            print(f"Limit: {limit}, Threshold: {threshold}")
            
            results = []
            
            # 1. Vector search
            print("1. Performing vector search...")
            vector_results = self.search_similar_hubspot_data(query, limit * 2, threshold)
            print(f"   Vector search found {len(vector_results)} results")
            results.extend(vector_results)
            
            # 2. Keyword search for specific patterns
            print("2. Performing keyword search...")
            query_lower = query.lower()
            
            # Extract potential names/emails from query
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_in_query = re.findall(email_pattern, query_lower)
            
            # Extract potential names
            words = query_lower.split()
            potential_names = [word for word in words if len(word) > 2 and word not in ['contact', 'hubspot', 'about', 'with', 'the', 'and', 'for']]
            
            print(f"   Emails found in query: {emails_in_query}")
            print(f"   Potential names found: {potential_names}")
            
            # Keyword search in database
            if emails_in_query or potential_names:
                keyword_results = db.keyword_search_hubspot_data(emails_in_query, potential_names, limit)
                print(f"   Keyword search found {len(keyword_results)} results")
                results.extend(keyword_results)
            else:
                print("   No keywords to search for")
            
            # 3. Remove duplicates and rank results
            print("3. Removing duplicates...")
            seen_ids = set()
            unique_results = []
            for result in results:
                result_id = result.get('id') or result.get('contact_id')
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
            
            final_results = unique_results[:limit]
            print(f"Final results: {len(final_results)} unique records")
            print("=" * 50)
            
            return final_results
            
        except Exception as e:
            print(f"Error in hybrid HubSpot search: {e}")
            # Fallback to vector search only
            return self.search_similar_hubspot_data(query, limit, threshold)
    
    def hybrid_search_calendar_events(self, query: str, limit: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Hybrid search: Combine vector search with keyword search for calendar events"""
        try:
            results = []
            
            # 1. Vector search
            vector_results = self.search_similar_calendar_events(query, limit * 2, threshold)
            results.extend(vector_results)
            
            # 2. Keyword search for specific patterns
            query_lower = query.lower()
            
            # Extract potential names/emails from query
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_in_query = re.findall(email_pattern, query_lower)
            
            # Extract potential names
            words = query_lower.split()
            potential_names = [word for word in words if len(word) > 2 and word not in ['meeting', 'calendar', 'event', 'about', 'with', 'the', 'and', 'for', 'this', 'month', 'next', 'week']]
            
            # Keyword search in database
            if emails_in_query or potential_names:
                keyword_results = db.keyword_search_calendar_events(emails_in_query, potential_names, limit)
                results.extend(keyword_results)
            
            # 3. Remove duplicates and rank results
            seen_ids = set()
            unique_results = []
            for result in results:
                result_id = result.get('id') or result.get('event_id')
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"Error in hybrid calendar search: {e}")
            # Fallback to vector search only
            return self.search_similar_calendar_events(query, limit, threshold)

# Global embedding service instance
embedding_service = EmbeddingService() 