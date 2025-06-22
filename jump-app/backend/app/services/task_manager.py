from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from app.database import db
from app.services.google import send_email, get_upcoming_events, reschedule_event
from app.services.hubspot import create_hubspot_note, get_hubspot_contacts
from app.services.embeddings import embedding_service

class TaskManager:
    def __init__(self):
        self.db = db
    
    def create_task(self, title: str, description: str, task_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new task"""
        task_data = {
            "title": title,
            "description": description,
            "task_type": task_type,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        return self.db.create_task(task_data)
    
    def schedule_appointment_task(self, contact_name: str, contact_email: str, preferred_times: List[str] = None) -> Dict[str, Any]:
        """Create a task for scheduling an appointment"""
        task_data = {
            "title": f"Schedule appointment with {contact_name}",
            "description": f"Need to schedule an appointment with {contact_name} ({contact_email})",
            "task_type": "appointment_scheduling",
            "metadata": {
                "contact_name": contact_name,
                "contact_email": contact_email,
                "preferred_times": preferred_times or [],
                "status": "waiting_for_response",
                "attempts": 0
            }
        }
        
        return self.db.create_task(task_data)
    
    def create_hubspot_contact_task(self, email: str, note_content: str) -> Dict[str, Any]:
        """Create a task for creating a HubSpot contact"""
        task_data = {
            "title": f"Create HubSpot contact for {email}",
            "description": f"Create contact in HubSpot and add note: {note_content}",
            "task_type": "hubspot_contact_creation",
            "metadata": {
                "email": email,
                "note_content": note_content,
                "status": "pending"
            }
        }
        
        return self.db.create_task(task_data)
    
    def create_email_response_task(self, email: str, subject: str, content: str) -> Dict[str, Any]:
        """Create a task for sending an email response"""
        task_data = {
            "title": f"Send email to {email}",
            "description": f"Subject: {subject}\nContent: {content}",
            "task_type": "email_response",
            "metadata": {
                "email": email,
                "subject": subject,
                "content": content,
                "status": "pending"
            }
        }
        
        return self.db.create_task(task_data)
    
    def execute_pending_tasks(self) -> List[Dict[str, Any]]:
        """Execute all pending tasks"""
        pending_tasks = self.db.get_pending_tasks()
        results = []
        
        for task in pending_tasks:
            try:
                result = self.execute_task(task)
                results.append(result)
            except Exception as e:
                # Update task status to failed
                self.db.update_task(task["id"], {
                    "status": "failed",
                    "metadata": json.dumps({
                        **json.loads(task.get("metadata", "{}")),
                        "error": str(e),
                        "failed_at": datetime.utcnow().isoformat()
                    })
                })
                results.append({
                    "task_id": task["id"],
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task"""
        task_type = task.get("metadata", {}).get("task_type") if isinstance(task.get("metadata"), dict) else None
        
        if not task_type and isinstance(task.get("metadata"), str):
            # Parse metadata if it's a JSON string
            try:
                metadata = json.loads(task.get("metadata", "{}"))
                task_type = metadata.get("task_type")
            except:
                task_type = None
        
        if task_type == "appointment_scheduling":
            return self.execute_appointment_scheduling(task)
        elif task_type == "hubspot_contact_creation":
            return self.execute_hubspot_contact_creation(task)
        elif task_type == "email_response":
            return self.execute_email_response(task)
        else:
            return {
                "task_id": task["id"],
                "status": "unknown_task_type",
                "error": f"Unknown task type: {task_type}"
            }
    
    def execute_appointment_scheduling(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute appointment scheduling task"""
        metadata = json.loads(task.get("metadata", "{}")) if isinstance(task.get("metadata"), str) else task.get("metadata", {})
        
        contact_name = metadata.get("contact_name")
        contact_email = metadata.get("contact_email")
        attempts = metadata.get("attempts", 0)
        
        if attempts >= 3:
            # Max attempts reached, mark as failed
            self.db.update_task(task["id"], {
                "status": "failed",
                "metadata": json.dumps({
                    **metadata,
                    "error": "Max attempts reached",
                    "failed_at": datetime.utcnow().isoformat()
                })
            })
            return {
                "task_id": task["id"],
                "status": "failed",
                "error": "Max attempts reached"
            }
        
        # Get available times from calendar
        events = get_upcoming_events(10)
        available_times = self.generate_available_times(events)
        
        # Send email with available times
        email_content = f"""
        Hi {contact_name},
        
        I'd be happy to schedule an appointment with you. Here are some available times:
        
        {available_times}
        
        Please let me know which time works best for you, or if you'd prefer a different time.
        
        Best regards,
        [Your Name]
        """
        
        try:
            send_email(contact_email, "Appointment Scheduling", email_content)
            
            # Update task metadata
            self.db.update_task(task["id"], {
                "status": "waiting_for_response",
                "metadata": json.dumps({
                    **metadata,
                    "attempts": attempts + 1,
                    "last_email_sent": datetime.utcnow().isoformat(),
                    "available_times_sent": available_times
                })
            })
            
            return {
                "task_id": task["id"],
                "status": "email_sent",
                "message": f"Appointment scheduling email sent to {contact_email}"
            }
            
        except Exception as e:
            return {
                "task_id": task["id"],
                "status": "failed",
                "error": str(e)
            }
    
    def execute_hubspot_contact_creation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HubSpot contact creation task"""
        metadata = json.loads(task.get("metadata", "{}")) if isinstance(task.get("metadata"), str) else task.get("metadata", {})
        
        email = metadata.get("email")
        note_content = metadata.get("note_content")
        
        try:
            result = create_hubspot_note(email, note_content)
            
            # Mark task as completed
            self.db.update_task(task["id"], {
                "status": "completed",
                "metadata": json.dumps({
                    **metadata,
                    "completed_at": datetime.utcnow().isoformat(),
                    "result": result
                })
            })
            
            return {
                "task_id": task["id"],
                "status": "completed",
                "message": f"HubSpot contact/note created for {email}"
            }
            
        except Exception as e:
            return {
                "task_id": task["id"],
                "status": "failed",
                "error": str(e)
            }
    
    def execute_email_response(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email response task"""
        metadata = json.loads(task.get("metadata", "{}")) if isinstance(task.get("metadata"), str) else task.get("metadata", {})
        
        email = metadata.get("email")
        subject = metadata.get("subject")
        content = metadata.get("content")
        
        try:
            send_email(email, subject, content)
            
            # Mark task as completed
            self.db.update_task(task["id"], {
                "status": "completed",
                "metadata": json.dumps({
                    **metadata,
                    "completed_at": datetime.utcnow().isoformat()
                })
            })
            
            return {
                "task_id": task["id"],
                "status": "completed",
                "message": f"Email sent to {email}"
            }
            
        except Exception as e:
            return {
                "task_id": task["id"],
                "status": "failed",
                "error": str(e)
            }
    
    def generate_available_times(self, events: List[str]) -> str:
        """Generate available time slots based on calendar events"""
        # This is a simplified version - in a real implementation, you'd parse the events
        # and find actual available time slots
        
        available_times = [
            "Monday, 2:00 PM - 3:00 PM",
            "Tuesday, 10:00 AM - 11:00 AM", 
            "Wednesday, 3:00 PM - 4:00 PM",
            "Thursday, 1:00 PM - 2:00 PM",
            "Friday, 11:00 AM - 12:00 PM"
        ]
        
        return "\n".join([f"- {time}" for time in available_times])
    
    def handle_appointment_response(self, email_content: str, sender_email: str) -> Dict[str, Any]:
        """Handle response to appointment scheduling email"""
        # Find pending appointment tasks for this email
        pending_tasks = self.db.get_tasks_by_status("waiting_for_response")
        
        for task in pending_tasks:
            metadata = json.loads(task.get("metadata", "{}")) if isinstance(task.get("metadata"), str) else task.get("metadata", {})
            
            if metadata.get("contact_email") == sender_email and metadata.get("task_type") == "appointment_scheduling":
                # This is a response to our appointment scheduling
                return self.process_appointment_response(task, email_content)
        
        return {"status": "no_matching_task", "message": "No pending appointment task found"}
    
    def process_appointment_response(self, task: Dict[str, Any], response_content: str) -> Dict[str, Any]:
        """Process the response to an appointment scheduling email"""
        metadata = json.loads(task.get("metadata", "{}")) if isinstance(task.get("metadata"), str) else task.get("metadata", {})
        
        # Simple logic to detect if they accepted a time
        # In a real implementation, you'd use NLP to parse the response
        if any(word in response_content.lower() for word in ["yes", "okay", "works", "good", "perfect"]):
            # They accepted a time
            self.db.update_task(task["id"], {
                "status": "completed",
                "metadata": json.dumps({
                    **metadata,
                    "completed_at": datetime.utcnow().isoformat(),
                    "response": response_content
                })
            })
            
            # Send confirmation email
            confirmation_content = f"""
            Great! I've confirmed our appointment. I'll send you a calendar invitation shortly.
            
            Thank you for your response.
            """
            
            send_email(metadata.get("contact_email"), "Appointment Confirmed", confirmation_content)
            
            return {
                "task_id": task["id"],
                "status": "completed",
                "message": "Appointment scheduled successfully"
            }
        else:
            # They didn't accept, send more times
            return self.execute_appointment_scheduling(task)

# Global task manager instance
task_manager = TaskManager() 