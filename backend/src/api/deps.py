"""
FastAPI Dependency Injection Providers.
"""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings, settings
from ..infrastructure.database import get_db_session
from ..infrastructure.queue import TaskQueueInterface, default_task_queue
from ..infrastructure.storage import StorageServiceInterface, get_storage_service


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_storage() -> StorageServiceInterface:
    return get_storage_service()


def get_queue() -> TaskQueueInterface:
    return default_task_queue


def get_app_settings() -> Settings:
    return settings
