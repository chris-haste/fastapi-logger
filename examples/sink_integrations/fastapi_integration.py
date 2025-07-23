from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI

from fapilog import Sink, configure_logging, register_sink


@register_sink("custom")
class CustomSink(Sink):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    async def write(self, event_dict: Dict[str, Any]) -> None:
        # Implementation
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging with custom sink
    configure_logging(app=app, sinks=["custom://localhost:8080", "stdout"])
    yield


app = FastAPI(lifespan=lifespan)
