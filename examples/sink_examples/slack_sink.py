import logging
from typing import Any, Dict

import aiohttp

from fapilog import Sink, register_sink

logger = logging.getLogger(__name__)


@register_sink("slack")
class SlackSink(Sink):
    def __init__(self, webhook_url, channel="#alerts", level_filter="error", **kwargs):
        super().__init__()

        # Validate required parameters
        if not webhook_url:
            raise ValueError("webhook_url parameter is required")

        self.webhook_url = webhook_url
        self.channel = channel
        self.level_filter = level_filter
        self.session = None

    async def start(self):
        """Initialize HTTP session."""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
            logger.info("Slack sink HTTP session initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Slack HTTP session: {e}")
            raise

    async def stop(self):
        """Close HTTP session."""
        if self.session:
            try:
                await self.session.close()
                logger.info("Slack sink HTTP session closed")
            except Exception as e:
                logger.error(f"Error closing Slack HTTP session: {e}")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Send filtered logs to Slack."""
        # Filter by log level
        if event_dict.get("level") != self.level_filter:
            return

        if not self.session:
            raise RuntimeError("Sink not started")

        try:
            # Build enriched message
            event_text = event_dict.get("event", "Unknown error")
            level_emoji = "🚨" if event_dict.get("level") == "error" else "⚠️"

            message = {
                "channel": self.channel,
                "text": f"{level_emoji} {event_text}",
                "attachments": [
                    {
                        "color": (
                            "danger"
                            if event_dict.get("level") == "error"
                            else "warning"
                        ),
                        "fields": [
                            {
                                "title": "Trace ID",
                                "value": event_dict.get("trace_id", "N/A"),
                                "short": True,
                            },
                            {
                                "title": "User ID",
                                "value": event_dict.get("user_id", "N/A"),
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": str(event_dict.get("timestamp", "N/A")),
                                "short": True,
                            },
                            {
                                "title": "Level",
                                "value": event_dict.get("level", "N/A").upper(),
                                "short": True,
                            },
                        ],
                    }
                ],
            }

            async with self.session.post(self.webhook_url, json=message) as response:
                if response.status >= 400:
                    logger.warning(f"Slack API returned status {response.status}")

        except Exception as e:
            # Follow best practices: log error but don't re-raise
            logger.error(
                f"Slack sink failed to send message: {e}",
                extra={"sink_error": True, "original_event": event_dict},
            )
