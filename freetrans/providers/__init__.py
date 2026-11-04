"""Providers package for freetrans."""

import typing
from freetrans.constants import ProviderError
from freetrans.providers.base import BaseProvider
from freetrans.providers.google import GoogleProvider

PROVIDERS: typing.Dict[str, typing.Type[BaseProvider]] = {
    "google": GoogleProvider,
}


def get_provider(name: str) -> typing.Type[BaseProvider]:
    """Retrieve provider class by name."""
    clean_name = name.lower().strip()
    if clean_name not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS.keys()))
        raise ProviderError(
            f"Unsupported provider: '{name}'. Available providers: {available}"
        )
    return PROVIDERS[clean_name]


def register_provider(name: str, provider_cls: typing.Type[BaseProvider]) -> None:
    """Register a custom or third-party provider."""
    PROVIDERS[name.lower().strip()] = provider_cls


__all__ = ["BaseProvider", "GoogleProvider", "PROVIDERS", "get_provider", "register_provider"]
