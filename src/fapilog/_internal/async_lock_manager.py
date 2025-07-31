"""Centralized async lock management for processors.

This module provides thread-safe async lock management to eliminate race
conditions in processor operations. It addresses the mixed
threading.Lock/asyncio.Lock patterns identified in the current codebase.
"""

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from typing import Dict

logger = logging.getLogger(__name__)


class ProcessorLockManager:
    """Centralized async lock management for processors.

    Provides consistent async lock patterns to replace dangerous lock-free
    optimizations and mixed sync/async patterns in processors.
    """

    def __init__(self):
        """Initialize lock manager with thread-safe lock creation."""
        self._async_locks: Dict[str, asyncio.Lock] = {}
        self._sync_locks: Dict[str, threading.Lock] = {}
        self._lock_creation_lock = threading.Lock()
        self._async_lock_creation_lock = asyncio.Lock()

    @asynccontextmanager
    async def get_async_lock(self, lock_name: str):
        """Get or create async lock for specific operation.

        Args:
            lock_name: Unique identifier for the lock

        Yields:
            asyncio.Lock: The async lock for the operation
        """
        if lock_name not in self._async_locks:
            async with self._async_lock_creation_lock:
                if lock_name not in self._async_locks:
                    self._async_locks[lock_name] = asyncio.Lock()
                    logger.debug(f"Created async lock: {lock_name}")

        lock = self._async_locks[lock_name]
        async with lock:
            logger.debug(f"Acquired async lock: {lock_name}")
            try:
                yield lock
            finally:
                logger.debug(f"Released async lock: {lock_name}")

    def get_sync_lock(self, lock_name: str) -> threading.Lock:
        """Get or create sync lock for specific operation.

        Args:
            lock_name: Unique identifier for the lock

        Returns:
            threading.Lock: The sync lock for the operation
        """
        with self._lock_creation_lock:
            if lock_name not in self._sync_locks:
                self._sync_locks[lock_name] = threading.Lock()
                logger.debug(f"Created sync lock: {lock_name}")
            return self._sync_locks[lock_name]

    async def cleanup_unused_locks(self) -> int:
        """Clean up unused async locks to prevent memory leaks.

        Returns:
            int: Number of locks cleaned up
        """
        cleaned_count = 0
        async with self._async_lock_creation_lock:
            # Remove locks that are not currently held
            locks_to_remove = []
            for lock_name, lock in list(self._async_locks.items()):
                if not lock.locked():
                    locks_to_remove.append(lock_name)

            for lock_name in locks_to_remove:
                del self._async_locks[lock_name]
                cleaned_count += 1
                logger.debug(f"Cleaned up unused async lock: {lock_name}")

        return cleaned_count

    def get_lock_stats(self) -> Dict[str, int]:
        """Get lock manager statistics.

        Returns:
            Dict with async and sync lock counts
        """
        return {
            "async_locks": len(self._async_locks),
            "sync_locks": len(self._sync_locks),
            "active_async_locks": sum(
                1 for lock in self._async_locks.values() if lock.locked()
            ),
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup_unused_locks()
