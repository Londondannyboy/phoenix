"""
Authentication middleware for Phoenix Gateway.
"""

import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    expected_key = os.getenv("API_KEY")

    # Skip auth in development if no key configured
    if not expected_key:
        return "development"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return api_key
