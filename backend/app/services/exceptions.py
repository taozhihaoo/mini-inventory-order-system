"""Domain exceptions mapped to uniform API error responses."""

from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"
    default_message = "Invalid request."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    default_message = "Validation failed."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    default_message = "Conflicting state."


class DuplicateError(ConflictError):
    code = "duplicate"
    default_message = "A record with the same unique value already exists."


class ReferencedError(ConflictError):
    code = "referenced_by_other_records"
    default_message = "Record is referenced by other records and cannot be deleted."


class InsufficientStockError(ConflictError):
    code = "insufficient_stock"
    default_message = "Insufficient stock."


class InvalidStateTransitionError(ConflictError):
    code = "invalid_state_transition"
    default_message = "Operation is not allowed for the current status."
