# backend/app/api/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from app.services.google import get_recent_emails, get_upcoming_events, send_email, reschedule_event
from app.services.hubspot import get_hubspot_contacts, create_hubspot_note, get_hubspot_contact_notes
from app.services.ai_agent import ai_agent
from app.database import db

router = APIRouter()
client = OpenAI()

class ChatRequest(BaseModel):
    question: str
    user_id: str = "default_user"  # In a real app, this would come from authentication

class ChatResponse(BaseModel):
    answer: str

# Legacy tools for backward compatibility
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
                    "message": {"type": "string", "description": "Email message to send"},
                },
                "required": ["email", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_event_tool",
            "description": "Reschedule a meeting with a contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "Name or email of the person"},
                    "new_time": {"type": "string", "description": "New time to reschedule the meeting to"},
                },
                "required": ["person", "new_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hubspot_contacts_tool",
            "description": "Get recent contacts from HubSpot CRM",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_hubspot_note_tool",
            "description": "Create a note for a HubSpot contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_email": {"type": "string", "description": "Email address of the contact"},
                    "note_content": {"type": "string", "description": "Content of the note to create"},
                },
                "required": ["contact_email", "note_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hubspot_contact_notes_tool",
            "description": "Get notes for a specific HubSpot contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_email": {"type": "string", "description": "Email address of the contact"},
                },
                "required": ["contact_email"]
            }
        }
    }
]

def ask_openai(question: str, context: str = "") -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for a financial advisor. "
                    "Use tools when needed to send emails, reschedule meetings, or manage HubSpot contacts and notes."
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{question}"
            }
        ],
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    if message.tool_calls:
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = eval(tool_call.function.arguments)
            if name == "send_email_tool":
                send_email(args["email"], args["message"])
                return f"✅ I emailed {args['email']} with message: \"{args['message']}\""
            elif name == "reschedule_event_tool":
                result = reschedule_event(args["person"], args["new_time"])
                return result
            elif name == "get_hubspot_contacts_tool":
                contacts = get_hubspot_contacts()
                return f"📋 HubSpot Contacts:\n{contacts}"
            elif name == "create_hubspot_note_tool":
                result = create_hubspot_note(args["contact_email"], args["note_content"])
                return result
            elif name == "get_hubspot_contact_notes_tool":
                notes = get_hubspot_contact_notes(args["contact_email"])
                return f"📝 Notes for {args['contact_email']}:\n{notes}"
    else:
        return message.content.strip()

@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    try:
        # Use the new AI agent with RAG and task management
        answer = ai_agent.process_user_query(
            user_id=request.user_id,
            query=request.question
        )
        return ChatResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/legacy", response_model=ChatResponse)
async def chat_with_legacy_agent(request: ChatRequest):
    """Legacy endpoint for backward compatibility"""
    try:
        emails = get_recent_emails()
        events = get_upcoming_events()
        contacts = get_hubspot_contacts()

        formatted_emails = (
            "\n".join(f"- {email}" for email in emails) if isinstance(emails, list) else str(emails)
        )
        formatted_events = (
            "\n".join(f"- {event}" for event in events) if isinstance(events, list) else str(events)
        )
        formatted_contacts = (
            "\n".join(f"- {contact}" for contact in contacts) if isinstance(contacts, list) else str(contacts)
        )

        context = f"Recent emails:\n{formatted_emails}\n\nUpcoming calendar events:\n{formatted_events}\n\nHubSpot contacts:\n{formatted_contacts}"
        answer = ask_openai(request.question, context=context)
        return ChatResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New endpoints for enhanced functionality

@router.post("/tasks/execute")
async def execute_pending_tasks():
    """Execute all pending tasks"""
    try:
        from app.services.task_manager import task_manager
        results = task_manager.execute_pending_tasks()
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/instructions")
async def save_ongoing_instruction(instruction: str, category: str = "general"):
    """Save an ongoing instruction"""
    try:
        result = db.save_ongoing_instruction(instruction, category)
        return {"message": "Instruction saved", "instruction": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/instructions")
async def get_ongoing_instructions(category: str = None):
    """Get active ongoing instructions"""
    try:
        instructions = db.get_active_instructions(category)
        return {"instructions": instructions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def bulk_import_data():
    """Bulk import emails and HubSpot data with embeddings"""
    try:
        result = ai_agent.bulk_import_data()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks")
async def get_tasks(status: str = None):
    """Get tasks by status"""
    try:
        if status:
            tasks = db.get_tasks_by_status(status)
        else:
            tasks = db.get_pending_tasks()
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/email/process")
async def process_incoming_email(email_data: dict):
    """Process incoming email proactively"""
    try:
        result = ai_agent.process_incoming_email(email_data)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendar/process")
async def process_calendar_event(event_data: dict):
    """Process calendar event proactively"""
    try:
        result = ai_agent.process_calendar_event(event_data)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

