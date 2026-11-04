"""Free translation library for Python across multiple providers.

Translates totally free of charge without API keys, logins, or paid tiers.
Drop-in compatible with googletrans / googletrans-curl.
"""

__all__ = (
    "Translator",
    "SyncTranslator",
    "LANGUAGES",
    "LANGCODES",
    "TranslationError",
    "RateLimitError",
    "ProviderError",
    "CurlOpt",
    "Translated",
    "Detected",
)
__version__ = "0.1.0"

from freetrans.client import SyncTranslator, Translator
from freetrans.constants import (
    LANGCODES,
    LANGUAGES,
    ProviderError,
    RateLimitError,
    TranslationError,
)
from freetrans.models import Detected, Translated

try:
    from curl_cffi import CurlOpt
except ImportError:  # pragma: no cover
    CurlOpt = None
