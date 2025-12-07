"""Celery tasks API endpoints."""

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.celery import celery_app
from app.files.tasks import cleanup_old_files, process_file
from app.items.tasks import bulk_import, process_item

router = APIRouter()


# Request schemas
class ProcessItemRequest(BaseModel):
    """Request schema for process item task."""

    item_id: int
    operation: str = "validate"


class BulkImportRequest(BaseModel):
    """Request schema for bulk import task."""

    items: list[dict]


class ProcessFileRequest(BaseModel):
    """Request schema for process file task."""

    filename: str
    operation: str = "analyze"


class CleanupFilesRequest(BaseModel):
    """Request schema for cleanup files task."""

    max_age_days: int = 30


# Response schemas
class TaskResponse(BaseModel):
    """Response schema for task submission."""

    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response schema for task status."""

    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


# Items tasks endpoints
@router.post("/items/process", response_model=TaskResponse)
async def create_process_item_task(request: ProcessItemRequest):
    """
    Submit a task to process an item.

    Operations: validate, enrich, sync
    """
    task = process_item.delay(request.item_id, request.operation)
    return TaskResponse(task_id=task.id, status="PENDING")


@router.post("/items/bulk-import", response_model=TaskResponse)
async def create_bulk_import_task(request: BulkImportRequest):
    """
    Submit a bulk import task.

    Progress can be tracked via the status endpoint.
    """
    task = bulk_import.delay(request.items)
    return TaskResponse(task_id=task.id, status="PENDING")


# Files tasks endpoints
@router.post("/files/process", response_model=TaskResponse)
async def create_process_file_task(request: ProcessFileRequest):
    """
    Submit a task to process a file.

    Operations: analyze, scan, convert, compress
    """
    task = process_file.delay(request.filename, request.operation)
    return TaskResponse(task_id=task.id, status="PENDING")


@router.post("/files/cleanup", response_model=TaskResponse)
async def create_cleanup_files_task(request: CleanupFilesRequest):
    """
    Submit a task to clean up old files.

    Deletes files older than max_age_days.
    """
    task = cleanup_old_files.delay(request.max_age_days)
    return TaskResponse(task_id=task.id, status="PENDING")


# Common task management endpoints
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a Celery task.

    Returns current status and result if available.
    """
    result = AsyncResult(task_id, app=celery_app)

    response = TaskStatusResponse(
        task_id=task_id,
        status=result.status,
    )

    if result.ready():
        if result.successful():
            response.result = result.result
        else:
            response.error = str(result.result)
    elif result.status == "PROGRESS":
        response.result = result.info

    return response


@router.delete("/revoke/{task_id}")
async def revoke_task(task_id: str):
    """
    Revoke (cancel) a pending or running task.

    Note: Running tasks can only be terminated if workers have SIGTERM support.
    """
    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        raise HTTPException(status_code=400, detail="Task already completed")

    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "status": "revoked"}
