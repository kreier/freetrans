"""Main client interface for freetrans."""

import asyncio
import logging
import threading
import typing

from httpx import Timeout
from httpx._types import ProxyTypes

from freetrans.constants import (
    DEFAULT_CLIENT_SERVICE_URLS,
    DEFAULT_RAISE_EXCEPTION,
    DEFAULT_USER_AGENT,
    RateLimitError,
    TranslationError,
)
from freetrans.models import Detected, Translated
from freetrans.providers import get_provider
from freetrans.providers.google import _normalize_lang

try:
    from curl_cffi.requests import AsyncSession
    from curl_cffi.curl import CurlOpt
    CURL_AVAILABLE = True
except ImportError:  # pragma: no cover
    AsyncSession = None
    CurlOpt = None
    CURL_AVAILABLE = False

logger = logging.getLogger("freetrans")


class Translator:
    """Drop-in async translator class supporting multiple free service providers.

    :param service_urls: provider translate URL list. URLs will be used randomly.
    :param user_agent: User-Agent header string.
    :param raise_exception: whether to raise exceptions on failures.
    :param proxy: proxy URL or mapping.
    :param timeout: request timeout (seconds or httpx.Timeout).
    :param http2: whether to enable HTTP/2 (for httpx transport).
    :param list_operation_max_concurrency: maximum concurrent requests for batch translation.
    :param transport: HTTP transport to use: 'auto' (curl-cffi if installed, else httpx),
                      'curl' (requires curl-cffi), or 'httpx'.
    :param impersonate: browser TLS/JA3/HTTP2 fingerprint to impersonate with curl-cffi.
    :param proxies: legacy alias for proxy.
    :param curl_options: custom libcurl options dictionary.
    :param ipv4: if True, force IPv4 DNS resolution (avoids 30s timeouts on broken IPv6).
    :param ip_resolve: IP resolution strategy ('v4', 'v6', 'any', or int 0, 1, 2).
    :param provider: translation provider to use (default: 'google').
    """

    def __init__(
        self,
        service_urls: typing.Sequence[str] = DEFAULT_CLIENT_SERVICE_URLS,
        user_agent: str = DEFAULT_USER_AGENT,
        raise_exception: bool = DEFAULT_RAISE_EXCEPTION,
        proxy: typing.Optional[ProxyTypes] = None,
        timeout: typing.Optional[Timeout] = None,
        http2: bool = True,
        list_operation_max_concurrency: int = 2,
        transport: typing.Literal["auto", "curl", "httpx"] = "auto",
        impersonate: str = "chrome",
        proxies: typing.Optional[typing.Any] = None,
        curl_options: typing.Optional[typing.Dict[typing.Any, typing.Any]] = None,
        ipv4: bool = False,
        ip_resolve: typing.Optional[typing.Union[int, str]] = None,
        provider: str = "google",
        **kwargs: typing.Any,
    ):
        if proxies is not None and proxy is None:
            proxy = proxies

        self._provider_name = provider.lower().strip()
        provider_cls = get_provider(self._provider_name)

        provider_kwargs: typing.Dict[str, typing.Any] = {
            "service_urls": service_urls,
            "user_agent": user_agent,
            "raise_exception": raise_exception,
            "proxy": proxy,
            "timeout": timeout,
            "http2": http2,
            "list_operation_max_concurrency": list_operation_max_concurrency,
            "transport": transport,
            "impersonate": impersonate,
            "curl_options": curl_options,
            "ipv4": ipv4,
            "ip_resolve": ip_resolve,
        }
        provider_kwargs.update(kwargs)

        self._provider = provider_cls(**provider_kwargs)

    @property
    def provider(self) -> str:
        """Name of the active provider."""
        return self._provider_name

    @property
    def service_urls(self) -> typing.List[str]:
        return getattr(self._provider, "service_urls", [])

    @service_urls.setter
    def service_urls(self, value: typing.List[str]) -> None:
        if hasattr(self._provider, "service_urls"):
            self._provider.service_urls = value

    @property
    def client_type(self) -> str:
        return getattr(self._provider, "client_type", "webapp")

    @client_type.setter
    def client_type(self, value: str) -> None:
        if hasattr(self._provider, "client_type"):
            self._provider.client_type = value

    @property
    def raise_exception(self) -> bool:
        return getattr(self._provider, "raise_exception", True)

    @raise_exception.setter
    def raise_exception(self, value: bool) -> None:
        if hasattr(self._provider, "raise_exception"):
            self._provider.raise_exception = value

    @property
    def list_operation_max_concurrency(self) -> int:
        return getattr(self._provider, "list_operation_max_concurrency", 2)

    @list_operation_max_concurrency.setter
    def list_operation_max_concurrency(self, value: int) -> None:
        if hasattr(self._provider, "list_operation_max_concurrency"):
            self._provider.list_operation_max_concurrency = value

    @property
    def transport(self) -> str:
        return getattr(self._provider, "transport", "httpx")

    @property
    def impersonate(self) -> str:
        return getattr(self._provider, "impersonate", "chrome")

    @property
    def client(self) -> typing.Any:
        return getattr(self._provider, "client", None)

    @property
    def token_acquirer(self) -> typing.Any:
        return getattr(self._provider, "token_acquirer", None)

    @property
    def curl_options(self) -> typing.Dict[typing.Any, typing.Any]:
        return getattr(self._provider, "curl_options", {})

    @property
    def ipv4(self) -> bool:
        return getattr(self._provider, "ipv4", False)

    @property
    def ip_resolve(self) -> typing.Optional[typing.Union[int, str]]:
        return getattr(self._provider, "ip_resolve", None)

    async def __aenter__(self):
        return self

    async def aclose(self):
        """Close underlying provider HTTP client session."""
        if hasattr(self._provider, "aclose"):
            await self._provider.aclose()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    @typing.overload
    async def translate(
        self, text: str, dest: str = ..., src: str = ..., **kwargs: typing.Any
    ) -> Translated: ...

    @typing.overload
    async def translate(
        self,
        text: typing.List[str],
        dest: str = ...,
        src: str = ...,
        **kwargs: typing.Any,
    ) -> typing.List[Translated]: ...

    async def translate(
        self,
        text: typing.Union[str, typing.List[str]],
        dest: str = "en",
        src: str = "auto",
        **kwargs: typing.Any,
    ) -> typing.Union[Translated, typing.List[Translated]]:
        """Translate text from source language to destination language."""
        return await self._provider.translate(text, dest=dest, src=src, **kwargs)

    @typing.overload
    async def detect(self, text: str, **kwargs: typing.Any) -> Detected: ...

    @typing.overload
    async def detect(
        self, text: typing.List[str], **kwargs: typing.Any
    ) -> typing.List[Detected]: ...

    async def detect(
        self, text: typing.Union[str, typing.List[str]], **kwargs: typing.Any
    ) -> typing.Union[Detected, typing.List[Detected]]:
        """Detect language of the input text."""
        return await self._provider.detect(text, **kwargs)

    def translate_sync(
        self,
        text: typing.Union[str, typing.List[str]],
        dest: str = "en",
        src: str = "auto",
        **kwargs: typing.Any,
    ) -> typing.Union[Translated, typing.List[Translated]]:
        """Synchronously translate text without manually managing an event loop."""
        with SyncTranslator(
            service_urls=self.service_urls,
            raise_exception=self.raise_exception,
            list_operation_max_concurrency=self.list_operation_max_concurrency,
            transport=self.transport,
            impersonate=self.impersonate,
            curl_options=self.curl_options,
            ipv4=self.ipv4,
            ip_resolve=self.ip_resolve,
            provider=self.provider,
        ) as sync_trans:
            return sync_trans.translate(text, dest=dest, src=src, **kwargs)

    def detect_sync(
        self,
        text: typing.Union[str, typing.List[str]],
        **kwargs: typing.Any,
    ) -> typing.Union[Detected, typing.List[Detected]]:
        """Synchronously detect text language without manually managing an event loop."""
        with SyncTranslator(
            service_urls=self.service_urls,
            raise_exception=self.raise_exception,
            list_operation_max_concurrency=self.list_operation_max_concurrency,
            transport=self.transport,
            impersonate=self.impersonate,
            curl_options=self.curl_options,
            ipv4=self.ipv4,
            ip_resolve=self.ip_resolve,
            provider=self.provider,
        ) as sync_trans:
            return sync_trans.detect(text, **kwargs)


class SyncTranslator:
    """Synchronous drop-in translator wrapper for blocking workflows."""

    def __init__(
        self,
        service_urls: typing.Sequence[str] = DEFAULT_CLIENT_SERVICE_URLS,
        user_agent: str = DEFAULT_USER_AGENT,
        raise_exception: bool = DEFAULT_RAISE_EXCEPTION,
        proxy: typing.Optional[ProxyTypes] = None,
        timeout: typing.Optional[Timeout] = None,
        http2: bool = True,
        list_operation_max_concurrency: int = 2,
        transport: typing.Literal["auto", "curl", "httpx"] = "auto",
        impersonate: str = "chrome",
        proxies: typing.Optional[typing.Any] = None,
        curl_options: typing.Optional[typing.Dict[typing.Any, typing.Any]] = None,
        ipv4: bool = False,
        ip_resolve: typing.Optional[typing.Union[int, str]] = None,
        provider: str = "google",
        **kwargs: typing.Any,
    ):
        if proxies is not None and proxy is None:
            proxy = proxies

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

        async def _init_client():
            return Translator(
                service_urls=service_urls,
                user_agent=user_agent,
                raise_exception=raise_exception,
                proxy=proxy,
                timeout=timeout,
                http2=http2,
                transport=transport,
                impersonate=impersonate,
                list_operation_max_concurrency=list_operation_max_concurrency,
                curl_options=curl_options,
                ipv4=ipv4,
                ip_resolve=ip_resolve,
                provider=provider,
                **kwargs,
            )

        future = asyncio.run_coroutine_threadsafe(_init_client(), self._loop)
        self._async_translator = future.result()

    @property
    def provider(self) -> str:
        return self._async_translator.provider

    @property
    def service_urls(self) -> typing.List[str]:
        return self._async_translator.service_urls

    @property
    def client_type(self) -> str:
        return self._async_translator.client_type

    @property
    def raise_exception(self) -> bool:
        return self._async_translator.raise_exception

    @property
    def transport(self) -> str:
        return self._async_translator.transport

    @property
    def impersonate(self) -> str:
        return self._async_translator.impersonate

    @property
    def client(self) -> typing.Any:
        return self._async_translator.client

    @property
    def curl_options(self) -> typing.Dict[typing.Any, typing.Any]:
        return self._async_translator.curl_options

    @property
    def ipv4(self) -> bool:
        return self._async_translator.ipv4

    @property
    def ip_resolve(self) -> typing.Optional[typing.Union[int, str]]:
        return self._async_translator.ip_resolve

    def _run_coroutine(self, coro: typing.Coroutine) -> typing.Any:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def translate(
        self,
        text: typing.Union[str, typing.List[str]],
        dest: str = "en",
        src: str = "auto",
        **kwargs: typing.Any,
    ) -> typing.Union[Translated, typing.List[Translated]]:
        """Synchronously translate text from source language to destination language."""
        return self._run_coroutine(
            self._async_translator.translate(text, dest=dest, src=src, **kwargs)
        )

    def detect(
        self,
        text: typing.Union[str, typing.List[str]],
        **kwargs: typing.Any,
    ) -> typing.Union[Detected, typing.List[Detected]]:
        """Synchronously detect language of the input text."""
        return self._run_coroutine(
            self._async_translator.detect(text, **kwargs)
        )

    def close(self):
        """Close the underlying client session and persistent event loop."""
        if hasattr(self, "_loop") and self._loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._async_translator.aclose(), self._loop
                )
                future.result(timeout=2.0)
            except Exception:
                pass
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
                if hasattr(self, "_thread") and self._thread.is_alive():
                    self._thread.join(timeout=2.0)
                try:
                    self._loop.close()
                except Exception:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
