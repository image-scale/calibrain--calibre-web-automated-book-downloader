"""Tests for the download queue module."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from bookdl.core.models import DownloadTask, QueueStatus
from bookdl.core.queue import BookQueue, get_queue


class TestBookQueue:
    """Tests for BookQueue class."""

    def test_add_returns_true_for_new_task(self):
        """add() returns True for new task."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")

        result = queue.add(task)

        assert result is True

    def test_add_returns_false_for_existing_task(self):
        """add() returns False if task_id already exists."""
        queue = BookQueue()
        task1 = DownloadTask(task_id="task1", source="test", title="Book 1")
        task2 = DownloadTask(task_id="task1", source="test", title="Book 1 duplicate")

        queue.add(task1)
        result = queue.add(task2)

        assert result is False

    def test_get_next_returns_task_id_and_cancelled_flag(self):
        """get_next() returns (task_id, is_cancelled) tuple."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)

        task_id, is_cancelled = queue.get_next()

        assert task_id == "task1"
        assert is_cancelled is False

    def test_get_next_returns_none_when_empty(self):
        """get_next() returns (None, False) when queue is empty."""
        queue = BookQueue()

        task_id, is_cancelled = queue.get_next()

        assert task_id is None
        assert is_cancelled is False

    def test_priority_ordering(self):
        """Queue respects priority ordering (lower number first)."""
        queue = BookQueue()
        task_low = DownloadTask(task_id="low", source="test", title="Low", priority=10)
        task_high = DownloadTask(task_id="high", source="test", title="High", priority=1)

        queue.add(task_low)
        queue.add(task_high)

        # High priority (lower number) should be returned first
        task_id, _ = queue.get_next()
        assert task_id == "high"

    def test_same_priority_uses_added_time(self):
        """Same priority tasks use added_time for ordering (FIFO)."""
        queue = BookQueue()
        task1 = DownloadTask(task_id="first", source="test", title="First", priority=5, added_time=100.0)
        task2 = DownloadTask(task_id="second", source="test", title="Second", priority=5, added_time=200.0)

        queue.add(task1)
        queue.add(task2)

        task_id, _ = queue.get_next()
        assert task_id == "first"

    def test_update_status_changes_task_status(self):
        """update_status() changes task status."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)

        result = queue.update_status("task1", QueueStatus.DOWNLOADING)

        assert result is True
        assert queue.get_status("task1") == QueueStatus.DOWNLOADING

    def test_update_status_returns_false_for_missing_task(self):
        """update_status() returns False for non-existent task."""
        queue = BookQueue()

        result = queue.update_status("nonexistent", QueueStatus.DOWNLOADING)

        assert result is False

    def test_update_status_sets_message_and_progress(self):
        """update_status() can set message and progress."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)

        queue.update_status("task1", QueueStatus.DOWNLOADING, message="50%", progress=0.5)

        updated_task = queue.get_task("task1")
        assert updated_task.status_message == "50%"
        assert updated_task.progress == 0.5

    def test_cancel_sets_cancellation_flag(self):
        """cancel() sets cancellation flag for task."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)

        result = queue.cancel("task1")

        assert result is True
        assert queue.is_cancelled("task1") is True
        assert queue.get_status("task1") == QueueStatus.CANCELLED

    def test_cancel_returns_false_for_missing_task(self):
        """cancel() returns False for non-existent task."""
        queue = BookQueue()

        result = queue.cancel("nonexistent")

        assert result is False

    def test_get_next_shows_cancelled_flag(self):
        """get_next() shows is_cancelled=True for cancelled tasks."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1", status=QueueStatus.QUEUED)
        queue.add(task)

        # Mark cancelled but change status back to queued to trigger get_next
        queue._cancelled.add("task1")

        task_id, is_cancelled = queue.get_next()
        # The task is actually cancelled so it returns with cancelled flag
        assert is_cancelled is True

    def test_get_status_returns_current_status(self):
        """get_status() returns current status of task."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)

        status = queue.get_status("task1")

        assert status == QueueStatus.QUEUED

    def test_get_status_returns_none_for_missing_task(self):
        """get_status() returns None for non-existent task."""
        queue = BookQueue()

        status = queue.get_status("nonexistent")

        assert status is None

    def test_get_task_returns_task_data(self):
        """get_task() returns task data by id."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="My Book", author="Author")
        queue.add(task)

        result = queue.get_task("task1")

        assert result is not None
        assert result.title == "My Book"
        assert result.author == "Author"

    def test_get_task_returns_none_for_missing_task(self):
        """get_task() returns None for non-existent task."""
        queue = BookQueue()

        result = queue.get_task("nonexistent")

        assert result is None

    def test_get_all_statuses_returns_dict(self):
        """get_all_statuses() returns dict of all task statuses."""
        queue = BookQueue()
        task1 = DownloadTask(task_id="task1", source="test", title="Book 1")
        task2 = DownloadTask(task_id="task2", source="test", title="Book 2")
        queue.add(task1)
        queue.add(task2)
        queue.update_status("task2", QueueStatus.DOWNLOADING)

        statuses = queue.get_all_statuses()

        assert statuses == {
            "task1": QueueStatus.QUEUED,
            "task2": QueueStatus.DOWNLOADING,
        }

    def test_terminal_statuses_skipped_by_get_next(self):
        """get_next() skips tasks in terminal status."""
        queue = BookQueue()
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)
        queue.update_status("task1", QueueStatus.COMPLETE)

        task_id, _ = queue.get_next()

        assert task_id is None

    def test_cleanup_stale_removes_old_terminal_tasks(self):
        """cleanup_stale() removes old tasks in terminal status."""
        queue = BookQueue(stale_timeout=0)  # Immediate expiration
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)
        queue.update_status("task1", QueueStatus.COMPLETE)
        time.sleep(0.01)

        removed = queue.cleanup_stale()

        assert removed == 1
        assert queue.get_task("task1") is None

    def test_cleanup_stale_keeps_active_tasks(self):
        """cleanup_stale() keeps active tasks."""
        queue = BookQueue(stale_timeout=0)
        task = DownloadTask(task_id="task1", source="test", title="Book 1")
        queue.add(task)
        # Keep in QUEUED (active) status
        time.sleep(0.01)

        removed = queue.cleanup_stale()

        assert removed == 0
        assert queue.get_task("task1") is not None

    def test_size_returns_task_count(self):
        """size() returns number of tasks."""
        queue = BookQueue()
        assert queue.size() == 0

        queue.add(DownloadTask(task_id="task1", source="test", title="Book 1"))
        assert queue.size() == 1

        queue.add(DownloadTask(task_id="task2", source="test", title="Book 2"))
        assert queue.size() == 2

    def test_active_count_returns_active_tasks(self):
        """active_count() returns number of active tasks."""
        queue = BookQueue()
        queue.add(DownloadTask(task_id="task1", source="test", title="Book 1"))
        queue.add(DownloadTask(task_id="task2", source="test", title="Book 2"))
        queue.update_status("task1", QueueStatus.COMPLETE)

        assert queue.active_count() == 1

    def test_clear_removes_all_tasks(self):
        """clear() removes all tasks."""
        queue = BookQueue()
        queue.add(DownloadTask(task_id="task1", source="test", title="Book 1"))
        queue.add(DownloadTask(task_id="task2", source="test", title="Book 2"))

        queue.clear()

        assert queue.size() == 0
        assert queue.get_all_statuses() == {}

    def test_thread_safety_concurrent_operations(self):
        """Concurrent operations don't corrupt state."""
        queue = BookQueue()
        errors = []

        def add_tasks(start_idx):
            try:
                for i in range(20):
                    task = DownloadTask(
                        task_id=f"task_{start_idx}_{i}",
                        source="test",
                        title=f"Book {start_idx}_{i}",
                    )
                    queue.add(task)
            except Exception as e:
                errors.append(e)

        def update_statuses():
            try:
                for _ in range(50):
                    statuses = queue.get_all_statuses()
                    for task_id in statuses:
                        queue.update_status(task_id, QueueStatus.DOWNLOADING)
            except Exception as e:
                errors.append(e)

        def pop_tasks():
            try:
                for _ in range(20):
                    queue.get_next()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(3):
                futures.append(executor.submit(add_tasks, i))
            for _ in range(3):
                futures.append(executor.submit(update_statuses))
                futures.append(executor.submit(pop_tasks))

            for future in futures:
                future.result()

        assert len(errors) == 0


class TestGetQueue:
    """Tests for get_queue() function."""

    def test_returns_book_queue_instance(self):
        """get_queue() returns a BookQueue instance."""
        queue = get_queue()
        assert isinstance(queue, BookQueue)

    def test_returns_same_instance(self):
        """get_queue() returns the same instance on subsequent calls."""
        queue1 = get_queue()
        queue2 = get_queue()
        assert queue1 is queue2
