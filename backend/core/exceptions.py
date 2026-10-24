"""Domain exceptions mapped to clean HTTP errors (no stack traces to users)."""
from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "app_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidImageError(AppError):
    status_code = 400
    code = "invalid_image"


class UnsupportedImageFormat(InvalidImageError):
    code = "unsupported_image_format"


class ImageTooLarge(InvalidImageError):
    status_code = 413
    code = "image_too_large"


class ModelUnavailableError(AppError):
    status_code = 503
    code = "model_unavailable"


class PredictionFailure(AppError):
    status_code = 500
    code = "prediction_failed"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class Conflict(AppError):
    status_code = 409
    code = "conflict"
