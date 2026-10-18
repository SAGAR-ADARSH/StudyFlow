from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.errors import http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentTextResponse,
    QuizGenerateRequest,
    QuizResponse,
    SummaryGenerateRequest,
    SummaryResponse,
)
from app.services.document_service import document_service
from app.services.insight_service import insight_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="A PDF file (.pdf)")],
    title: Annotated[str | None, Form(max_length=180)] = None,
    subject_id: Annotated[int | None, Form(gt=0)] = None,
    semester_id: Annotated[int | None, Form(gt=0)] = None,
):
    """Upload a PDF, extract its text, and report the processing outcome."""
    try:
        data = await document_service.read_upload(file)
        return await document_service.create_from_upload(
            db,
            current_user.id,
            data=data,
            filename=file.filename or "document.pdf",
            title=title,
            subject_id=subject_id,
            semester_id=semester_id,
        )
    except Exception as error:  # mapped to a meaningful HTTP status
        raise http_error(error) from error


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str | None = Query(None, alias="q", max_length=120),
    subject_id: int | None = Query(None, gt=0),
    semester_id: int | None = Query(None, gt=0),
    processing_status: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    try:
        items = await document_service.list_documents(
            db,
            current_user.id,
            query=query,
            subject_id=subject_id,
            semester_id=semester_id,
            status=processing_status,
            limit=limit,
            offset=offset,
        )
    except Exception as error:
        raise http_error(error) from error
    return DocumentListResponse(
        items=items, total=len(items), limit=limit, offset=offset
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    document = await document_service.get_document(db, current_user.id, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.get("/{document_id}/text", response_model=DocumentTextResponse)
async def get_document_text(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await document_service.get_text(db, current_user.id, document_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document, text = result
    return DocumentTextResponse(
        document_id=document.id,
        title=document.title,
        processing_status=document.processing_status,
        page_count=document.page_count,
        extracted_chars=document.extracted_chars,
        text_truncated=document.text_truncated,
        text=text or None,
    )


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-run text extraction, e.g. after a failed or corrupt upload."""
    try:
        document = await document_service.reprocess(db, current_user.id, document_id)
    except Exception as error:
        raise http_error(error) from error
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await document_service.delete(db, current_user.id, document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.post(
    "/{document_id}/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_summary(
    document_id: int,
    payload: SummaryGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate (or regenerate) an extractive summary of one document."""
    try:
        return await insight_service.generate_summary(
            db,
            current_user.id,
            document_id=document_id,
            max_words=payload.max_words,
            max_key_points=payload.max_key_points,
        )
    except Exception as error:
        raise http_error(error) from error


@router.get("/{document_id}/summary", response_model=SummaryResponse)
async def get_summary(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        summary = await insight_service.latest_summary(db, current_user.id, document_id=document_id)
    except Exception as error:
        raise http_error(error) from error
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary has been generated for this document yet.",
        )
    return summary


@router.get("/{document_id}/summaries", response_model=list[SummaryResponse])
async def list_summaries(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50),
):
    try:
        return await insight_service.list_summaries(
            db, current_user.id, document_id=document_id, limit=limit
        )
    except Exception as error:
        raise http_error(error) from error


@router.post("/{document_id}/quiz", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    document_id: int,
    payload: QuizGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate a multiple-choice quiz from the document's extracted text."""
    try:
        return await insight_service.generate_quiz(
            db,
            current_user.id,
            document_id=document_id,
            question_count=payload.question_count,
        )
    except Exception as error:
        raise http_error(error) from error


@router.get("/{document_id}/quizzes", response_model=list[QuizResponse])
async def list_document_quizzes(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50),
):
    try:
        return await insight_service.list_quizzes(
            db, current_user.id, document_id=document_id, limit=limit
        )
    except Exception as error:
        raise http_error(error) from error

