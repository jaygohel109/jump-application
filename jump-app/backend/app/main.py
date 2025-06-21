from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from api import auth, chat
from services.google import build_flow, handle_google_callback
from dotenv import load_dotenv
import os
import secrets
import pickle

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend and backend
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
    domain="127.0.0.1",
    path="/"
)

# Register API routers
app.include_router(auth.router, prefix="/auth")
app.include_router(chat.router, prefix="/chat")

@app.get("/")
def root():
    return {"status": "Backend is running"}
