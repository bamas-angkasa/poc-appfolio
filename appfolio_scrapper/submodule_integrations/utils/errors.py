from typing import Optional


class IntegrationError(Exception):
    """Base exception carrying structured integration error details."""

    def __init__(
        self,
        integration_name: Optional[str] = None,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ):
        self.integration_name = integration_name
        self.message = message or self.__class__.__name__
        self.status_code = status_code
        self.error_code = error_code

        prefix = f"{integration_name}: " if integration_name else ""
        super().__init__(f"{prefix}{self.message}")


class IntegrationAPIError(IntegrationError):
    """Raised when an integration's remote API request fails."""


class IntegrationAuthError(IntegrationError):
    """Raised when integration credentials are absent or rejected."""

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        integration_name: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(integration_name, message, status_code, error_code)
