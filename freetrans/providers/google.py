"""Google Translate provider for freetrans."""

import asyncio
import logging
import random
import re
import typing

import httpx
from httpx import ConnectTimeout, Response, Timeout
from httpx._types import ProxyTypes

from freetrans import urls, utils
from freetrans.constants import (
    DEFAULT_CLIENT_SERVICE_URLS,
    DEFAULT_RAISE_EXCEPTION,
    DEFAULT_USER_AGENT,
    DUMMY_DATA,
    LANGCODES,
    LANGUAGES,
    SPECIAL_CASES,
    RateLimitError,
    TranslationError,
)
from freetrans.gtoken import TokenAcquirer
from freetrans.models import Detected, Translated
from freetrans.providers.base import BaseProvider

logger = logging.getLogger("freetrans.google")

EXCLUDES = ("en", "ca", "fr")


def _normalize_lang(code: str) -> str:
    """Normalize language code, preserving script/regional variants like zh-cn or zh-tw."""
    code = code.lower().strip()
    if "@" in code:
        code = code.split("@", 1)[0]
    if code in LANGUAGES:
        return code
    # Try replacing underscores with hyphens (e.g. zh_cn -> zh-cn)
    hyphenated = code.replace("_", "-")
    if hyphenated in LANGUAGES:
        return hyphenated
    # Fallback to base language code (e.g. en_us -> en, it_ch -> it)
    base = re.split(r"[-_]", code)[0]
    if base in LANGUAGES:
        return base
    return code


try:
    from curl_cffi.requests import AsyncSession
    from curl_cffi.requests.exceptions import RequestException as CurlRequestException
    from curl_cffi.requests.exceptions import Timeout as CurlTimeout
    from curl_cffi.curl import CurlError, CurlOpt
    CURL_AVAILABLE = True
except ImportError:  # pragma: no cover
    CURL_AVAILABLE = False
    CurlRequestException = Exception
    CurlTimeout = Exception
    CurlError = Exception
    CurlOpt = None


class GoogleProvider(BaseProvider):
    """Google Translate AJAX API provider implementation."""

    name = "google"

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
    ):
        if proxies is not None and proxy is None:
            proxy = proxies

        if transport not in ("auto", "curl", "httpx"):
            raise ValueError(
                f"Invalid transport: '{transport}'. Must be one of 'auto', 'curl', 'httpx'."
            )

        if transport == "curl":
            if not CURL_AVAILABLE:
                raise ImportError(
                    "curl_cffi is required when transport='curl'. "
                    "Install it via `pip install curl_cffi`."
                )
            use_curl = True
        elif transport == "httpx":
            use_curl = False
        else:  # transport == "auto"
            use_curl = CURL_AVAILABLE

        self.transport = "curl" if use_curl else "httpx"
        self.impersonate = impersonate
        self.ipv4 = ipv4
        self.ip_resolve = ip_resolve

        resolved_curl_options: typing.Dict[typing.Any, typing.Any] = {}
        if curl_options:
            resolved_curl_options.update(curl_options)

        ip_resolve_val: typing.Optional[int] = None
        if ip_resolve is not None:
            if isinstance(ip_resolve, str):
                ip_clean = ip_resolve.lower().strip()
                if ip_clean in ("v4", "ipv4", "4"):
                    ip_resolve_val = 1
                elif ip_clean in ("v6", "ipv6", "6"):
                    ip_resolve_val = 2
                elif ip_clean in ("any", "whatever", "0", "all"):
                    ip_resolve_val = 0
                else:
                    raise ValueError(
                        f"Invalid ip_resolve value: '{ip_resolve}'. Expected 'v4', 'v6', 'any', 0, 1, or 2."
                    )
            elif isinstance(ip_resolve, int):
                if ip_resolve in (0, 1, 2):
                    ip_resolve_val = ip_resolve
                else:
                    raise ValueError(
                        f"Invalid ip_resolve value: {ip_resolve}. Expected 0, 1, or 2."
                    )
            else:
                raise ValueError(
                    f"Invalid ip_resolve type: {type(ip_resolve)}. Expected str or int."
                )
        elif ipv4:
            ip_resolve_val = 1

        if ip_resolve_val is not None:
            opt_key = CurlOpt.IPRESOLVE if CurlOpt is not None else 113
            resolved_curl_options[opt_key] = ip_resolve_val

        self._curl_options = resolved_curl_options

        if use_curl:
            timeout_sec = None
            if timeout is not None:
                if isinstance(timeout, httpx.Timeout):
                    timeout_sec = timeout.connect or timeout.read
                else:
                    timeout_sec = float(timeout)
                if timeout_sec is not None and 0 < timeout_sec < 0.001:
                    timeout_sec = 0.001

            session_kwargs: typing.Dict[str, typing.Any] = {
                "impersonate": impersonate,
                "headers": {
                    "User-Agent": user_agent,
                },
                "curl_options": resolved_curl_options,
            }
            if timeout_sec is not None:
                session_kwargs["timeout"] = timeout_sec
            if isinstance(proxy, str):
                session_kwargs["proxy"] = proxy
            elif isinstance(proxy, dict):
                session_kwargs["proxies"] = proxy

            self.client = AsyncSession(**session_kwargs)
            self.client.aclose = self.client.close
        else:
            if resolved_curl_options:
                logger.warning(
                    "curl_options and ipv4/ip_resolve are only applicable when transport='curl'."
                )
            self.client = httpx.AsyncClient(
                http2=http2,
                proxy=proxy,
                headers={
                    "User-Agent": user_agent,
                },
            )
            if timeout is not None:
                self.client.timeout = timeout

        self.service_urls = ["translate.google.com"]
        self.client_type = "webapp"
        self.token_acquirer = TokenAcquirer(
            client=self.client, host=self.service_urls[0]
        )

        if service_urls:
            self.service_urls = list(service_urls)
            self.client_type = "webapp"
            self.token_acquirer = TokenAcquirer(
                client=self.client, host=self.service_urls[0]
            )

            for _t in enumerate(service_urls):
                api_type = re.search("googleapis", service_urls[0])
                if api_type:
                    self.service_urls = ["translate.googleapis.com"]
                    self.client_type = "gtx"
                    break

        self.raise_exception = raise_exception
        self.list_operation_max_concurrency = list_operation_max_concurrency

    @property
    def curl_options(self) -> typing.Dict[typing.Any, typing.Any]:
        """Access the underlying curl options dictionary."""
        if hasattr(self.client, "curl_options"):
            return self.client.curl_options
        return getattr(self, "_curl_options", {})

    def _pick_service_url(self) -> str:
        if len(self.service_urls) == 1:
            return self.service_urls[0]
        return random.choice(self.service_urls)

    async def aclose(self):
        """Close underlying HTTP client session."""
        if hasattr(self.client, "aclose"):
            await self.client.aclose()
        elif hasattr(self.client, "close"):
            await self.client.close()

    async def _translate(
        self, text: str, dest: str, src: str, override: typing.Dict[str, typing.Any]
    ) -> typing.Tuple[typing.List[typing.Any], typing.Any]:
        token = "xxxx"  # dummy default value here as it is not used by api client
        if self.client_type == "webapp":
            try:
                token = await self.token_acquirer.do(text)
            except (CurlTimeout, httpx.TimeoutException) as exc:
                if self.raise_exception:
                    raise ConnectTimeout(str(exc)) from exc
                logger.warning("Token acquisition timed out: %s. Using fallback token.", exc)
            except CurlError as exc:
                msg = str(exc).lower()
                if getattr(exc, "code", None) == 28 or "timed out" in msg or "timeout" in msg:
                    if self.raise_exception:
                        raise ConnectTimeout(str(exc)) from exc
                    logger.warning("Token acquisition timed out: %s. Using fallback token.", exc)
                elif self.raise_exception:
                    raise TranslationError(
                        f"HTTP transport error during token acquisition: {exc}"
                    ) from exc
                else:
                    logger.warning("Token acquisition failed: %s. Using fallback token.", exc)
            except CurlRequestException as exc:
                if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
                    if self.raise_exception:
                        raise ConnectTimeout(str(exc)) from exc
                    logger.warning("Token acquisition timed out: %s. Using fallback token.", exc)
                elif self.raise_exception:
                    raise TranslationError(
                        f"HTTP transport error during token acquisition: {exc}"
                    ) from exc
                else:
                    logger.warning("Token acquisition failed: %s. Using fallback token.", exc)
            except Exception as exc:
                if self.raise_exception:
                    raise
                logger.warning("Token acquisition failed: %s. Using fallback token.", exc)

        params = utils.build_params(
            client=self.client_type,
            query=text,
            src=src,
            dest=dest,
            token=token,
            override=override,
        )

        url = urls.TRANSLATE.format(host=self._pick_service_url())
        try:
            r = await self.client.get(url, params=params)
        except (CurlTimeout, httpx.TimeoutException) as exc:
            raise ConnectTimeout(str(exc)) from exc
        except CurlError as exc:
            msg = str(exc).lower()
            if getattr(exc, "code", None) == 28 or "timed out" in msg or "timeout" in msg:
                raise ConnectTimeout(str(exc)) from exc
            if self.raise_exception:
                raise TranslationError(
                    f"HTTP transport error during translation request: {exc}"
                ) from exc
            logger.warning("HTTP transport error: %s. Returning fallback dummy data.", exc)
            DUMMY_DATA[0][0][0] = text
            return DUMMY_DATA, None
        except CurlRequestException as exc:
            if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
                raise ConnectTimeout(str(exc)) from exc
            if self.raise_exception:
                raise TranslationError(
                    f"HTTP transport error during translation request: {exc}"
                ) from exc
            logger.warning("HTTP transport error: %s. Returning fallback dummy data.", exc)
            DUMMY_DATA[0][0][0] = text
            return DUMMY_DATA, None

        if r.status_code == 200:
            data = utils.format_json(r.text)
            if not isinstance(data, list):
                data = [data]  # Convert dict to list to match return type
            return data, r

        if self.raise_exception:
            if r.status_code == 429:
                raise RateLimitError(
                    f'Google Translate rate limit reached (HTTP 429) from {self.service_urls}. '
                    f'Consider using transport="curl" with browser impersonation, slowing requests, or rotating proxies.',
                    status_code=429,
                    response=r,
                )
            raise TranslationError(
                f'Unexpected status code "{r.status_code}" from {self.service_urls}. '
                f'Response: {r.text[:200]}',
                status_code=r.status_code,
                response=r,
            )

        logger.warning(
            "Google Translate returned HTTP %s from %s. Returning fallback dummy data because raise_exception=False.",
            r.status_code,
            self.service_urls,
        )
        DUMMY_DATA[0][0][0] = text
        return DUMMY_DATA, r

    def _parse_extra_data(
        self, data: typing.List[typing.Any]
    ) -> typing.Dict[str, typing.Any]:
        response_parts_name_mapping = {
            0: "translation",
            1: "all-translations",
            2: "original-language",
            5: "possible-translations",
            6: "confidence",
            7: "possible-mistakes",
            8: "language",
            11: "synonyms",
            12: "definitions",
            13: "examples",
            14: "see-also",
        }

        extra = {}
        for index, category in response_parts_name_mapping.items():
            extra[category] = (
                data[index] if (index < len(data) and data[index]) else None
            )
        return extra

    async def translate(
        self,
        text: typing.Union[str, typing.List[str]],
        dest: str = "en",
        src: str = "auto",
        **kwargs: typing.Any,
    ) -> typing.Union[Translated, typing.List[Translated]]:
        dest = _normalize_lang(dest)
        src = _normalize_lang(src)

        if src != "auto" and src not in LANGUAGES:
            if src in SPECIAL_CASES:
                src = SPECIAL_CASES[src]
            elif src in LANGCODES:
                src = LANGCODES[src]
            else:
                raise ValueError("invalid source language")

        if dest not in LANGUAGES:
            if dest in SPECIAL_CASES:
                dest = SPECIAL_CASES[dest]
            elif dest in LANGCODES:
                dest = LANGCODES[dest]
            else:
                raise ValueError("invalid destination language")

        if isinstance(text, list):
            concurrency_limit = kwargs.pop(
                "list_operation_max_concurrency", self.list_operation_max_concurrency
            )
            semaphore = asyncio.Semaphore(concurrency_limit)

            async def translate_with_semaphore(item):
                async with semaphore:
                    return await self.translate(item, dest=dest, src=src, **kwargs)

            tasks = [translate_with_semaphore(item) for item in text]
            result = await asyncio.gather(*tasks)
            return result

        origin = text
        data, response = await self._translate(text, dest, src, kwargs)

        translated = "".join([d[0] if d[0] else "" for d in data[0]])
        extra_data = self._parse_extra_data(data)

        detected_src = None
        try:
            detected_src = data[2]
        except Exception:  # pragma: nocover
            pass

        # Fallback for Traditional Chinese and ambiguous detections
        if (not detected_src or detected_src == dest) and len(data) > 0 and data[0] and len(data[0][0]) > 8:
            try:
                models = data[0][0][8]
                if models and isinstance(models, list):
                    first = models[0]
                    while isinstance(first, list) and len(first) > 0 and isinstance(first[0], list):
                        first = first[0]
                    if isinstance(first, list) and len(first) >= 2 and isinstance(first[1], str) and "_" in first[1]:
                        model_src = first[1].split("_")[0]
                        if model_src:
                            detected_src = model_src
            except Exception:  # pragma: nocover
                pass

        if detected_src:
            src = detected_src

        pron = origin
        try:
            pron = data[0][1][-2]
        except Exception:  # pragma: nocover
            pass

        if pron is None:
            try:
                pron = data[0][1][2]
            except Exception:  # pragma: nocover
                pass

        if dest in EXCLUDES and pron == origin:
            pron = translated

        result = Translated(
            src=src,
            dest=dest,
            origin=origin,
            text=translated,
            pronunciation=pron,
            extra_data=extra_data,
            response=response,
            provider=self.name,
        )

        return result

    async def detect(
        self,
        text: typing.Union[str, typing.List[str]],
        **kwargs: typing.Any,
    ) -> typing.Union[Detected, typing.List[Detected]]:
        if isinstance(text, list):
            concurrency_limit = kwargs.pop(
                "list_operation_max_concurrency", self.list_operation_max_concurrency
            )
            semaphore = asyncio.Semaphore(concurrency_limit)

            async def detect_with_semaphore(item):
                async with semaphore:
                    return await self.detect(item, **kwargs)

            tasks = [detect_with_semaphore(item) for item in text]
            result = await asyncio.gather(*tasks)
            return result

        data, response = await self._translate(text, "en", "auto", kwargs)

        src = ""
        confidence = 0.0
        try:
            if len(data[8][0]) > 1:
                src = data[8][0]
                confidence = data[8][-2]
            else:
                src = "".join(data[8][0])
                confidence = data[8][-2][0]
        except Exception:  # pragma: nocover
            pass

        # Fallback if detect returned destination ('en') or empty for CJK/other characters
        if (not src or src == "en") and len(data) > 0 and data[0] and len(data[0][0]) > 8:
            try:
                models = data[0][0][8]
                if models and isinstance(models, list):
                    first = models[0]
                    while isinstance(first, list) and len(first) > 0 and isinstance(first[0], list):
                        first = first[0]
                    if isinstance(first, list) and len(first) >= 2 and isinstance(first[1], str) and "_" in first[1]:
                        model_src = first[1].split("_")[0]
                        if model_src and model_src != "en":
                            src = model_src
                            confidence = 1.0
            except Exception:  # pragma: nocover
                pass

        result = Detected(
            lang=src,
            confidence=confidence,
            response=response,
            provider=self.name,
        )
        return result
