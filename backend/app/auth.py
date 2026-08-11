"""
Shared API key gate — this app is deployed publicly with no other login,
so every real endpoint requires a matching X-API-Key header. Only enforced
when API_KEY is actually set; local dev leaves it unset so nothing needs
to change to keep working against SQLite.

Two keys are supported: API_KEY (full read/write) and the optional
API_KEY_READONLY (read-only). get_access_level resolves which one a
request used; require_write_access is a second gate layered on top of it
for write endpoints (POST /api/trades, /api/cash/deposit,
/api/cash/withdraw, /api/reinvestment/park, /api/reinvestment/unpark) so a
read-only key can authenticate but never mutate anything — enforced here,
not just hidden in the frontend, since a caller could otherwise hit the
API directly with a key pulled from the client bundle.
"""
from typing import Literal

from fastapi import Depends, Header, HTTPException, status

from app.config import API_KEY, API_KEY_READONLY

AccessLevel = Literal["write", "read"]


def get_access_level(x_api_key: str | None = Header(default=None)) -> AccessLevel:
    if not API_KEY:
        return "write"
    if x_api_key == API_KEY:
        return "write"
    if API_KEY_READONLY and x_api_key == API_KEY_READONLY:
        return "read"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key",
    )


def require_write_access(access_level: AccessLevel = Depends(get_access_level)) -> None:
    if access_level != "write":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key is read-only and cannot perform write actions.",
        )
