"""Helpers that translate domain exceptions into application/API exceptions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.domain.exceptions import DomainNotFoundError
from core.exceptions.base_exception import FMMSNotFoundError


def load_or_not_found[
    T
](
    loader: Callable[[], T],
    *,
    message: str,
    details: dict[str, Any] | None = None,
) -> T:
    """Execute a repository load and map domain not-found to ``FMMSNotFoundError``.

    Supports both contracts used in FMMS:
    - Repositories that raise ``DomainNotFoundError`` (production Django repos).
    - Test doubles that return ``None`` for missing entities.

    Args:
        loader: Zero-arg callable that loads the entity.
        message: Human-readable not-found message for the API body.
        details: Structured details for the API error payload.

    Returns:
        The loaded entity.

    Raises:
        FMMSNotFoundError: If the loader raises ``DomainNotFoundError`` or
            returns ``None``.
    """
    try:
        entity = loader()
    except DomainNotFoundError as exc:
        raise FMMSNotFoundError(message=message, details=details) from exc
    if entity is None:
        raise FMMSNotFoundError(message=message, details=details)
    return entity
