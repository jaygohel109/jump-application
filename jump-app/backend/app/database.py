from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta
import json

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# Database table names
TABLES = {
    "tasks": "tasks",
    "ongoing_instructions": "ongoing_instructions", 
    "email_embeddings": "email_embeddings",
    "hubspot_embeddings": "hubspot_embeddings",
    "conversation_history": "conversation_history",
    "calendar_embeddings": "calendar_embeddings"
}

class DatabaseManager:
    def __init__(self):
        self.supabase = supabase
    
    # Task Management
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task in the database"""
        task = {
            "title": task_data.get("title"),
            "description": task_data.get("description"),
            "status": "pending",
            "priority": task_data.get("priority", "medium"),
            "assigned_to": task_data.get("assigned_to"),
            "due_date": task_data.get("due_date"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": json.dumps(task_data.get("metadata", {}))
        }
        
        result = self.supabase.table(TABLES["tasks"]).insert(task).execute()
        return result.data[0] if result.data else None
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        result = self.supabase.table(TABLES["tasks"]).select("*").eq("id", task_id).execute()
        return result.data[0] if result.data else None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a task"""
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = self.supabase.table(TABLES["tasks"]).update(updates).eq("id", task_id).execute()
        return result.data[0] if result.data else None
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks"""
        result = self.supabase.table(TABLES["tasks"]).select("*").eq("status", "pending").execute()
        return result.data
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get tasks by status"""
        result = self.supabase.table(TABLES["tasks"]).select("*").eq("status", status).execute()
        return result.data
    
    # Ongoing Instructions
    def save_ongoing_instruction(self, instruction: str, category: str = "general") -> Dict[str, Any]:
        """Save an ongoing instruction"""
        instruction_data = {
            "instruction": instruction,
            "category": category,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table(TABLES["ongoing_instructions"]).insert(instruction_data).execute()
        return result.data[0] if result.data else None
    
    def get_active_instructions(self, category: str = None) -> List[Dict[str, Any]]:
        """Get all active ongoing instructions"""
        query = self.supabase.table(TABLES["ongoing_instructions"]).select("*").eq("is_active", True)
        if category:
            query = query.eq("category", category)
        result = query.execute()
        return result.data
    
    def deactivate_instruction(self, instruction_id: str) -> bool:
        """Deactivate an ongoing instruction"""
        result = self.supabase.table(TABLES["ongoing_instructions"]).update({
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", instruction_id).execute()
        return len(result.data) > 0
    
    # Email Embeddings (RAG)
    def save_email_embedding(self, email_data: Dict[str, Any], embedding: List[float]) -> Dict[str, Any]:
        """Save email content with its embedding for RAG"""
        embedding_data = {
            "email_id": email_data.get("id"),
            "subject": email_data.get("subject"),
            "sender": email_data.get("sender"),
            "recipient": email_data.get("recipient"),
            "content": email_data.get("content"),
            "date": email_data.get("date"),
            "embedding": embedding,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table(TABLES["email_embeddings"]).insert(embedding_data).execute()
        return result.data[0] if result.data else None
    
    def search_emails(self, query_embedding: List[float], limit: int = 5, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search emails using vector similarity"""
        # Use the match_emails function we created in the database
        result = self.supabase.rpc(
            'match_emails',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }
        ).execute()
        return result.data
    
    def get_recent_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent emails without vector search"""
        result = self.supabase.table(TABLES["email_embeddings"]).select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    # HubSpot Embeddings (RAG)
    def save_hubspot_embedding(self, contact_data: Dict[str, Any], embedding: List[float]) -> Dict[str, Any]:
        """Save HubSpot contact/note content with its embedding for RAG"""
        embedding_data = {
            "contact_id": contact_data.get("id"),
            "contact_email": contact_data.get("email"),
            "contact_name": contact_data.get("name"),
            "content_type": contact_data.get("content_type"),  # "contact" or "note"
            "content": contact_data.get("content"),
            "embedding": embedding,
            "phone": contact_data.get("phone"),
            "company": contact_data.get("company"),
            "job_title": contact_data.get("job_title"),
            "address": contact_data.get("address"),
            "website": contact_data.get("website"),
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table(TABLES["hubspot_embeddings"]).insert(embedding_data).execute()
        return result.data[0] if result.data else None
    
    def search_hubspot_data(self, query_embedding: List[float], limit: int = 5, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search HubSpot data using vector similarity"""
        # Use the match_hubspot_data function we created in the database
        result = self.supabase.rpc(
            'match_hubspot_data',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }
        ).execute()
        return result.data
    
    def get_recent_hubspot_data(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent HubSpot data without vector search"""
        result = self.supabase.table(TABLES["hubspot_embeddings"]).select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    def keyword_search_hubspot_data(self, emails: List[str], names: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Keyword search for HubSpot data by email addresses or names"""
        try:
            results = []
            
            # Search by email addresses
            for email in emails:
                result = self.supabase.table(TABLES["hubspot_embeddings"]).select("*").ilike("contact_email", f"%{email}%").limit(limit).execute()
                if result.data:
                    results.extend(result.data)
            
            # Search by names
            for name in names:
                result = self.supabase.table(TABLES["hubspot_embeddings"]).select("*").ilike("contact_name", f"%{name}%").limit(limit).execute()
                if result.data:
                    results.extend(result.data)
                
                result = self.supabase.table(TABLES["hubspot_embeddings"]).select("*").ilike("content", f"%{name}%").limit(limit).execute()
                if result.data:
                    results.extend(result.data)
            
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for result in results:
                if result.get('id') not in seen_ids:
                    seen_ids.add(result.get('id'))
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"Error in keyword HubSpot search: {e}")
            return []
    
    # Conversation History
    def save_conversation(self, user_id: str, message: str, response: str, context: str = "") -> Dict[str, Any]:
        """Save conversation history"""
        conversation_data = {
            "user_id": user_id,
            "user_message": message,
            "agent_response": response,
            "context": context,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table(TABLES["conversation_history"]).insert(conversation_data).execute()
        return result.data[0] if result.data else None
    
    def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history for a user"""
        result = self.supabase.table(TABLES["conversation_history"]).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    # Utility methods
    def clear_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clear old data from all tables"""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Clear old conversations
        conv_result = self.supabase.table(TABLES["conversation_history"]).delete().lt("created_at", cutoff_date).execute()
        
        # Clear old email embeddings (keep recent ones)
        email_result = self.supabase.table(TABLES["email_embeddings"]).delete().lt("created_at", cutoff_date).execute()
        
        # Clear old hubspot embeddings (keep recent ones)
        hubspot_result = self.supabase.table(TABLES["hubspot_embeddings"]).delete().lt("created_at", cutoff_date).execute()
        
        return {
            "conversations_deleted": len(conv_result.data) if conv_result.data else 0,
            "emails_deleted": len(email_result.data) if email_result.data else 0,
            "hubspot_data_deleted": len(hubspot_result.data) if hubspot_result.data else 0
        }
    
    # Calendar Embeddings (RAG)
    def save_calendar_embedding(self, event_data: Dict[str, Any], embedding: List[float]) -> Dict[str, Any]:
        """Save calendar event with its embedding for RAG"""
        embedding_data = {
            "event_id": event_data.get("id"),
            "summary": event_data.get("summary"),
            "description": event_data.get("description"),
            "start_time": event_data.get("start_time"),
            "end_time": event_data.get("end_time"),
            "attendees": event_data.get("attendees", []),
            "location": event_data.get("location"),
            "embedding": embedding,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table(TABLES["calendar_embeddings"]).insert(embedding_data).execute()
        return result.data[0] if result.data else None
    
    def search_calendar_events(self, query_embedding: List[float], limit: int = 5, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search calendar events using vector similarity"""
        result = self.supabase.rpc(
            'match_calendar_events',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }
        ).execute()
        return result.data
    
    def get_recent_calendar_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent calendar events without vector search"""
        result = self.supabase.table(TABLES["calendar_embeddings"]).select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    def keyword_search_calendar_events(self, emails: List[str], names: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Keyword search for calendar events by email addresses or names"""
        try:
            results = []
            
            # Search by attendee emails
            for email in emails:
                result = self.supabase.table(TABLES["calendar_embeddings"]).select("*").contains("attendees", [email]).limit(limit).execute()
                if result.data:
                    results.extend(result.data)
            
            # Search by names in summary/description
            for name in names:
                result = self.supabase.table(TABLES["calendar_embeddings"]).select("*").ilike("summary", f"%{name}%").limit(limit).execute()
                if result.data:
                    results.extend(result.data)
                
                result = self.supabase.table(TABLES["calendar_embeddings"]).select("*").ilike("description", f"%{name}%").limit(limit).execute()
                if result.data:
                    results.extend(result.data)
            
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for result in results:
                if result.get('id') not in seen_ids:
                    seen_ids.add(result.get('id'))
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"Error in keyword calendar search: {e}")
            return []

# Global database manager instance
db = DatabaseManager() 