"""SDK-level errors (split from sdk.py so operations can import them)."""


class ServiceNotReadyError(NotImplementedError):
    """The requested capability's service module has not landed yet."""
