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
    def __init__(self):
        self.client = client
        self.db = db
        self.embedding_service = embedding_service
        self.task_manager = task_manager
    
    def process_user_query(self, user_id: str, query: str, context: str = "") -> str:
        """Process a user query with full RAG and task management"""
        try:
            # Get relevant context from RAG
            rag_context = self.get_rag_context(query)
            
            # Get ongoing instructions
            ongoing_instructions = self.get_ongoing_instructions()
            
            # Get recent conversation history
            conversation_history = self.get_conversation_history(user_id)
            
            # Combine all context
            full_context = self.build_full_context(
                query, rag_context, ongoing_instructions, conversation_history, context
            )
            
            # Process with OpenAI
            response = self.get_ai_response(query, full_context)
            
            # Save conversation
            self.db.save_conversation(user_id, query, response, full_context)
            
            return response
            
        except Exception as e:
            return f"Error processing query: {str(e)}"
    
    def get_rag_context(self, query: str) -> str:
        """Get relevant context using RAG"""
        try:
            # Search for similar emails
            similar_emails = self.embedding_service.search_similar_emails(query, limit=3)
            
            # Search for similar HubSpot data
            similar_hubspot = self.embedding_service.search_similar_hubspot_data(query, limit=3)
            
            # Format the results
            email_context = ""
            if similar_emails:
                email_context = "Relevant Emails:\n"
                for email in similar_emails:
                    email_context += f"- From: {email.get('sender', 'Unknown')}\n"
                    email_context += f"  Subject: {email.get('subject', 'No subject')}\n"
                    email_context += f"  Content: {email.get('content', '')[:200]}...\n"
                    email_context += f"  Similarity: {email.get('similarity', 0):.2f}\n\n"
            
            hubspot_context = ""
            if similar_hubspot:
                hubspot_context = "Relevant HubSpot Data:\n"
                for data in similar_hubspot:
                    hubspot_context += f"- Contact: {data.get('contact_name', 'Unknown')}\n"
                    hubspot_context += f"  Email: {data.get('contact_email', 'Unknown')}\n"
                    hubspot_context += f"  Type: {data.get('content_type', 'Unknown')}\n"
                    hubspot_context += f"  Content: {data.get('content', '')[:200]}...\n"
                    hubspot_context += f"  Similarity: {data.get('similarity', 0):.2f}\n\n"
            
            return email_context + hubspot_context
            
        except Exception as e:
            print(f"Error getting RAG context: {e}")
            return ""
    
    def get_ongoing_instructions(self) -> str:
        """Get active ongoing instructions"""
        try:
            instructions = self.db.get_active_instructions()
            if not instructions:
                return ""
            
            instruction_text = "Ongoing Instructions:\n"
            for instruction in instructions:
                instruction_text += f"- {instruction.get('instruction', '')}\n"
            
            return instruction_text + "\n"
            
        except Exception as e:
            print(f"Error getting ongoing instructions: {e}")
            return ""
    
    def get_conversation_history(self, user_id: str, limit: int = 5) -> str:
        """Get recent conversation history"""
        try:
            conversations = self.db.get_recent_conversations(user_id, limit)
            if not conversations:
                return ""
            
            history_text = "Recent Conversation History:\n"
            for conv in conversations:
                history_text += f"User: {conv.get('user_message', '')[:100]}...\n"
                history_text += f"Agent: {conv.get('agent_response', '')[:100]}...\n\n"
            
            return history_text
            
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return ""
    
    def build_full_context(self, query: str, rag_context: str, ongoing_instructions: str, 
                          conversation_history: str, additional_context: str = "") -> str:
        """Build the full context for the AI"""
        context_parts = []
        
        if ongoing_instructions:
            context_parts.append(ongoing_instructions)
        
        if conversation_history:
            context_parts.append(conversation_history)
        
        if rag_context:
            context_parts.append(rag_context)
        
        if additional_context:
            context_parts.append(f"Additional Context:\n{additional_context}")
        
        return "\n".join(context_parts)
    
    def get_ai_response(self, query: str, context: str) -> str:
        """Get response from OpenAI with tool calling"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "send_email_tool",
                    "description": "Send an email via Gmail",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Recipient's email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "message": {"type": "string", "description": "Email message to send"},
                        },
                        "required": ["email", "subject", "message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "schedule_appointment_tool",
                    "description": "Schedule an appointment with a contact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_name": {"type": "string", "description": "Name of the contact"},
                            "contact_email": {"type": "string", "description": "Email of the contact"},
                            "preferred_times": {"type": "array", "items": {"type": "string"}, "description": "Preferred times for appointment"}
                        },
                        "required": ["contact_name", "contact_email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_hubspot_contact_tool",
                    "description": "Create a contact in HubSpot with a note",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Email address of the contact"},
                            "note_content": {"type": "string", "description": "Note content to add"}
                        },
                        "required": ["email", "note_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_hubspot_note_tool",
                    "description": "Add a note to an existing HubSpot contact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Email address of the existing contact"},
                            "note_content": {"type": "string", "description": "Note content to add"}
                        },
                        "required": ["email", "note_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_ongoing_instruction_tool",
                    "description": "Save an ongoing instruction for future use",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instruction": {"type": "string", "description": "The instruction to remember"},
                            "category": {"type": "string", "description": "Category of the instruction (e.g., 'email', 'calendar', 'hubspot')"}
                        },
                        "required": ["instruction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_emails_tool",
                    "description": "Search through emails using semantic similarity",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for emails"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_hubspot_tool",
                    "description": "Search through HubSpot contacts and notes using semantic similarity",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for HubSpot data"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_calendar_tool",
                    "description": "Search through calendar events and upcoming meetings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for calendar events"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_calendar_event_tool",
                    "description": "Create a new calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Title/summary of the calendar event"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time in format 'YYYY-MM-DD HH:MM' (24-hour format)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time in format 'YYYY-MM-DD HH:MM' (optional, defaults to 1 hour after start)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the event (optional)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location of the event (optional)"
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of attendee email addresses (optional)"
                            }
                        },
                        "required": ["summary", "start_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tomorrow_meetings_tool",
                    "description": "Get tomorrow's meetings with full details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of meetings to return",
                                "default": 10
                            }
                        },
                        "required": ["limit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_contact_details_tool",
                    "description": "Get detailed contact information by name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_name": {
                                "type": "string",
                                "description": "Name of the contact to look up"
                            }
                        },
                        "required": ["contact_name"]
                    }
                }
            }
        ]
        
        # Get current date and time for the AI
        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime("%Y-%m-%d")
        current_time_str = current_datetime.strftime("%H:%M")
        current_day_str = current_datetime.strftime("%A")
        
        system_prompt = f"""You are an AI assistant for a financial advisor. You have access to:
1. Email and calendar data via Google APIs
2. HubSpot CRM data
3. Vector search capabilities for finding relevant information
4. Task management for ongoing tasks
5. Memory of ongoing instructions

IMPORTANT: Current date and time information:
- Today is {current_day_str}, {current_date_str}
- Current time is {current_time_str}
- Use this information when answering questions about dates and times

AUTOMATIC DATABASE UPDATES:
- When you send emails, they are automatically saved to the database with embeddings
- When you create calendar events, they are automatically saved to the database with embeddings
- When you create HubSpot notes, they are automatically saved to the database with embeddings
- This means all new entries are immediately searchable in future conversations

Context:
{context}

You can:
- Send emails (automatically saved to database)
- Schedule appointments and create calendar events (automatically saved to database)
- Create HubSpot contacts and notes (automatically saved to database)
- Search through emails, calendar events, and HubSpot data
- Get detailed information about tomorrow's meetings
- Get detailed contact information including phone numbers and email addresses
- Remember ongoing instructions
- Create and manage tasks

Always be helpful and proactive. If you need to do something that requires waiting for a response, create a task to handle it later."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            if message.tool_calls:
                return self.handle_tool_calls(message.tool_calls)
            else:
                return message.content.strip()
                
        except Exception as e:
            return f"Error getting AI response: {str(e)}"
    
    def handle_tool_calls(self, tool_calls) -> str:
        """Handle tool calls from OpenAI"""
        results = []
        
        for tool_call in tool_calls:
            try:
                name = tool_call.function.name
                args = eval(tool_call.function.arguments)
                
                if name == "send_email_tool":
                    # Send the email
                    send_email(args["email"], args["subject"], args["message"])
                    results.append(f"✅ Email sent to {args['email']}")
                    
                    # Automatically save the sent email to database with embedding
                    try:
                        sent_email_data = {
                            "id": f"sent_{datetime.now().timestamp()}",  # Generate unique ID
                            "subject": args["subject"],
                            "sender": "me",  # The user sent this email
                            "recipient": args["email"],
                            "content": args["message"],
                            "date": datetime.now().isoformat()
                        }
                        
                        # Create embedding for the sent email
                        self.embedding_service.create_email_embedding(sent_email_data)
                        print(f"📧 Saved sent email to database: {args['subject']}")
                        
                    except Exception as e:
                        print(f"⚠️ Failed to save sent email to database: {e}")
                
                elif name == "schedule_appointment_tool":
                    task = self.task_manager.schedule_appointment_task(
                        args["contact_name"], 
                        args["contact_email"],
                        args.get("preferred_times", [])
                    )
                    results.append(f"✅ Appointment scheduling task created for {args['contact_name']}")
                
                elif name == "create_hubspot_contact_tool":
                    # Create the HubSpot note
                    result = create_hubspot_note(args["email"], args["note_content"])
                    results.append(result)
                    
                    # Automatically save the created HubSpot note to database with embedding
                    try:
                        hubspot_data = {
                            "id": f"created_note_{datetime.now().timestamp()}",  # Generate unique ID
                            "name": args["email"].split('@')[0],  # Use email prefix as name
                            "email": args["email"],
                            "content_type": "note",
                            "content": f"Note for {args['email']}: {args['note_content']}"
                        }
                        
                        # Create embedding for the HubSpot note
                        self.embedding_service.create_hubspot_embedding(hubspot_data)
                        print(f"📋 Saved created HubSpot note to database: {args['email']}")
                        
                    except Exception as e:
                        print(f"⚠️ Failed to save created HubSpot note to database: {e}")
                
                elif name == "create_hubspot_note_tool":
                    # Create the HubSpot note
                    result = create_hubspot_note(args["email"], args["note_content"])
                    results.append(result)
                    
                    # Automatically save the created HubSpot note to database with embedding
                    try:
                        hubspot_data = {
                            "id": f"created_note_{datetime.now().timestamp()}",  # Generate unique ID
                            "name": args["email"].split('@')[0],  # Use email prefix as name
                            "email": args["email"],
                            "content_type": "note",
                            "content": f"Note for {args['email']}: {args['note_content']}"
                        }
                        
                        # Create embedding for the HubSpot note
                        self.embedding_service.create_hubspot_embedding(hubspot_data)
                        print(f"📋 Saved created HubSpot note to database: {args['email']}")
                        
                    except Exception as e:
                        print(f"⚠️ Failed to save created HubSpot note to database: {e}")
                
                elif name == "save_ongoing_instruction_tool":
                    instruction = self.db.save_ongoing_instruction(
                        args["instruction"], 
                        args.get("category", "general")
                    )
                    results.append(f"✅ Ongoing instruction saved: {args['instruction']}")
                
                elif name == "search_emails_tool":
                    emails = self.embedding_service.hybrid_search_emails(
                        args["query"], 
                        args.get("limit", 5),
                        threshold=0.1  # Lower threshold for better matching
                    )
                    if emails:
                        email_summary = "\n".join([
                            f"- {email.get('sender', 'Unknown')}: {email.get('subject', 'No subject')}"
                            for email in emails
                        ])
                        results.append(f"📧 Found {len(emails)} relevant emails:\n{email_summary}")
                    else:
                        results.append("📧 No relevant emails found")
                
                elif name == "search_hubspot_tool":
                    hubspot_data = self.embedding_service.hybrid_search_hubspot_data(
                        args["query"], 
                        args.get("limit", 5),
                        threshold=0.1  # Lower threshold for better matching
                    )
                    
                    # Debug logging - print raw data to terminal
                    print("\n🔍 DEBUG: HubSpot Search Results")
                    print("=" * 50)
                    print(f"Query: {args['query']}")
                    print(f"Found {len(hubspot_data) if hubspot_data else 0} records")
                    if hubspot_data:
                        for i, data in enumerate(hubspot_data, 1):
                            print(f"\nRecord {i}:")
                            print(f"  Raw Data: {data}")
                            print(f"  Contact Name: {data.get('contact_name', 'Unknown')}")
                            print(f"  Contact Email: {data.get('contact_email', 'No email')}")
                            print(f"  Content Type: {data.get('content_type', 'Unknown')}")
                            print(f"  Phone: {data.get('phone', 'No phone number')}")
                            print(f"  Content: {data.get('content', 'No content')}")
                            print("-" * 30)
                    print("=" * 50)
                    
                    if hubspot_data:
                        # Provide detailed information for HubSpot contacts
                        contact_details = []
                        for data in hubspot_data:
                            contact_name = data.get('contact_name', 'Unknown')
                            contact_email = data.get('contact_email', 'No email')
                            content_type = data.get('content_type', 'Unknown')
                            content = data.get('content', 'No content')
                            
                            # Use the new detailed fields if available
                            phone_number = data.get('phone', 'No phone number')
                            company = data.get('company', 'No company')
                            job_title = data.get('job_title', 'No job title')
                            address = data.get('address', 'No address')
                            website = data.get('website', 'No website')
                            
                            # If the new fields aren't available, try to extract from content
                            if phone_number == 'No phone number':
                                # Look for phone number patterns in content
                                import re
                                phone_patterns = [
                                    r'Phone:\s*([\d\-\(\)\s]+)',
                                    r'phone:\s*([\d\-\(\)\s]+)',
                                    r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
                                    r'(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})'
                                ]
                                
                                for pattern in phone_patterns:
                                    phone_match = re.search(pattern, content)
                                    if phone_match:
                                        phone_number = phone_match.group(1).strip()
                                        break
                            
                            if company == 'No company':
                                # Look for company information
                                company_patterns = [
                                    r'Company:\s*([^\n]+)',
                                    r'company:\s*([^\n]+)',
                                    r'at\s+([A-Z][a-zA-Z\s&]+)',
                                    r'with\s+([A-Z][a-zA-Z\s&]+)'
                                ]
                                
                                for pattern in company_patterns:
                                    company_match = re.search(pattern, content)
                                    if company_match:
                                        company = company_match.group(1).strip()
                                        break
                            
                            # Build detailed contact info
                            contact_info = f"👤 **{contact_name}**\n"
                            contact_info += f"📧 **Email:** {contact_email}\n"
                            contact_info += f"📞 **Phone:** {phone_number}\n"
                            if job_title != 'No job title':
                                contact_info += f"💼 **Job Title:** {job_title}\n"
                            if company != 'No company':
                                contact_info += f"🏢 **Company:** {company}\n"
                            if address != 'No address':
                                contact_info += f"📍 **Address:** {address}\n"
                            if website != 'No website':
                                contact_info += f"🌐 **Website:** {website}\n"
                            contact_info += f"📋 **Type:** {content_type}\n"
                            
                            # Add content preview if it's a note
                            if content_type == "note" and content != "No content":
                                content_preview = content[:200] + ('...' if len(content) > 200 else '')
                                contact_info += f"📝 **Note:** {content_preview}\n"
                            
                            contact_details.append(contact_info)
                        
                        results.append(f"📋 Found {len(hubspot_data)} relevant HubSpot records:\n\n" + "\n\n".join(contact_details))
                    else:
                        results.append("📋 No relevant HubSpot data found")
                
                elif name == "search_calendar_tool":
                    events = self.embedding_service.hybrid_search_calendar_events(
                        args["query"], 
                        args.get("limit", 5),
                        threshold=0.1  # Lower threshold for better matching
                    )
                    if events:
                        # Provide more detailed information for calendar events
                        event_details = []
                        for event in events:
                            summary = event.get('summary', 'No summary')
                            start_time = event.get('start_time', 'TBD')
                            end_time = event.get('end_time', 'TBD')
                            location = event.get('location', 'No location')
                            description = event.get('description', 'No description')
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
                            
                            # Build detailed event info
                            event_info = f"📅 **{summary}**\n"
                            event_info += f"🕐 **Time:** {time_info}\n"
                            if location and location != 'No location':
                                event_info += f"📍 **Location:** {location}\n"
                            if description and description != 'No description':
                                event_info += f"📝 **Description:** {description[:200]}{'...' if len(description) > 200 else ''}\n"
                            if attendees:
                                event_info += f"👥 **Attendees:** {', '.join(attendees)}\n"
                            
                            event_details.append(event_info)
                        
                        results.append(f"📅 Found {len(events)} relevant calendar events:\n\n" + "\n\n".join(event_details))
                    else:
                        results.append("📅 No relevant calendar events found")
                
                elif name == "get_tomorrow_meetings_tool":
                    # Special tool for getting tomorrow's meetings with full details
                    from datetime import datetime, timedelta
                    tomorrow = datetime.now() + timedelta(days=1)
                    tomorrow_date = tomorrow.strftime('%Y-%m-%d')
                    
                    # Search for events tomorrow
                    events = self.embedding_service.hybrid_search_calendar_events(
                        f"meetings on {tomorrow_date}", 
                        limit=10,
                        threshold=0.05  # Very low threshold to catch all events
                    )
                    
                    if events:
                        # Filter for events that are actually tomorrow
                        tomorrow_events = []
                        for event in events:
                            try:
                                start_time = event.get('start_time', '')
                                if start_time:
                                    event_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    if event_date.date() == tomorrow.date():
                                        tomorrow_events.append(event)
                            except:
                                continue
                        
                        if tomorrow_events:
                            event_details = []
                            for event in tomorrow_events:
                                summary = event.get('summary', 'No summary')
                                start_time = event.get('start_time', 'TBD')
                                end_time = event.get('end_time', 'TBD')
                                location = event.get('location', 'No location')
                                description = event.get('description', 'No description')
                                attendees = event.get('attendees', [])
                                
                                # Format the time nicely
                                try:
                                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                                    formatted_start = start_dt.strftime('%I:%M %p')
                                    formatted_end = end_dt.strftime('%I:%M %p')
                                    time_info = f"{formatted_start} - {formatted_end}"
                                except:
                                    time_info = f"{start_time} - {end_time}"
                                
                                # Build detailed event info
                                event_info = f"📅 **{summary}**\n"
                                event_info += f"🕐 **Time:** {time_info}\n"
                                if location and location != 'No location':
                                    event_info += f"📍 **Location:** {location}\n"
                                if description and description != 'No description':
                                    event_info += f"📝 **Description:** {description[:200]}{'...' if len(description) > 200 else ''}\n"
                                if attendees:
                                    event_info += f"👥 **Attendees:** {', '.join(attendees)}\n"
                                
                                event_details.append(event_info)
                            
                            results.append(f"📅 **Tomorrow's Meetings ({tomorrow.strftime('%A, %B %d')}):**\n\n" + "\n\n".join(event_details))
                        else:
                            results.append(f"📅 No meetings found for tomorrow ({tomorrow.strftime('%A, %B %d')})")
                    else:
                        results.append(f"📅 No meetings found for tomorrow ({tomorrow.strftime('%A, %B %d')})")
                
                elif name == "create_calendar_event_tool":
                    # Parse natural language date if needed
                    start_time = args["start_time"]
                    if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', start_time):
                        # Try to parse as natural language
                        parsed_time = parse_natural_date(start_time)
                        if parsed_time:
                            start_time = parsed_time
                            print(f"🔍 Parsed '{args['start_time']}' to '{start_time}'")
                        else:
                            results.append(f"⚠️ Could not parse date '{args['start_time']}'. Please use format 'YYYY-MM-DD HH:MM' or natural language like 'tomorrow at 2pm'")
                            continue
                    
                    # Create the calendar event
                    result = create_calendar_event(
                        summary=args["summary"],
                        start_time=start_time,
                        end_time=args.get("end_time"),
                        description=args.get("description", ""),
                        location=args.get("location", ""),
                        attendees=args.get("attendees", [])
                    )
                    results.append(result)
                    
                    # Automatically save the created calendar event to database with embedding
                    try:
                        # Parse the start and end times
                        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
                        if args.get("end_time"):
                            end_dt = datetime.strptime(args["end_time"], "%Y-%m-%d %H:%M")
                        else:
                            end_dt = start_dt + timedelta(hours=1)
                        
                        calendar_event_data = {
                            "id": f"created_{datetime.now().timestamp()}",  # Generate unique ID
                            "summary": args["summary"],
                            "description": args.get("description", ""),
                            "start_time": start_dt.isoformat(),
                            "end_time": end_dt.isoformat(),
                            "location": args.get("location", ""),
                            "attendees": args.get("attendees", [])
                        }
                        
                        # Create embedding for the calendar event
                        self.embedding_service.create_calendar_embedding(calendar_event_data)
                        print(f"📅 Saved created calendar event to database: {args['summary']}")
                        
                    except Exception as e:
                        print(f"⚠️ Failed to save created calendar event to database: {e}")
                
                elif name == "get_contact_details_tool":
                    # Get detailed contact information by name
                    contact_name = args["contact_name"]
                    
                    # Debug logging - print search request
                    print(f"\n🔍 DEBUG: Contact Details Search for '{contact_name}'")
                    print("=" * 50)
                    
                    # Search for the specific contact
                    hubspot_data = self.embedding_service.hybrid_search_hubspot_data(
                        contact_name, 
                        limit=10,
                        threshold=0.05  # Very low threshold to catch the contact
                    )
                    
                    # Debug logging - print search results
                    print(f"Query: {contact_name}")
                    print(f"Found {len(hubspot_data) if hubspot_data else 0} records")
                    if hubspot_data:
                        for i, data in enumerate(hubspot_data, 1):
                            print(f"\nRecord {i}:")
                            print(f"  Raw Data: {data}")
                            print(f"  Contact Name: {data.get('contact_name', 'Unknown')}")
                            print(f"  Contact Email: {data.get('contact_email', 'No email')}")
                            print(f"  Content Type: {data.get('content_type', 'Unknown')}")
                            print(f"  Content: {data.get('content', 'No content')}")
                            print("-" * 30)
                    print("=" * 50)
                    
                    if hubspot_data:
                        # Find the best match for the contact name
                        best_match = None
                        for data in hubspot_data:
                            data_name = data.get('contact_name', '').lower()
                            if contact_name.lower() in data_name or data_name in contact_name.lower():
                                best_match = data
                                break
                        
                        if best_match:
                            contact_name = best_match.get('contact_name', 'Unknown')
                            contact_email = best_match.get('contact_email', 'No email')
                            content_type = best_match.get('content_type', 'Unknown')
                            content = best_match.get('content', 'No content')
                            
                            # Use the new detailed fields if available
                            phone_number = best_match.get('phone', 'No phone number')
                            company = best_match.get('company', 'No company')
                            job_title = best_match.get('job_title', 'No job title')
                            address = best_match.get('address', 'No address')
                            website = best_match.get('website', 'No website')
                            
                            # If the new fields aren't available, try to extract from content
                            if phone_number == 'No phone number':
                                # Look for phone number patterns in content
                                import re
                                phone_patterns = [
                                    r'Phone:\s*([\d\-\(\)\s]+)',
                                    r'phone:\s*([\d\-\(\)\s]+)',
                                    r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
                                    r'(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})'
                                ]
                                
                                for pattern in phone_patterns:
                                    phone_match = re.search(pattern, content)
                                    if phone_match:
                                        phone_number = phone_match.group(1).strip()
                                        break
                            
                            if company == 'No company':
                                # Look for company information
                                company_patterns = [
                                    r'Company:\s*([^\n]+)',
                                    r'company:\s*([^\n]+)',
                                    r'at\s+([A-Z][a-zA-Z\s&]+)',
                                    r'with\s+([A-Z][a-zA-Z\s&]+)'
                                ]
                                
                                for pattern in company_patterns:
                                    company_match = re.search(pattern, content)
                                    if company_match:
                                        company = company_match.group(1).strip()
                                        break
                            
                            # Build detailed contact info
                            contact_info = f"👤 **{contact_name}**\n"
                            contact_info += f"📧 **Email:** {contact_email}\n"
                            contact_info += f"📞 **Phone:** {phone_number}\n"
                            if job_title != 'No job title':
                                contact_info += f"💼 **Job Title:** {job_title}\n"
                            if company != 'No company':
                                contact_info += f"🏢 **Company:** {company}\n"
                            if address != 'No address':
                                contact_info += f"📍 **Address:** {address}\n"
                            if website != 'No website':
                                contact_info += f"🌐 **Website:** {website}\n"
                            contact_info += f"📋 **Type:** {content_type}\n"
                            
                            # Add content preview if it's a note
                            if content_type == "note" and content != "No content":
                                content_preview = content[:200] + ('...' if len(content) > 200 else '')
                                contact_info += f"📝 **Note:** {content_preview}\n"
                            
                            results.append(f"📋 **Contact Details for {contact_name}:**\n\n{contact_info}")
                        else:
                            results.append(f"📋 Contact '{contact_name}' not found in HubSpot")
                    else:
                        results.append(f"📋 Contact '{contact_name}' not found in HubSpot")
                
            except Exception as e:
                results.append(f"❌ Error executing {name}: {str(e)}")
        
        return "\n\n".join(results)
    
    def process_incoming_email(self, email_data: Dict[str, Any]) -> str:
        """Process incoming email proactively"""
        try:
            # Create embedding for the email
            self.embedding_service.create_email_embedding(email_data)
            
            # Check ongoing instructions for email processing
            instructions = self.db.get_active_instructions("email")
            
            for instruction in instructions:
                # Simple keyword matching - in a real implementation, you'd use NLP
                instruction_text = instruction.get("instruction", "").lower()
                email_content = email_data.get("content", "").lower()
                
                if "not in hubspot" in instruction_text and "create contact" in instruction_text:
                    # Check if sender is in HubSpot
                    sender_email = email_data.get("sender", "")
                    if sender_email:
                        # Create task to add to HubSpot
                        self.task_manager.create_hubspot_contact_task(
                            sender_email, 
                            f"Email received: {email_data.get('subject', 'No subject')}"
                        )
                        return f"✅ Created task to add {sender_email} to HubSpot"
            
            return "📧 Email processed and stored"
            
        except Exception as e:
            return f"Error processing email: {str(e)}"
    
    def process_calendar_event(self, event_data: Dict[str, Any]) -> str:
        """Process calendar event proactively"""
        try:
            # Check ongoing instructions for calendar processing
            instructions = self.db.get_active_instructions("calendar")
            
            for instruction in instructions:
                instruction_text = instruction.get("instruction", "").lower()
                
                if "send email to attendees" in instruction_text:
                    attendees = event_data.get("attendees", [])
                    for attendee in attendees:
                        email = attendee.get("email")
                        if email:
                            subject = f"Meeting Reminder: {event_data.get('summary', 'Meeting')}"
                            content = f"""
                            Hi,
                            
                            This is a reminder about our upcoming meeting:
                            
                            Event: {event_data.get('summary', 'Meeting')}
                            Time: {event_data.get('start', {}).get('dateTime', 'TBD')}
                            
                            Looking forward to it!
                            """
                            
                            self.task_manager.create_email_response_task(email, subject, content)
            
            return "📅 Calendar event processed"
            
        except Exception as e:
            return f"Error processing calendar event: {str(e)}"
    
    def bulk_import_data(self) -> Dict[str, Any]:
        """Bulk import emails, HubSpot data, and calendar events with embeddings"""
        try:
            # Import recent emails
            emails = get_recent_emails(50)  # Get more emails for import
            print(f"Importing {len(emails)} emails")
            email_results = self.embedding_service.bulk_import_emails(emails)
            print(f"Imported {email_results['success']} emails")
            
            # Import HubSpot data
            contacts = get_hubspot_contacts()
            hubspot_results = self.embedding_service.bulk_import_hubspot_data(contacts)
            print(f"Imported {hubspot_results['success']} HubSpot records")
            
            # Import calendar events
            # Get current month events
            current_month_events = get_calendar_events_for_period(max_results=50)
            
            # Get next month events
            next_month_start = datetime.utcnow().replace(day=1) + timedelta(days=32)
            next_month_start = next_month_start.replace(day=1)
            next_month_end = next_month_start.replace(month=next_month_start.month + 1) - timedelta(days=1)
            
            next_month_events = get_calendar_events_for_period(
                start_date=next_month_start,
                end_date=next_month_end,
                max_results=50
            )
            
            all_calendar_events = current_month_events + next_month_events
            print(f"Importing {len(all_calendar_events)} calendar events")
            calendar_results = self.embedding_service.bulk_import_calendar_events(all_calendar_events)
            print(f"Imported {calendar_results['success']} calendar events")
            
            return {
                "emails": email_results,
                "hubspot_data": hubspot_results,
                "calendar_events": calendar_results,
                "message": "Bulk import completed for emails, HubSpot data, and calendar events"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def debug_search(self, query: str) -> str:
        """Debug method to test search functionality"""
        try:
            # Test email search
            emails = self.embedding_service.search_similar_emails(query, 5, 0.3)
            
            # Test HubSpot search
            hubspot_data = self.embedding_service.search_similar_hubspot_data(query, 5, 0.3)
            
            # Get recent data from database
            recent_emails = self.db.get_recent_emails(3)
            recent_hubspot = self.db.get_recent_hubspot_data(3)
            
            debug_info = f"""
🔍 Debug Search Results for: "{query}"

📧 Email Search Results (threshold 0.3):
- Found {len(emails)} emails
- Emails: {[email.get('subject', 'No subject') for email in emails]}

📋 HubSpot Search Results (threshold 0.3):
- Found {len(hubspot_data)} records
- Records: {[data.get('content_type', 'Unknown') for data in hubspot_data]}

🗄️ Recent Database Data:
- Recent emails in DB: {len(recent_emails)}
- Recent HubSpot data in DB: {len(recent_hubspot)}
"""
            return debug_info
            
        except Exception as e:
            return f"Debug error: {str(e)}"

# Global AI agent instance
ai_agent = AIAgent() 