"""SDK layer — exposes the Hw4Sdk facade (NFR-1)."""

from hw4.sdk.sdk import Hw4Sdk, ServiceNotReadyError

__all__ = ["Hw4Sdk", "ServiceNotReadyError"]
