import hmac
import hashlib
import base64
import time
from app import config


def make_state(email: str, max_age: int = 300) -> str:
    """
    Create a tamper-proof state parameter for OAuth flows.
    
    Args:
        email: User's email address to encode in state
        max_age: Maximum age of state token in seconds (default: 5 minutes)
    
    Returns:
        Base64 encoded string in format: base64(email|timestamp).base64(signature)
    """
    ts = int(time.time())
    payload = f"{email}|{ts}".encode()
    
    # Create HMAC signature using app secret
    sig = hmac.new(
        config.settings.APP_SECRET.encode(), 
        payload, 
        hashlib.sha256
    ).digest()
    
    # Return base64(payload).base64(signature)
    return (
        base64.urlsafe_b64encode(payload).decode()
        + '.'
        + base64.urlsafe_b64encode(sig).decode()
    )


def verify_state(state: str, max_age: int = 300) -> str:
    """
    Validate and extract email from state parameter.
    
    Args:
        state: State parameter from OAuth callback
        max_age: Maximum age of state token in seconds (default: 5 minutes)
    
    Returns:
        User's email address if state is valid
    
    Raises:
        ValueError: If state is expired, malformed, or has invalid signature
    """
    try:
        # Split payload and signature
        b64_payload, b64_sig = state.split('.')
        
        # Decode payload and extract email and timestamp
        payload = base64.urlsafe_b64decode(b64_payload)
        email, ts_str = payload.decode().split('|')
        ts = int(ts_str)
        
        # Check if state has expired
        if time.time() - ts > max_age:
            raise ValueError('State token has expired')
        
        # Verify HMAC signature
        expected_sig = hmac.new(
            config.settings.APP_SECRET.encode(), 
            payload, 
            hashlib.sha256
        ).digest()
        sig = base64.urlsafe_b64decode(b64_sig)
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_sig, sig):
            raise ValueError('Invalid state signature')
        
        return email
        
    except (ValueError, IndexError, UnicodeDecodeError) as e:
        # Re-raise with more descriptive error
        raise ValueError(f'Malformed state parameter: {str(e)}') 