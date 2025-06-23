from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from app.database import db
from app.services.embeddings import embedding_service
from app.services.task_manager import task_manager
from app.services.google import get_recent_emails, get_upcoming_events, send_email, reschedule_event, get_calendar_events_for_period, create_calendar_event, parse_natural_date
from app.services.hubspot import get_hubspot_contacts, create_hubspot_note, get_hubspot_contact_notes
import re
from datetime import datetime, timedelta

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AIAgent:
    def __init__(self, user_email: str = None):
        self.user_email = user_email
        self.embedding_service = embedding_service
        self.task_manager = task_manager
        self.conversation_history = []
    
    def get_user_context(self) -> str:
        """Get user-specific context for the AI"""
        if not self.user_email:
            return "No user context available."
        
        context_parts = []
        
        # Get user's recent conversations
        recent_conversations = db.get_recent_conversations(self.user_email, limit=5)
        if recent_conversations:
            context_parts.append("Recent conversation context:")
            for conv in recent_conversations:
                context_parts.append(f"- User: {conv['user_message'][:100]}...")
                context_parts.append(f"- Assistant: {conv['agent_response'][:100]}...")
        
        # Get user's ongoing instructions
        active_instructions = db.get_active_instructions()
        if active_instructions:
            context_parts.append("Active instructions:")
            for instruction in active_instructions:
                context_parts.append(f"- {instruction['instruction']}")
        
        return "\n".join(context_parts) if context_parts else "No specific context available."

    def search_relevant_data(self, query: str) -> Dict[str, Any]:
        """Search for relevant data across all sources"""
        if not self.user_email:
            return {"emails": [], "hubspot_data": [], "calendar_events": []}
        
        results = {
            "emails": self.embedding_service.hybrid_search_emails(query, limit=3, threshold=0.3),
            "hubspot_data": self.embedding_service.hybrid_search_hubspot_data(query, limit=3, threshold=0.3),
            "calendar_events": self.embedding_service.hybrid_search_calendar_events(query, limit=3, threshold=0.3)
        }
        
        return results

    def process_message(self, user_message: str) -> str:
        """Process user message and generate response"""
        try:
            # Get user context
            user_context = self.get_user_context()
            
            # Search for relevant data
            relevant_data = self.search_relevant_data(user_message)
            
            # Build context for AI
            context = self.build_context(user_context, relevant_data)
            
            # Generate response using OpenAI
            response = self.generate_response(user_message, context)
            
            # Save conversation
            if self.user_email:
                db.save_conversation(self.user_email, user_message, response, context)
            
            return response
            
        except Exception as e:
            print(f"Error processing message: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def build_context(self, user_context: str, relevant_data: Dict[str, Any]) -> str:
        """Build context string from relevant data"""
        context_parts = []
        
        if user_context:
            context_parts.append(f"USER CONTEXT:\n{user_context}\n")
        
        # Add relevant emails
        if relevant_data["emails"]:
            context_parts.append("RELEVANT EMAILS:")
            for email in relevant_data["emails"]:
                context_parts.append(f"- From: {email.get('sender', 'Unknown')}")
                context_parts.append(f"  Subject: {email.get('subject', 'No Subject')}")
                context_parts.append(f"  Content: {email.get('content', '')[:200]}...")
                context_parts.append("")
        
        # Add relevant HubSpot data
        if relevant_data["hubspot_data"]:
            context_parts.append("RELEVANT HUBSPOT DATA:")
            for contact in relevant_data["hubspot_data"]:
                context_parts.append(f"- Contact: {contact.get('contact_name', 'Unknown')}")
                context_parts.append(f"  Email: {contact.get('contact_email', 'No Email')}")
                context_parts.append(f"  Phone: {contact.get('phone', 'No Phone')}")
                context_parts.append(f"  Company: {contact.get('company', 'No Company')}")
                context_parts.append(f"  Job Title: {contact.get('job_title', 'No Title')}")
                context_parts.append(f"  Content: {contact.get('content', '')[:200]}...")
                context_parts.append("")
        
        # Add relevant calendar events
        if relevant_data["calendar_events"]:
            context_parts.append("RELEVANT CALENDAR EVENTS:")
            for event in relevant_data["calendar_events"]:
                context_parts.append(f"- Event: {event.get('summary', 'No Title')}")
                context_parts.append(f"  Time: {event.get('start_time', 'No Time')} - {event.get('end_time', 'No End Time')}")
                context_parts.append(f"  Location: {event.get('location', 'No Location')}")
                context_parts.append(f"  Attendees: {', '.join(event.get('attendees', []))}")
                context_parts.append(f"  Description: {event.get('description', '')[:200]}...")
                context_parts.append("")
        
        return "\n".join(context_parts)

    def generate_response(self, user_message: str, context: str) -> str:
        """Generate response using OpenAI API with function calling"""
        try:
            import openai
            
            # Set up OpenAI client
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Define tools for function calling
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_emails",
                        "description": "Search user's emails for relevant information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for emails"}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_hubspot_contacts",
                        "description": "Search HubSpot contacts for relevant information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for HubSpot contacts"}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_calendar_events",
                        "description": "Search calendar events for relevant information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for calendar events"}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_calendar_events",
                        "description": "Get upcoming calendar events for the current month",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {"type": "integer", "description": "Maximum number of events to return", "default": 10}
                            },
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_email",
                        "description": "Send an email via Gmail",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string", "description": "Recipient's email address"},
                                "subject": {"type": "string", "description": "Email subject"},
                                "body": {"type": "string", "description": "Email message body"}
                            },
                            "required": ["to", "subject", "body"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "create_calendar_event",
                        "description": "Create a new calendar event",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string", "description": "Event title/summary"},
                                "start_time": {"type": "string", "description": "Start time (ISO format)"},
                                "end_time": {"type": "string", "description": "End time (ISO format)"},
                                "description": {"type": "string", "description": "Event description"},
                                "location": {"type": "string", "description": "Event location"},
                                "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"}
                            },
                            "required": ["summary", "start_time", "end_time"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "create_hubspot_note",
                        "description": "Create a note for a HubSpot contact",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contact_email": {"type": "string", "description": "Email address of the contact"},
                                "note_content": {"type": "string", "description": "Content of the note to create"}
                            },
                            "required": ["contact_email", "note_content"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_hubspot_contact_notes",
                        "description": "Get notes for a specific HubSpot contact",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contact_email": {"type": "string", "description": "Email address of the contact"}
                            },
                            "required": ["contact_email"]
                        }
                    }
                }
            ]
            
            # Build system prompt
            system_prompt = f"""You are an AI assistant for a financial advisor. You have access to the user's emails, HubSpot CRM data, and calendar events.

Your capabilities include:
- Searching and analyzing emails
- Accessing HubSpot contact information and notes
- Viewing and creating calendar events
- Sending emails
- Creating notes in HubSpot

Current user context:
{context}

Always be helpful, professional, and concise. Use the appropriate tools when needed to perform actions.

Remember: You are working with {self.user_email}'s data and should respect privacy and security."""
            
            # Generate response with function calling
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                tools=tools,
                tool_choice="auto",
                max_tokens=1000,
                temperature=0.7
            )
            
            message = response.choices[0].message
            
            # Handle tool calls
            if message.tool_calls:
                tool_results = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    args = eval(tool_call.function.arguments)
                    
                    # Execute the tool
                    result = self.execute_tool(tool_name, **args)
                    tool_results.append(result)
                
                # Return the tool results
                return "\n\n".join(tool_results)
            else:
                return message.content
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."

    def bulk_import_data(self) -> Dict[str, Any]:
        """Bulk import data from all sources"""
        if not self.user_email:
            return {"error": "No user email provided"}
        
        results = {
            "emails": {"success": 0, "errors": 0, "total": 0},
            "hubspot_data": {"success": 0, "errors": 0, "total": 0},
            "calendar_events": {"success": 0, "errors": 0, "total": 0}
        }
        
        try:
            # Import emails
            from ..services.google import get_user_emails
            emails = get_user_emails(self.user_email, max_results=100)
            if emails:
                results["emails"] = self.embedding_service.bulk_import_emails(emails)
            
            # Import HubSpot data
            from ..services.hubspot import get_hubspot_contacts
            hubspot_data = get_hubspot_contacts(self.user_email)
            if hubspot_data:
                results["hubspot_data"] = self.embedding_service.bulk_import_hubspot_data(hubspot_data)
            
            # Import calendar events
            from ..services.google import get_calendar_events
            calendar_events = get_calendar_events(self.user_email, max_results=100)
            if calendar_events:
                results["calendar_events"] = self.embedding_service.bulk_import_calendar_events(calendar_events)
            
            return results
            
        except Exception as e:
            print(f"Error in bulk import: {e}")
            return {"error": str(e)}

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a specific tool"""
        if not self.user_email:
            return "Error: No user email provided"
        
        try:
            if tool_name == "search_emails":
                query = kwargs.get("query", "")
                results = self.embedding_service.hybrid_search_emails(query, limit=5, threshold=0.3)
                if results:
                    response = "Found relevant emails:\n\n"
                    for email in results:
                        response += f"**From:** {email.get('sender', 'Unknown')}\n"
                        response += f"**Subject:** {email.get('subject', 'No Subject')}\n"
                        response += f"**Date:** {email.get('date', 'Unknown')}\n"
                        response += f"**Content:** {email.get('content', '')[:200]}...\n\n"
                    return response
                else:
                    return "No relevant emails found."
            
            elif tool_name == "search_hubspot_contacts":
                query = kwargs.get("query", "")
                results = self.embedding_service.hybrid_search_hubspot_data(query, limit=5, threshold=0.3)
                if results:
                    response = "Found relevant HubSpot contacts:\n\n"
                    for contact in results:
                        response += f"**Name:** {contact.get('contact_name', 'Unknown')}\n"
                        response += f"**Email:** {contact.get('contact_email', 'No Email')}\n"
                        response += f"**Phone:** {contact.get('phone', 'No Phone')}\n"
                        response += f"**Company:** {contact.get('company', 'No Company')}\n"
                        response += f"**Job Title:** {contact.get('job_title', 'No Title')}\n"
                        response += f"**Content:** {contact.get('content', '')[:200]}...\n\n"
                    return response
                else:
                    return "No relevant HubSpot contacts found."
            
            elif tool_name == "search_calendar_events":
                query = kwargs.get("query", "")
                results = self.embedding_service.hybrid_search_calendar_events(query, limit=5, threshold=0.3)
                if results:
                    response = "Found relevant calendar events:\n\n"
                    for event in results:
                        response += f"**Event:** {event.get('summary', 'No Title')}\n"
                        response += f"**Time:** {event.get('start_time', 'No Time')} - {event.get('end_time', 'No End Time')}\n"
                        response += f"**Location:** {event.get('location', 'No Location')}\n"
                        response += f"**Attendees:** {', '.join(event.get('attendees', []))}\n"
                        response += f"**Description:** {event.get('description', '')[:200]}...\n\n"
                    return response
                else:
                    return "No relevant calendar events found."
            
            elif tool_name == "get_calendar_events":
                max_results = kwargs.get("max_results", 10)
                from ..services.google import get_calendar_events_for_period
                
                # Get events for current month
                events = get_calendar_events_for_period(self.user_email, max_results=max_results)
                
                if events:
                    response = f"📅 **Calendar Events for This Month** (showing {len(events)} events):\n\n"
                    for i, event in enumerate(events, 1):
                        summary = event.get('summary', 'No Title')
                        start_time = event.get('start_time', 'TBD')
                        end_time = event.get('end_time', 'TBD')
                        location = event.get('location', '')
                        description = event.get('description', '')
                        attendees = event.get('attendees', [])
                        
                        # Format the time nicely
                        try:
                            from datetime import datetime
                            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            formatted_start = start_dt.strftime('%A, %B %d at %I:%M %p')
                            formatted_end = end_dt.strftime('%I:%M %p')
                            time_info = f"{formatted_start} - {formatted_end}"
                        except:
                            time_info = f"{start_time} - {end_time}"
                        
                        response += f"{i}. **{summary}**\n"
                        response += f"   🕐 {time_info}\n"
                        if location:
                            response += f"   📍 {location}\n"
                        if description:
                            desc_preview = description[:150] + ('...' if len(description) > 150 else '')
                            response += f"   📝 {desc_preview}\n"
                        if attendees:
                            response += f"   👥 Attendees: {', '.join(attendees)}\n"
                        response += "\n"
                    
                    return response
                else:
                    return "📅 No calendar events found for this month."
            
            elif tool_name == "send_email":
                to_email = kwargs.get("to", "")
                subject = kwargs.get("subject", "")
                body = kwargs.get("body", "")
                
                from ..services.google import send_email
                result = send_email(self.user_email, to_email, subject, body)
                
                if result.get("success"):
                    return f"✅ Email sent successfully to {to_email} with subject: '{subject}'"
                else:
                    return f"❌ Failed to send email: {result.get('error', 'Unknown error')}"
            
            elif tool_name == "create_calendar_event":
                summary = kwargs.get("summary", "")
                start_time = kwargs.get("start_time", "")
                end_time = kwargs.get("end_time", "")
                description = kwargs.get("description", "")
                location = kwargs.get("location", "")
                attendees = kwargs.get("attendees", [])
                
                from ..services.google import create_calendar_event
                result = create_calendar_event(
                    self.user_email, summary, start_time, end_time, 
                    description, location, attendees
                )
                
                if result.get("success"):
                    return f"✅ Calendar event created successfully: {summary}"
                else:
                    return f"❌ Failed to create calendar event: {result.get('error', 'Unknown error')}"
            
            elif tool_name == "create_hubspot_note":
                contact_email = kwargs.get("contact_email", "")
                note_content = kwargs.get("note_content", "")
                
                from ..services.hubspot import create_hubspot_note
                result = create_hubspot_note(self.user_email, contact_email, note_content)
                return result
            
            elif tool_name == "get_hubspot_contact_notes":
                contact_email = kwargs.get("contact_email", "")
                
                from ..services.hubspot import get_hubspot_contact_notes
                result = get_hubspot_contact_notes(self.user_email, contact_email)
                return result
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            print(f"Error executing tool {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"

# Global AI agent instance
ai_agent = AIAgent() 