from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from api import auth, chat, hubspot, webhooks
from dotenv import load_dotenv
import os
import secrets
from app.database import db

load_dotenv()

app = FastAPI()

# Get allowed origins from environment or use defaults
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware with explicit cookie settings
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", secrets.token_urlsafe(32)),
    same_site="lax",  # Try 'none' if needed (requires HTTPS)
    https_only=False,  # Set to False for local HTTP testing
    max_age=1209600,  # 14 days, matching your cookie
    path="/"
)

# Register API routers
app.include_router(auth.router, prefix="/auth")
app.include_router(chat.router, prefix="/chat")
app.include_router(hubspot.router, prefix="/hubspot")
app.include_router(webhooks.router, prefix="/webhooks")

@app.get("/")
def root():
    return {"status": "Backend is running"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Jump AI Agent is running",
        "features": {
            "rag": "enabled",
            "task_management": "enabled", 
            "ongoing_instructions": "enabled",
            "proactive_processing": "enabled"
        }
    }

# This is required for Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
