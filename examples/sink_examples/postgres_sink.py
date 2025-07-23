import logging
from typing import Any, Dict

import asyncpg

from fapilog import Sink, register_sink

logger = logging.getLogger(__name__)


@register_sink("postgres")
class PostgresSink(Sink):
    def __init__(
        self,
        host="localhost",
        port=5432,
        database="logs",
        user=None,
        password=None,
        **kwargs,
    ):
        super().__init__()

        # Validate required parameters
        if not database:
            raise ValueError("database parameter is required")
        if not user:
            raise ValueError("user parameter is required")
        if not password:
            raise ValueError("password parameter is required")

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool = None

    async def start(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=1,
                max_size=10,
                command_timeout=10,
            )
            logger.info("PostgreSQL sink connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise

    async def stop(self):
        """Close database connection pool."""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("PostgreSQL sink connection pool closed")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection pool: {e}")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write log event to PostgreSQL."""
        if not self.pool:
            raise RuntimeError("Sink not started")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO logs (timestamp, level, event, data)
                    VALUES ($1, $2, $3, $4)
                """,
                    event_dict.get("timestamp"),
                    event_dict.get("level"),
                    event_dict.get("event"),
                    event_dict,
                )
        except Exception as e:
            # Follow best practices: log error but don't re-raise
            logger.error(
                f"PostgreSQL sink failed to write event: {e}",
                extra={"sink_error": True, "original_event": event_dict},
            )
