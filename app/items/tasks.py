"""Celery tasks for items module."""

import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="items.process_item")
def process_item(self, item_id: int, operation: str = "validate") -> dict:
    """
    Process an item asynchronously.

    Example task that simulates item processing like validation,
    enrichment, or external API calls.

    Args:
        item_id: ID of the item to process
        operation: Type of operation (validate, enrich, sync)

    Returns:
        dict with processing result
    """
    logger.info(f"Task {self.request.id}: Processing item {item_id} with operation={operation}")

    # Simulate processing time
    time.sleep(2)

    result = {
        "task_id": self.request.id,
        "item_id": item_id,
        "operation": operation,
        "status": "completed",
    }

    logger.info(f"Task {self.request.id}: Item {item_id} processing completed")
    return result


@shared_task(bind=True, name="items.bulk_import")
def bulk_import(self, items_data: list[dict]) -> dict:
    """
    Bulk import items asynchronously.

    Processes a list of items with progress updates.

    Args:
        items_data: List of item data dictionaries

    Returns:
        dict with import results
    """
    total = len(items_data)
    logger.info(f"Task {self.request.id}: Starting bulk import of {total} items")

    processed = 0
    for i, _item in enumerate(items_data):
        # Simulate processing each item
        time.sleep(0.5)
        processed += 1

        # Update progress
        progress = ((i + 1) / total) * 100
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": total, "percent": progress},
        )
        logger.info(f"Task {self.request.id}: Progress {progress:.0f}%")

    logger.info(f"Task {self.request.id}: Bulk import completed")
    return {
        "task_id": self.request.id,
        "status": "completed",
        "total_items": total,
        "processed": processed,
    }
