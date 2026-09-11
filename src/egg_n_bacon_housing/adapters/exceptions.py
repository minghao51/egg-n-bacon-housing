"""Adapter-level typed exceptions for external data fetches and auth."""


class AdapterError(Exception):
    """Base exception for adapter failures."""


class CredentialError(AdapterError):
    """Raised when required credentials are missing or invalid."""


class OneMapAuthError(AdapterError):
    """Raised when OneMap authentication fails."""


class URAAuthError(AdapterError):
    """Raised when URA Data Service authentication fails (bad key/token)."""


class DatasetFetchError(AdapterError):
    """Raised when a dataset fetch fails."""


class IncompleteDatasetFetchError(DatasetFetchError):
    """Raised when paginated dataset fetch is incomplete."""
