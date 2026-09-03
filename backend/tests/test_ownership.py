from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.dependencies.auth import ensure_owner
from app.domain.users.entities import User


def _user(user_id) -> User:
    return User(
        id=user_id,
        email="owner@example.com",
        hashed_password="irrelevant",
        is_active=True,
        created_at=datetime.now(UTC),
    )


def test_ensure_owner_allows_the_resources_own_user() -> None:
    owner_id = uuid4()

    ensure_owner(resource_owner_id=owner_id, current_user=_user(owner_id))  # must not raise


def test_ensure_owner_denies_a_different_user() -> None:
    resource_owner_id = uuid4()
    other_user = _user(uuid4())

    with pytest.raises(HTTPException) as excinfo:
        ensure_owner(resource_owner_id=resource_owner_id, current_user=other_user)

    assert excinfo.value.status_code == 403
