"""Adapter-level typed exceptions for external data fetches and auth."""


class AdapterError(Exception):
    """Base exception for adapter failures."""


class CredentialError(AdapterError):
    """Raised when required credentials are missing or invalid."""


class OneMapAuthError(AdapterError):
    """Raised when OneMap authentication fails."""


class DatasetFetchError(AdapterError):
    """Raised when a dataset fetch fails."""


class IncompleteDatasetFetchError(DatasetFetchError):
    """Raised when paginated dataset fetch is incomplete."""
