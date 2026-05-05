"""Thread-safe download queue with priority support and status tracking.

Provides BookQueue class for managing download tasks in a priority queue
with cancellation flags and stale task cleanup.
"""

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bookdl.core.models import (
    ACTIVE_QUEUE_STATUSES,
    TERMINAL_QUEUE_STATUSES,
    DownloadTask,
    QueueStatus,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(order=True)
class PriorityTask:
    """Wrapper for tasks in priority queue."""

    priority: int
    added_time: float
    task_id: str = field(compare=False)


class BookQueue:
    """Thread-safe download queue with priority support.

    Manages download tasks with priority ordering, status tracking,
    cancellation support, and stale task cleanup.
    """

    def __init__(self, stale_timeout: int = 3600) -> None:
        """Initialize the book queue.

        Args:
            stale_timeout: Seconds after which completed tasks are removed
        """
        self._lock = threading.Lock()
        self._heap: list[PriorityTask] = []
        self._tasks: dict[str, DownloadTask] = {}
        self._cancelled: set[str] = set()
        self._status_timestamps: dict[str, float] = {}
        self._stale_timeout = stale_timeout

    def add(self, task: DownloadTask) -> bool:
        """Add a download task to the queue.

        Args:
            task: DownloadTask to add

        Returns:
            True if added, False if task_id already exists
        """
        with self._lock:
            if task.task_id in self._tasks:
                return False

            self._tasks[task.task_id] = task
            self._status_timestamps[task.task_id] = time.time()

            # Add to priority heap
            priority_task = PriorityTask(
                priority=task.priority,
                added_time=task.added_time,
                task_id=task.task_id,
            )
            heapq.heappush(self._heap, priority_task)

            return True

    def get_next(self) -> tuple[str | None, bool]:
        """Get the next task to process from the queue.

        Returns:
            Tuple of (task_id, is_cancelled). Returns (None, False) if queue is empty.
        """
        with self._lock:
            while self._heap:
                priority_task = heapq.heappop(self._heap)
                task_id = priority_task.task_id

                # Skip if task no longer exists
                if task_id not in self._tasks:
                    continue

                task = self._tasks[task_id]

                # Skip if task is already in terminal state
                if task.status in TERMINAL_QUEUE_STATUSES:
                    continue

                # Check if cancelled
                is_cancelled = task_id in self._cancelled
                return (task_id, is_cancelled)

            return (None, False)

    def update_status(
        self,
        task_id: str,
        status: QueueStatus,
        message: str | None = None,
        progress: float | None = None,
    ) -> bool:
        """Update the status of a task.

        Args:
            task_id: Task ID to update
            status: New status
            message: Optional status message
            progress: Optional progress (0.0 to 1.0)

        Returns:
            True if updated, False if task not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            task.status = status
            if message is not None:
                task.status_message = message
            if progress is not None:
                task.progress = progress
            self._status_timestamps[task_id] = time.time()

            return True

    def cancel(self, task_id: str) -> bool:
        """Mark a task for cancellation.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancellation flag set, False if task not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return False

            self._cancelled.add(task_id)
            task = self._tasks[task_id]
            task.status = QueueStatus.CANCELLED
            self._status_timestamps[task_id] = time.time()

            return True

    def get_status(self, task_id: str) -> QueueStatus | None:
        """Get the current status of a task.

        Args:
            task_id: Task ID

        Returns:
            Current status, or None if task not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            return task.status if task else None

    def get_task(self, task_id: str) -> DownloadTask | None:
        """Get task data by ID.

        Args:
            task_id: Task ID

        Returns:
            DownloadTask, or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_statuses(self) -> dict[str, QueueStatus]:
        """Get status of all tasks in the queue.

        Returns:
            Dictionary mapping task_id to status
        """
        with self._lock:
            return {task_id: task.status for task_id, task in self._tasks.items()}

    def get_all_tasks(self) -> list[DownloadTask]:
        """Get all tasks in the queue.

        Returns:
            List of all DownloadTask objects
        """
        with self._lock:
            return list(self._tasks.values())

    def cleanup_stale(self) -> int:
        """Remove tasks in terminal state that have exceeded the stale timeout.

        Returns:
            Number of tasks removed
        """
        with self._lock:
            now = time.time()
            stale_ids = []

            for task_id, task in self._tasks.items():
                if task.status in TERMINAL_QUEUE_STATUSES:
                    last_update = self._status_timestamps.get(task_id, 0)
                    if now - last_update > self._stale_timeout:
                        stale_ids.append(task_id)

            for task_id in stale_ids:
                del self._tasks[task_id]
                self._cancelled.discard(task_id)
                if task_id in self._status_timestamps:
                    del self._status_timestamps[task_id]

            return len(stale_ids)

    def is_cancelled(self, task_id: str) -> bool:
        """Check if a task is marked for cancellation.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False otherwise
        """
        with self._lock:
            return task_id in self._cancelled

    def size(self) -> int:
        """Get the number of tasks in the queue.

        Returns:
            Number of tasks
        """
        with self._lock:
            return len(self._tasks)

    def active_count(self) -> int:
        """Get the number of active (non-terminal) tasks.

        Returns:
            Number of active tasks
        """
        with self._lock:
            return sum(
                1 for task in self._tasks.values() if task.status in ACTIVE_QUEUE_STATUSES
            )

    def clear(self) -> None:
        """Remove all tasks from the queue."""
        with self._lock:
            self._heap.clear()
            self._tasks.clear()
            self._cancelled.clear()
            self._status_timestamps.clear()


# Global queue instance
_global_queue: BookQueue | None = None
_queue_lock = threading.Lock()


def get_queue() -> BookQueue:
    """Get the global queue instance (lazy initialization).

    Returns:
        Global BookQueue instance
    """
    global _global_queue
    if _global_queue is None:
        with _queue_lock:
            if _global_queue is None:
                _global_queue = BookQueue()
    return _global_queue
