"""Application error types.

Every message carried by these exceptions is written for the end user
(in Persian) and can be shown directly in the interface.
"""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class StorageError(AppError):
    pass
