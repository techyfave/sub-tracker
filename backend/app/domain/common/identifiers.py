from __future__ import annotations

from uuid import UUID, uuid4

type Identifier = UUID


def new_identifier() -> Identifier:
    """Create a new application identifier."""

    return uuid4()