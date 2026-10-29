"""Application-specific exceptions with safe user-facing messages."""


class LLMSECError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(LLMSECError):
    """A configuration file is missing, malformed, or invalid."""


class ProviderError(LLMSECError):
    """A model provider request failed."""


class ModelNotFoundError(ProviderError):
    """The requested local model is not installed."""


class ReportError(LLMSECError):
    """A report could not be read or written."""
