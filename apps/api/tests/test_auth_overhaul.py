from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from pwdlib.hashers.bcrypt import BcryptHasher
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.services.security import verify_password_and_update


@pytest.mark.asyncio
async def test_registration_requires_a_strong_password(client: AsyncClient):
    weak_passwords = [
        "short1A",
        "alllowercase123",
        "ALLUPPERCASE123",
        "NoNumbersHere!",
    ]
    for index, password in enumerate(weak_passwords):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"weak{index}@studyflow.edu",
                "password": password,
                "display_name": "Student",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_password_change_rotates_token_and_revokes_old_sessions(client: AsyncClient):
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "secure.student@studyflow.edu",
            "password": old_password,
            "display_name": "Secure Student",
        },
    )
    assert registration.status_code == 201
    old_token = registration.json()["access_token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    bad_change = await client.post(
        "/api/v1/auth/change-password",
        headers=old_headers,
        json={"current_password": "incorrect", "new_password": new_password},
    )
    assert bad_change.status_code == 400
    assert (await client.get("/api/v1/auth/me", headers=old_headers)).status_code == 200

    change = await client.post(
        "/api/v1/auth/change-password",
        headers=old_headers,
        json={"current_password": old_password, "new_password": new_password},
    )
    assert change.status_code == 200
    change_data = change.json()
    assert change_data["expires_in"] == get_settings().access_token_expire_minutes * 60
    new_headers = {"Authorization": f"Bearer {change_data['access_token']}"}

    assert (await client.get("/api/v1/auth/me", headers=old_headers)).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers=new_headers)).status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "secure.student@studyflow.edu", "password": old_password},
    )
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "secure.student@studyflow.edu", "password": new_password},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_access_tokens_require_the_expected_issuer(client: AsyncClient):
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "1",
            "iss": "some-other-service",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            "jti": "forged-session-id",
            "pwd_sig": "not-a-valid-password-signature",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_legacy_bcrypt_hashes_verify_and_upgrade_to_argon2id():
    password = "LegacyPassword123!"
    legacy_hash = BcryptHasher().hash(password)

    verified, upgraded_hash = verify_password_and_update(password, legacy_hash)

    assert verified is True
    assert upgraded_hash is not None
    assert upgraded_hash.startswith("$argon2id$")


def test_example_jwt_secret_is_rejected():
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="replace-this-with-a-random-32-byte-secret")
