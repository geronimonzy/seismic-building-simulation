"""
Exceptions for seismic data fetching.
"""


class SeismoHubError(Exception):
    """Base exception for seismic data operations."""

    pass


class DataNotFoundError(SeismoHubError):
    """Raised when requested seismic data is not found."""

    pass


class NetworkError(SeismoHubError):
    """Raised when a network request fails."""

    pass


class CacheError(SeismoHubError):
    """Raised when cache operations fail."""

    pass
