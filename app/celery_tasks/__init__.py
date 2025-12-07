"""Celery tasks router module.

Tasks are distributed across domain modules:
- app.items.tasks - Item-related tasks
- app.files.tasks - File-related tasks

Each domain module has its own tasks.py file that is autodiscovered by Celery.
"""

from app.celery_tasks.router import router

__all__ = ["router"]
