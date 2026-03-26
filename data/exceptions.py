# data/exceptions.py
# Unified exception hierarchy for the UFC analytics engine.
# Provides consistent error types across all data and provider modules.


class AnalyticsError(Exception):
    """Base exception for all analytics engine errors."""
    pass


class DataSourceError(AnalyticsError):
    """Raised when an external data source (API, scraper) fails."""
    def __init__(self, provider: str, message: str, cause: Exception | None = None):
        self.provider = provider
        self.cause = cause
        super().__init__(f"[{provider}] {message}")


class ValidationError(AnalyticsError):
    """Raised when input data fails validation."""
    pass


class FighterNotFoundError(AnalyticsError):
    """Raised when a fighter cannot be resolved."""
    def __init__(self, name: str):
        self.fighter_name = name
        super().__init__(f"Fighter not found: {name!r}")


class EventNotFoundError(AnalyticsError):
    """Raised when an event cannot be resolved."""
    def __init__(self, event_id: str):
        self.event_id = event_id
        super().__init__(f"Event not found: {event_id!r}")


class PipelineTimeoutError(AnalyticsError):
    """Raised when the analysis pipeline exceeds its timeout."""
    def __init__(self, stage: str, timeout_seconds: float):
        self.stage = stage
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Pipeline stage '{stage}' timed out after {timeout_seconds}s")
