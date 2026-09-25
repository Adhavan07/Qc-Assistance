"""
Unit tests for password hashing, bcrypt verification, and JWT security tokens.
"""

from datetime import timedelta
import pytest
from fastapi import HTTPException

from backend.src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_pass = "SuperSecretPassword123!"
    hashed = hash_password(raw_pass)

    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_issuance_and_decoding():
    token = create_access_token(
        subject="user_123",
        tenant_id="org_456",
        role="ENGINEER",
        expires_delta=timedelta(minutes=15),
    )

    payload = decode_access_token(token)
    assert payload["sub"] == "user_123"
    assert payload["org_id"] == "org_456"
    assert payload["role"] == "ENGINEER"


def test_expired_jwt_token_rejection():
    # Token expired 1 second ago
    expired_token = create_access_token(
        subject="user_expired",
        tenant_id="org_expired",
        role="INSPECTOR",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(HTTPException) as exc:
        decode_access_token(expired_token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_tampered_jwt_token_rejection():
    token = create_access_token(
        subject="user_normal",
        tenant_id="org_normal",
        role="INSPECTOR",
    )
    tampered_token = token[:-5] + "AAAAA"

    with pytest.raises(HTTPException) as exc:
        decode_access_token(tampered_token)
    assert exc.value.status_code == 401
