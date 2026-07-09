"""Shared domain exception hierarchy for FMMS bounded contexts.

Bounded-context exception modules inherit from these bases so the API
layer can map categories (not-found vs state) without knowing about
vehicle, repair, or other domain types.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all FMMS domain-layer exceptions.

    Domain entities and repositories raise subclasses of this type.
    Application services translate not-found cases into ``FMMSNotFoundError``
    for the API. State violations may surface as ``DomainStateError`` and are
    mapped to HTTP 422 by the global exception handler.
    """


class DomainNotFoundError(DomainError):
    """Base for resource-not-found errors raised by repositories/entities.

    Application services must catch this type (or subclasses) and re-raise
    ``FMMSNotFoundError``. The global HTTP handler must not gain
    domain-specific not-found knowledge.
    """


class DomainStateError(DomainError):
    """Base for invalid aggregate state / illegal state-machine transitions.

    Propagates from domain entities through application services without
    weakening domain rules. The HTTP layer maps this category to 422.
    """
