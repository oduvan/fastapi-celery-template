"""Tests for Celery tasks."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.celery import celery_app


@pytest.fixture
def mock_celery_task():
    """Create a mock Celery task result."""

    def _create_mock(task_id="test-task-id"):
        mock = MagicMock()
        mock.id = task_id
        return mock

    return _create_mock


@pytest.fixture
def celery_eager():
    """Configure Celery to run tasks eagerly (synchronously) for testing."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


# Items tasks unit tests


def test_process_item_task(celery_eager):
    """Test process_item task logic."""
    from app.items.tasks import process_item

    with patch("app.items.tasks.time.sleep"):
        result = process_item.delay(item_id=1, operation="validate")

    assert result.successful()
    data = result.result
    assert data["item_id"] == 1
    assert data["operation"] == "validate"
    assert data["status"] == "completed"


def test_process_item_default_operation(celery_eager):
    """Test process_item with default operation."""
    from app.items.tasks import process_item

    with patch("app.items.tasks.time.sleep"):
        result = process_item.delay(item_id=5)

    assert result.successful()
    assert result.result["operation"] == "validate"


def test_bulk_import_task(celery_eager):
    """Test bulk_import task logic."""
    from app.items.tasks import bulk_import

    items = [{"name": "Item 1"}, {"name": "Item 2"}, {"name": "Item 3"}]

    with patch("app.items.tasks.time.sleep"):
        result = bulk_import.delay(items)

    assert result.successful()
    data = result.result
    assert data["status"] == "completed"
    assert data["total_items"] == 3
    assert data["processed"] == 3


# Files tasks unit tests


def test_process_file_task(celery_eager):
    """Test process_file task logic."""
    from app.files.tasks import process_file

    with patch("app.files.tasks.time.sleep"):
        result = process_file.delay(filename="test.pdf", operation="scan")

    assert result.successful()
    data = result.result
    assert data["filename"] == "test.pdf"
    assert data["operation"] == "scan"
    assert data["status"] == "completed"


def test_process_file_default_operation(celery_eager):
    """Test process_file with default operation."""
    from app.files.tasks import process_file

    with patch("app.files.tasks.time.sleep"):
        result = process_file.delay(filename="doc.txt")

    assert result.successful()
    assert result.result["operation"] == "analyze"


def test_cleanup_old_files_task(celery_eager):
    """Test cleanup_old_files task logic."""
    from app.files.tasks import cleanup_old_files

    with patch("app.files.tasks.time.sleep"):
        result = cleanup_old_files.delay(max_age_days=7)

    assert result.successful()
    data = result.result
    assert data["status"] == "completed"
    assert data["max_age_days"] == 7


# API endpoint tests - Items


@pytest.mark.asyncio
async def test_create_process_item_task(client: AsyncClient, mock_celery_task):
    """Test creating a process item task via API."""
    with patch("app.celery_tasks.router.process_item") as mock_task:
        mock_task.delay.return_value = mock_celery_task("item-task-123")

        response = await client.post(
            "/celery/items/process", json={"item_id": 1, "operation": "enrich"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "item-task-123"
        assert data["status"] == "PENDING"
        mock_task.delay.assert_called_once_with(1, "enrich")


@pytest.mark.asyncio
async def test_create_bulk_import_task(client: AsyncClient, mock_celery_task):
    """Test creating a bulk import task via API."""
    with patch("app.celery_tasks.router.bulk_import") as mock_task:
        mock_task.delay.return_value = mock_celery_task("import-task-456")

        items = [{"name": "Item 1"}, {"name": "Item 2"}]
        response = await client.post("/celery/items/bulk-import", json={"items": items})

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "import-task-456"
        mock_task.delay.assert_called_once_with(items)


# API endpoint tests - Files


@pytest.mark.asyncio
async def test_create_process_file_task(client: AsyncClient, mock_celery_task):
    """Test creating a process file task via API."""
    with patch("app.celery_tasks.router.process_file") as mock_task:
        mock_task.delay.return_value = mock_celery_task("file-task-789")

        response = await client.post(
            "/celery/files/process", json={"filename": "doc.pdf", "operation": "convert"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "file-task-789"
        mock_task.delay.assert_called_once_with("doc.pdf", "convert")


@pytest.mark.asyncio
async def test_create_cleanup_files_task(client: AsyncClient, mock_celery_task):
    """Test creating a cleanup files task via API."""
    with patch("app.celery_tasks.router.cleanup_old_files") as mock_task:
        mock_task.delay.return_value = mock_celery_task("cleanup-task-101")

        response = await client.post("/celery/files/cleanup", json={"max_age_days": 14})

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "cleanup-task-101"
        mock_task.delay.assert_called_once_with(14)


# API endpoint tests - Task status


@pytest.mark.asyncio
async def test_get_task_status_pending(client: AsyncClient):
    """Test getting status of a pending task."""
    with patch("app.celery_tasks.router.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.status = "PENDING"
        mock_instance.ready.return_value = False
        mock_result.return_value = mock_instance

        response = await client.get("/celery/status/test-task-id")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "PENDING"
        assert data["result"] is None


@pytest.mark.asyncio
async def test_get_task_status_success(client: AsyncClient):
    """Test getting status of a completed task."""
    with patch("app.celery_tasks.router.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.status = "SUCCESS"
        mock_instance.ready.return_value = True
        mock_instance.successful.return_value = True
        mock_instance.result = {"result": 42}
        mock_result.return_value = mock_instance

        response = await client.get("/celery/status/completed-task-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"] == {"result": 42}


@pytest.mark.asyncio
async def test_get_task_status_failure(client: AsyncClient):
    """Test getting status of a failed task."""
    with patch("app.celery_tasks.router.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.status = "FAILURE"
        mock_instance.ready.return_value = True
        mock_instance.successful.return_value = False
        mock_instance.result = Exception("Task failed")
        mock_result.return_value = mock_instance

        response = await client.get("/celery/status/failed-task-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILURE"
        assert data["error"] == "Task failed"


@pytest.mark.asyncio
async def test_get_task_status_progress(client: AsyncClient):
    """Test getting status of a task in progress."""
    with patch("app.celery_tasks.router.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.status = "PROGRESS"
        mock_instance.ready.return_value = False
        mock_instance.info = {"current": 5, "total": 10, "percent": 50}
        mock_result.return_value = mock_instance

        response = await client.get("/celery/status/progress-task-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PROGRESS"
        assert data["result"] == {"current": 5, "total": 10, "percent": 50}


@pytest.mark.asyncio
async def test_revoke_task(client: AsyncClient):
    """Test revoking a pending task."""
    with patch("app.celery_tasks.router.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.ready.return_value = False
        mock_result.return_value = mock_instance

        with patch("app.celery_tasks.router.celery_app") as mock_app:
            response = await client.delete("/celery/revoke/task-to-revoke")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-to-revoke"
            assert data["status"] == "revoked"
            mock_app.control.revoke.assert_called_once_with("task-to-revoke", terminate=True)


@pytest.mark.asyncio
async def test_revoke_completed_task(client: AsyncClient):
    """Test revoking an already completed task."""
    with patch("app.celery_tasks.router.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.ready.return_value = True
        mock_result.return_value = mock_instance

        response = await client.delete("/celery/revoke/completed-task")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Task already completed"
