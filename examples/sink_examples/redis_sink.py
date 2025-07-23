from typing import Any, Dict

import aioredis

from fapilog import Sink, register_sink


@register_sink("redis")
class RedisSink(Sink):
    def __init__(self, host="localhost", port=6379, channel="logs", **kwargs):
        super().__init__()
        self.host = host
        self.port = port
        self.channel = channel
        self.redis = None

    async def start(self):
        """Initialize Redis connection."""
        self.redis = await aioredis.create_redis_pool((self.host, self.port))

    async def stop(self):
        """Close Redis connection."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Publish log event to Redis channel."""
        if not self.redis:
            raise RuntimeError("Sink not started")
        await self.redis.publish_json(self.channel, event_dict)
