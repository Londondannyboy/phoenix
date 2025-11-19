"""
Temporal Client Manager

Singleton pattern for managing Temporal client connection.
"""

import os
from typing import Optional
from temporalio.client import Client


class TemporalClientManager:
    """Manages Temporal client connection as singleton."""

    _client: Optional[Client] = None

    @classmethod
    async def get_client(cls) -> Client:
        """
        Get or create Temporal client.

        Returns:
            Connected Temporal client
        """
        if cls._client is None:
            address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
            namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
            api_key = os.getenv("TEMPORAL_API_KEY")

            if api_key:
                # Temporal Cloud with TLS
                cls._client = await Client.connect(
                    address,
                    namespace=namespace,
                    api_key=api_key,
                    tls=True,
                )
            else:
                # Local Temporal (development)
                cls._client = await Client.connect(
                    address,
                    namespace=namespace,
                )

            print(f"Connected to Temporal: {address}")

        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close Temporal client connection."""
        if cls._client is not None:
            # Temporal Python SDK doesn't require explicit close
            cls._client = None
            print("Temporal client closed")
