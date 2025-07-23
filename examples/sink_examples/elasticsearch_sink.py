from typing import Any, Dict

from elasticsearch import AsyncElasticsearch

from fapilog import Sink, register_sink


@register_sink("elasticsearch")
class ElasticsearchSink(Sink):
    def __init__(self, host="localhost", port=9200, index="logs", **kwargs):
        super().__init__()
        self.host = host
        self.port = port
        self.index = index
        self.client = None

    async def start(self):
        """Initialize Elasticsearch client."""
        self.client = AsyncElasticsearch([f"{self.host}:{self.port}"])

    async def stop(self):
        """Close Elasticsearch client."""
        if self.client:
            await self.client.close()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write log event to Elasticsearch."""
        if not self.client:
            raise RuntimeError("Sink not started")

        await self.client.index(index=self.index, body=event_dict)
