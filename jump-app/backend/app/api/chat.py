# backend/app/api/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from app.services.google import get_recent_emails, get_upcoming_events, send_email, reschedule_event

router = APIRouter()
client = OpenAI()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

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
                    "Use tools when needed to send emails or reschedule meetings."
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
    else:
        return message.content.strip()

@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    try:
        emails = get_recent_emails()
        events = get_upcoming_events()

        formatted_emails = (
            "\n".join(f"- {email}" for email in emails) if isinstance(emails, list) else str(emails)
        )
        formatted_events = (
            "\n".join(f"- {event}" for event in events) if isinstance(events, list) else str(events)
        )

        context = f"Recent emails:\n{formatted_emails}\n\nUpcoming calendar events:\n{formatted_events}"
        answer = ask_openai(request.question, context=context)
        return ChatResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

