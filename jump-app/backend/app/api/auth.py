# backend/app/api/auth.py
import sys, uuid
import time
sys.path.append("..")
from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import urllib.parse
from app import config
from app.services.google import get_google_oauth_url, exchange_google_code
from datetime import datetime, timedelta
import secrets
import os
from app.database import db
from app.services.hubspot import get_hubspot_oauth_url, exchange_hubspot_code
from app.utils.security import make_state, verify_state

router = APIRouter()

# === GOOGLE OAUTH FLOW ===
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

@router.get("/google")
def google_auth():
    params = {
        "client_id": config.settings.GOOGLE_CLIENT_ID,
        "redirect_uri": config.settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login"""
    oauth_url = get_google_oauth_url()
    return {"oauth_url": oauth_url}

@router.get("/google/callback")
async def google_callback(code: str, request: Request, response: Response):
    """Handle Google OAuth callback"""
    try:
        print(f"=== Google OAuth Callback Start ===")  # Debug log
        print(f"Google callback received with code: {code[:20]}...")  # Debug log
        
        # Exchange code for tokens
        tokens = await exchange_google_code(code)
        if not tokens:
            print("Failed to exchange code for tokens")  # Debug log
            raise HTTPException(status_code=400, detail="Failed to get Google tokens")
        
        print(f"Successfully got tokens for user")  # Debug log
        
        # Get user info from Google
        try:
            async with httpx.AsyncClient() as client:
                user_info_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"}
                )
                print(f"User info response status: {user_info_response.status_code}")  # Debug log
                
                if user_info_response.status_code != 200:
                    print(f"User info response error: {user_info_response.text}")  # Debug log
                    raise HTTPException(status_code=400, detail=f"Failed to get user info: {user_info_response.status_code}")
                
                user_info = user_info_response.json()
                print(f"Google user info response: {user_info}")  # Debug log
        except Exception as e:
            print(f"Error getting user info: {e}")  # Debug log
            raise HTTPException(status_code=400, detail=f"Failed to get user info: {str(e)}")
        
        email = user_info.get("email")
        if not email:
            print(f"No email found in user_info: {user_info}")  # Debug log
            raise HTTPException(status_code=400, detail="No email found in Google response")
        
        print(f"User email: {email}")  # Debug log
        
        # Create or update user in database
        try:
            google_tokens = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": (datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))).isoformat()
            }
            
            user = db.create_or_update_user(email, google_tokens=google_tokens)
            if not user:
                print(f"Failed to save user data for {email}")  # Debug log
                raise HTTPException(status_code=500, detail="Failed to save user data")
            
            print(f"User saved successfully: {user.get('id')}")  # Debug log
        except Exception as e:
            print(f"Error saving user data: {e}")  # Debug log
            raise HTTPException(status_code=500, detail=f"Failed to save user data: {str(e)}")
        
        # Create session
        try:
            session_id = secrets.token_urlsafe(32)
            if not db.create_session(email, session_id):
                print(f"Failed to create session for {email}")  # Debug log
                raise HTTPException(status_code=500, detail="Failed to create session")
            
            print(f"Session created successfully: {session_id[:20]}...")  # Debug log
        except Exception as e:
            print(f"Error creating session: {e}")  # Debug log
            raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")
        
        # Set session cookie and redirect
        try:
            print(f"About to redirect to set session cookie: {session_id[:20]}...")  # Debug log
            
            # Redirect to the set-session-and-redirect endpoint
            backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
            redirect_url = f"{backend_url}/auth/set-session-and-redirect?session_id={session_id}"
            print(f"Redirecting to: {redirect_url}")  # Debug log
            print(f"=== Google OAuth Callback End ===")  # Debug log
            return RedirectResponse(url=redirect_url, status_code=302)
            
        except Exception as e:
            print(f"Error creating redirect: {e}")  # Debug log
            import traceback
            traceback.print_exc()  # Print full stack trace
            raise HTTPException(status_code=500, detail=f"Failed to create redirect: {str(e)}")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Unexpected Google callback error: {e}")
        import traceback
        traceback.print_exc()  # Print full stack trace
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    try:
        session_id = request.cookies.get("session_id")
        if session_id:
            db.clear_session(session_id)
        
        # Clear session cookie
        response.delete_cookie(
            "session_id",
            path="/"
        )
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        print(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session")
async def get_session(request: Request):
    """Get current session info"""
    try:
        session_id = request.cookies.get("session_id")
        print(f"Session check - session_id: {session_id[:20] if session_id else 'None'}...")  # Debug log
        
        if not session_id:
            print("No session_id found in cookies")  # Debug log
            return {"authenticated": False}
        
        print(f"Calling validate_session with: {session_id[:20]}...")  # Debug log
        user = db.validate_session(session_id)
        print(f"Session validation result: {user.get('email') if user else 'None'}")  # Debug log
        
        if not user:
            print("Session validation failed")  # Debug log
            return {"authenticated": False}
        
        has_google = bool(user.get("google_access_token"))
        has_hubspot = bool(user.get("hubspot_access_token"))
        
        print(f"User {user.get('email')} - has_google: {has_google}, has_hubspot: {has_hubspot}")  # Debug log
        
        return {
            "authenticated": True,
            "email": user["email"],
            "has_google": has_google,
            "has_hubspot": has_hubspot
        }
        
    except Exception as e:
        print(f"Session check error: {e}")
        return {"authenticated": False}

@router.get("/tokens")
async def get_tokens(request: Request):
    """Get current user's tokens (for internal use)"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="No session found")
        
        user = db.validate_session(session_id)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        return {
            "email": user["email"],
            "google_access_token": user.get("google_access_token"),
            "google_refresh_token": user.get("google_refresh_token"),
            "google_token_expires_at": user.get("google_token_expires_at"),
            "hubspot_access_token": user.get("hubspot_access_token"),
            "hubspot_refresh_token": user.get("hubspot_refresh_token"),
            "hubspot_token_expires_at": user.get("hubspot_token_expires_at")
        }
        
    except Exception as e:
        print(f"Get tokens error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === HUBSPOT OAUTH FLOW ===
HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
HUBSPOT_SCOPES = "crm.objects.contacts.read crm.objects.contacts.write"

@router.get("/hubspot")
async def hubspot_auth(request: Request):
    """
    Initiate HubSpot OAuth with HMAC-signed state parameter.
    
    Validates user session and creates a tamper-proof state token containing
    the user's email, which will be echoed back by HubSpot in the callback.
    Returns JSON with oauth_url for frontend consumption.
    """
    try:
        # Validate user session first
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="No session found. Please authenticate with Google first.")
        
        user = db.validate_session(session_id)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired session. Please authenticate with Google first.")
        
        print(f"Creating HubSpot OAuth state for user: {user.get('email')}")  # Debug log
        
        # Generate HMAC-signed state parameter containing user email
        state = make_state(user["email"])
        print(f"Generated state token: {state[:50]}...")  # Debug log
        
        # Build HubSpot authorization URL with state parameter
        auth_params = {
            "client_id": config.settings.HUBSPOT_CLIENT_ID,
            "redirect_uri": config.settings.HUBSPOT_REDIRECT_URI,
            "response_type": "code",
            "scope": HUBSPOT_SCOPES,
            "state": state  # Include signed state parameter
        }
        
        auth_url = HUBSPOT_AUTH_URL + "?" + urllib.parse.urlencode(auth_params)
        print(f"Generated HubSpot OAuth URL: {auth_url[:100]}...")  # Debug log
        
        # Return JSON with oauth_url instead of redirect
        return {"oauth_url": auth_url}
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"HubSpot auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hubspot/login")
async def hubspot_login():
    """Initiate HubSpot OAuth login"""
    oauth_url = get_hubspot_oauth_url()
    return {"oauth_url": oauth_url}

@router.get("/hubspot/callback")
async def hubspot_callback(code: str, request: Request, response: Response, state: str = None):
    """
    Handle HubSpot OAuth callback using HMAC-signed state parameter.
    
    Primary approach: Validates the state parameter to extract user email
    Fallback approach: If state is missing, tries to get email from session cookie
    
    This ensures we can always get the user email to save HubSpot tokens.
    """
    try:
        print(f"=== HubSpot OAuth Callback Start ===")  # Debug log
        print(f"HubSpot callback received with code: {code[:20]}...")  # Debug log
        print(f"State parameter: {state[:50] if state else 'None'}...")  # Debug log
        
        email = None
        
        # Primary approach: Try to get email from state parameter
        if state:
            try:
                email = verify_state(state)
                print(f"State validation successful, extracted email: {email}")  # Debug log
            except ValueError as e:
                print(f"State validation failed: {e}")  # Debug log
                print("Falling back to session-based email extraction...")  # Debug log
                email = None
        
        # Fallback approach: Get email from session if state failed or is missing
        if not email:
            print("Attempting to get email from session...")  # Debug log
            session_id = request.cookies.get("session_id")
            if not session_id:
                print("No session_id found in cookies")  # Debug log
                raise HTTPException(status_code=401, detail="No session found and no valid state parameter. Please authenticate with Google first.")
            
            user = db.validate_session(session_id)
            if not user:
                print("Session validation failed")  # Debug log
                raise HTTPException(status_code=401, detail="Invalid session and no valid state parameter. Please authenticate with Google first.")
            
            email = user.get("email")
            print(f"Got email from session: {email}")  # Debug log
        
        if not email:
            print("No email found from either state or session")  # Debug log
            raise HTTPException(status_code=400, detail="Could not determine user email from state or session")
        
        # Verify user exists in database
        user = db.get_user_by_email(email)
        if not user:
            print(f"No user found with email: {email}")  # Debug log
            raise HTTPException(status_code=400, detail="User not found in database")
        
        print(f"Found user: {email}")  # Debug log
        
        # Exchange code for tokens
        print(f"Exchanging HubSpot code for tokens...")  # Debug log
        tokens = await exchange_hubspot_code(code)
        if not tokens:
            print("Failed to exchange HubSpot code for tokens")  # Debug log
            raise HTTPException(status_code=400, detail="Failed to get HubSpot tokens")
        
        print(f"Successfully got HubSpot tokens")  # Debug log
        
        # Update user with HubSpot tokens
        hubspot_tokens = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": (datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))).isoformat()
        }
        
        print(f"Updating HubSpot tokens for user: {email}")  # Debug log
        success = db.update_hubspot_tokens(
            email,
            hubspot_tokens["access_token"],
            hubspot_tokens["refresh_token"],
            hubspot_tokens["expires_at"]
        )
        
        if not success:
            print(f"Failed to save HubSpot tokens to database")  # Debug log
            raise HTTPException(status_code=500, detail="Failed to save HubSpot tokens")
        
        print(f"HubSpot tokens saved successfully")  # Debug log
        
        # Redirect to frontend
        frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
        print(f"Redirecting to frontend: {frontend_url}")  # Debug log
        print(f"=== HubSpot OAuth Callback End ===")  # Debug log
        return RedirectResponse(url=f"{frontend_url}/")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Unexpected HubSpot callback error: {e}")
        import traceback
        traceback.print_exc()  # Print full stack trace
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/test-session")
async def test_session(request: Request):
    """Test endpoint to verify session functionality"""
    try:
        session_id = request.cookies.get("session_id")
        print(f"Test session - session_id: {session_id[:20] if session_id else 'None'}...")
        
        if not session_id:
            return {"message": "No session found", "cookies": dict(request.cookies)}
        
        user = db.validate_session(session_id)
        if not user:
            return {"message": "Invalid session", "session_id": session_id[:20]}
        
        return {
            "message": "Session valid",
            "user": {
                "email": user.get("email"),
                "has_google": bool(user.get("google_access_token")),
                "has_hubspot": bool(user.get("hubspot_access_token"))
            }
        }
        
    except Exception as e:
        print(f"Test session error: {e}")
        return {"message": f"Error: {str(e)}"}

@router.get("/debug-cookies")
async def debug_cookies(request: Request):
    """Debug endpoint to show all cookies and session info"""
    try:
        all_cookies = dict(request.cookies)
        session_id = request.cookies.get("session_id")
        
        print(f"All cookies: {all_cookies}")
        print(f"Session ID from cookie: {session_id}")
        
        if session_id:
            user = db.validate_session(session_id)
            if user:
                return {
                    "message": "Session found",
                    "cookies": all_cookies,
                    "session_id": session_id[:20] + "...",
                    "user": {
                        "email": user.get("email"),
                        "has_google": bool(user.get("google_access_token")),
                        "has_hubspot": bool(user.get("hubspot_access_token"))
                    }
                }
            else:
                return {
                    "message": "Session ID found but invalid",
                    "cookies": all_cookies,
                    "session_id": session_id[:20] + "..."
                }
        else:
            return {
                "message": "No session ID in cookies",
                "cookies": all_cookies,
                "headers": dict(request.headers)
            }
        
    except Exception as e:
        print(f"Debug cookies error: {e}")
        return {"message": f"Error: {str(e)}"}

@router.get("/test-cookie")
async def test_cookie(request: Request, response: Response):
    """Test endpoint to verify cookie setting works"""
    try:
        test_value = "test_cookie_value_123"
        
        # Set a test cookie
        response.set_cookie(
            key="test_cookie",
            value=test_value,
            httponly=False,
            secure=False,
            samesite="lax",
            max_age=3600,  # 1 hour
            path="/"
        )
        
        return {
            "message": "Test cookie set",
            "test_value": test_value,
            "existing_cookies": dict(request.cookies)
        }
        
    except Exception as e:
        print(f"Test cookie error: {e}")
        return {"message": f"Error: {str(e)}"}

@router.get("/set-session-and-redirect")
async def set_session_and_redirect(session_id: str):
    """Temporary endpoint to set session cookie and redirect"""
    try:
        print(f"Setting session cookie: {session_id[:20]}...")  # Debug log
        
        # Create the redirect response first
        frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
        redirect_response = RedirectResponse(url=f"{frontend_url}/", status_code=302)
        
        # Set the cookie on the redirect response (not on the response parameter)
        redirect_response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=False,  # Allow JavaScript access for debugging
            secure=False,    # Allow HTTP for local development
            samesite="lax",  # More permissive for local development
            max_age=24 * 60 * 60,  # 24 hours
            path="/",
            domain=None  # Let the browser set the domain automatically
        )
        
        print(f"Session cookie set, redirecting to frontend...")  # Debug log
        return redirect_response
        
    except Exception as e:
        print(f"Error in set-session-and-redirect: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug-set-session")
async def debug_set_session(session_id: str, request: Request, response: Response):
    """Debug endpoint to set session cookie and return info instead of redirecting"""
    try:
        print(f"Debug: Setting session cookie: {session_id[:20]}...")  # Debug log
        
        # Set the session cookie with more permissive settings for local development
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=False,  # Allow JavaScript access for debugging
            secure=False,    # Allow HTTP for local development
            samesite="lax",  # More permissive for local development
            max_age=24 * 60 * 60,  # 24 hours
            path="/",
            domain=None  # Let the browser set the domain automatically
        )
        
        print(f"Debug: Session cookie set successfully")  # Debug log
        
        return {
            "message": "Session cookie set",
            "session_id": session_id[:20] + "...",
            "cookies_set": ["session_id"],
            "all_cookies": dict(request.cookies)
        }
        
    except Exception as e:
        print(f"Error in debug-set-session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/manual-test-session/{session_id}")
async def manual_test_session(session_id: str):
    """Manually test session validation with a specific session ID"""
    try:
        print(f"Manual testing session: {session_id[:20]}...")
        
        # Test database validation directly
        user = db.validate_session(session_id)
        
        if user:
            return {
                "message": "Session is valid",
                "session_id": session_id[:20] + "...",
                "user": {
                    "email": user.get("email"),
                    "has_google": bool(user.get("google_access_token")),
                    "has_hubspot": bool(user.get("hubspot_access_token")),
                    "session_expires_at": user.get("session_expires_at")
                }
            }
        else:
            return {
                "message": "Session is invalid or expired",
                "session_id": session_id[:20] + "..."
            }
        
    except Exception as e:
        print(f"Manual test session error: {e}")
        return {"message": f"Error: {str(e)}"}

@router.get("/debug-hubspot-session")
async def debug_hubspot_session(request: Request):
    """Debug endpoint to check session status before HubSpot auth"""
    try:
        session_id = request.cookies.get("session_id")
        print(f"Debug HubSpot session - session_id: {session_id[:20] if session_id else 'None'}...")
        
        if not session_id:
            return {
                "message": "No session found in cookies",
                "cookies": dict(request.cookies),
                "can_proceed_with_hubspot": False,
                "reason": "No session_id in cookies"
            }
        
        # Try to get user by session_id directly
        direct_user = db.get_user_by_session_id(session_id)
        if not direct_user:
            return {
                "message": "No user found with session_id",
                "session_id": session_id[:20] + "...",
                "can_proceed_with_hubspot": False,
                "reason": "Session ID not found in database"
            }
        
        # Try to validate session
        user = db.validate_session(session_id)
        if not user:
            return {
                "message": "Session validation failed",
                "session_id": session_id[:20] + "...",
                "user_email": direct_user.get("email"),
                "session_expires_at": direct_user.get("session_expires_at"),
                "can_proceed_with_hubspot": False,
                "reason": "Session expired or invalid"
            }
        
        return {
            "message": "Session is valid",
            "session_id": session_id[:20] + "...",
            "user_email": user.get("email"),
            "session_expires_at": user.get("session_expires_at"),
            "has_google": bool(user.get("google_access_token")),
            "has_hubspot": bool(user.get("hubspot_access_token")),
            "can_proceed_with_hubspot": True,
            "reason": "Session is valid and ready for HubSpot auth"
        }
        
    except Exception as e:
        print(f"Debug HubSpot session error: {e}")
        return {
            "message": f"Error: {str(e)}",
            "can_proceed_with_hubspot": False,
            "reason": "Error occurred during session check"
        }

@router.get("/debug-hubspot-oauth-url")
async def debug_hubspot_oauth_url(request: Request):
    """Debug endpoint to generate and show the HubSpot OAuth URL with state"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return {
                "error": "No session found",
                "message": "Please authenticate with Google first"
            }
        
        user = db.validate_session(session_id)
        if not user:
            return {
                "error": "Invalid session",
                "message": "Please authenticate with Google first"
            }
        
        email = user.get("email")
        print(f"Generating OAuth URL for user: {email}")
        
        # Generate state parameter
        state = make_state(email)
        print(f"Generated state: {state}")
        
        # Build OAuth URL
        auth_params = {
            "client_id": config.settings.HUBSPOT_CLIENT_ID,
            "redirect_uri": config.settings.HUBSPOT_REDIRECT_URI,
            "response_type": "code",
            "scope": HUBSPOT_SCOPES,
            "state": state
        }
        
        auth_url = HUBSPOT_AUTH_URL + "?" + urllib.parse.urlencode(auth_params)
        
        return {
            "message": "HubSpot OAuth URL generated successfully",
            "user_email": email,
            "state_parameter": state,
            "state_length": len(state),
            "oauth_url": auth_url,
            "oauth_url_length": len(auth_url),
            "parameters": auth_params
        }
        
    except Exception as e:
        print(f"Debug HubSpot OAuth URL error: {e}")
        return {
            "error": f"Failed to generate OAuth URL: {str(e)}"
        }

@router.get("/debug-hubspot-callback-test")
async def debug_hubspot_callback_test(code: str = None, state: str = None, request: Request = None):
    """
    Debug endpoint to test what parameters HubSpot sends in callback
    """
    try:
        # Get all query parameters
        query_params = dict(request.query_params) if request else {}
        
        # Get cookies
        cookies = dict(request.cookies) if request else {}
        
        # Get session info
        session_id = cookies.get("session_id")
        session_user = None
        if session_id:
            session_user = db.validate_session(session_id)
        
        return {
            "message": "HubSpot callback debug info",
            "query_parameters": query_params,
            "cookies": cookies,
            "session_id": session_id[:20] + "..." if session_id else None,
            "session_user": {
                "email": session_user.get("email") if session_user else None,
                "has_google": bool(session_user.get("google_access_token")) if session_user else False,
                "has_hubspot": bool(session_user.get("hubspot_access_token")) if session_user else False
            } if session_user else None,
            "state_analysis": {
                "state_present": bool(state),
                "state_length": len(state) if state else 0,
                "state_preview": state[:50] + "..." if state else None
            } if state else None
        }
        
    except Exception as e:
        return {
            "error": f"Debug error: {str(e)}",
            "query_parameters": dict(request.query_params) if request else {},
            "cookies": dict(request.cookies) if request else {}
        }
