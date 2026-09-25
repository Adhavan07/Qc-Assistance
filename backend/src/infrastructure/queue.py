"""
Asynchronous Background Task Queue Abstraction.
Provides decoupled worker job dispatching for long-running QC jobs.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class QCJobPayload(BaseModel):
    qc_run_id: str
    document_id: str
    organization_id: str
    file_path: str
    standards: List[str]


class TaskQueueInterface(ABC):
    @abstractmethod
    async def enqueue(self, payload: QCJobPayload) -> str:
        """Enqueue a QC job and return job dispatch ID."""
        pass

    @abstractmethod
    async def dequeue(self, timeout_seconds: float = 1.0) -> Optional[QCJobPayload]:
        """Dequeue next available job."""
        pass

    @abstractmethod
    def queue_size(self) -> int:
        """Return current backlog depth."""
        pass


class AsyncInMemoryQueue(TaskQueueInterface):
    """In-memory asyncio queue for unit testing and local development without Redis."""

    def __init__(self):
        self._queue: asyncio.Queue[QCJobPayload] = asyncio.Queue()

    async def enqueue(self, payload: QCJobPayload) -> str:
        await self._queue.put(payload)
        return payload.qc_run_id

    async def dequeue(self, timeout_seconds: float = 1.0) -> Optional[QCJobPayload]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return None

    def queue_size(self) -> int:
        return self._queue.qsize()


# Singleton queue instance for the application process
default_task_queue = AsyncInMemoryQueue()
