"""Domain exceptions for the Procurement bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class ProcurementDomainError(DomainError):
    """Base class for all Procurement domain exceptions."""


class PRNotFoundError(ProcurementDomainError, DomainNotFoundError):
    """Raised when a Purchase Requisition cannot be located.

    Args:
        pr_id: The identifier that was searched for.
    """

    def __init__(self, pr_id: object) -> None:
        super().__init__(f"Purchase Requisition not found: '{pr_id}'.")
        self.pr_id = pr_id


class PONotFoundError(ProcurementDomainError, DomainNotFoundError):
    """Raised when a Purchase Order cannot be located.

    Args:
        po_id: The identifier that was searched for.
    """

    def __init__(self, po_id: object) -> None:
        super().__init__(f"Purchase Order not found: '{po_id}'.")
        self.po_id = po_id


class GoodsDocumentNotFoundError(ProcurementDomainError, DomainNotFoundError):
    """Raised when a Goods Receipt or Goods Issue document cannot be located.

    Args:
        doc_id: The identifier that was searched for.
    """

    def __init__(self, doc_id: object) -> None:
        super().__init__(f"Goods document not found: '{doc_id}'.")
        self.doc_id = doc_id


class ProcurementInvalidStateTransitionError(ProcurementDomainError, DomainStateError):
    """Raised when a procurement document status transition is not permitted.

    Args:
        document_type: The type of procurement document (e.g. "PurchaseOrder").
        current_status: The current status.
        target_status: The attempted target status.
    """

    def __init__(
        self, document_type: str, current_status: str, target_status: str
    ) -> None:
        super().__init__(
            f"Cannot transition {document_type} from '{current_status}' "
            f"to '{target_status}'."
        )
        self.document_type = document_type
        self.current_status = current_status
        self.target_status = target_status
