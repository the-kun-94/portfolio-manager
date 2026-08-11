"""
Shared API key gate — this app is deployed publicly with no other login,
so every real endpoint requires a matching X-API-Key header. Only enforced
when API_KEY is actually set; local dev leaves it unset so nothing needs
to change to keep working against SQLite.
"""
from fastapi import Header, HTTPException, status

from app.config import API_KEY


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
