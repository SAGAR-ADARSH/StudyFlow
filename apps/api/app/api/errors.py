"""Shared translation of service-layer errors into HTTP responses."""
import logging

from fastapi import HTTPException, status

from app.services.document_service import DocumentValidationError
from app.services.quiz_engine import InsufficientContentError

logger = logging.getLogger("studyflow.api")


def http_error(error: Exception) -> HTTPException:
    """Map the exceptions raised by services onto the right status code."""
    if isinstance(error, HTTPException):
        return error
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, InsufficientContentError):
        return HTTPException(
            # 422 Unprocessable Content: the request is valid, the source is not usable.
            status_code=422,
            detail={"code": error.code, "message": str(error)},
        )
    if isinstance(error, DocumentValidationError):
        return HTTPException(
            status_code=getattr(error, "status_code", status.HTTP_400_BAD_REQUEST),
            detail={"code": error.code, "message": error.message},
        )
    if isinstance(error, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    logger.exception("Unhandled error in the document/insight flow")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Something went wrong while processing this request.",
    )


def detail_message(error: object) -> str:
    """Flatten the ``{"code", "message"}`` detail shape into one readable string."""
    detail = getattr(error, "detail", None)
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("code") or error)
    if isinstance(detail, str):
        return detail
    return str(error)
