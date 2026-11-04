# freetrans

[![PyPI version](https://img.shields.io/pypi/v/freetrans-py.svg)](https://pypi.org/project/freetrans-py/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![GitHub Repo](https://img.shields.io/badge/github-kreier%2Ffreetrans-blue.svg)](https://github.com/kreier/freetrans)

**freetrans** is a free, open translation library for Python across multiple providers.

No API keys, no logins, no subscription fees, no credit cards. Just free, open translation that works.

Built as an extensible drop-in replacement for `googletrans` and `googletrans-curl`, `freetrans` integrates [`curl-cffi`](https://github.com/lexiforest/curl_cffi) browser TLS/JA3 fingerprint impersonation to eliminate **HTTP 429 Too Many Requests** and rate-limiting blocks.

---

## Why freetrans?

Translating text programmatically in Python shouldn't require paid API keys, monthly subscription tiers, or dealing with fragile rate limits.

- **Drop-in Compatible**: Compatible with `googletrans` and `googletrans-curl` workflows.
- **Provider-Extensible**: Begins with full Google Translate support (gtx/webapp endpoints) and is architected to expand to Bing, DeepL Free, DuckDuckGo, and other services.
- **Anti-429 Protection**: Uses `curl-cffi` browser fingerprint impersonation (default: Chrome) to bypass automated bot detection and HTTP 429 rate limits.
- **Async & Sync**: Native `async`/`await` support with `Translator`, plus a rock-solid threaded synchronous wrapper `SyncTranslator` and convenience methods `translate_sync` / `detect_sync`.
- **IPv4 DNS Fallback**: Built-in `ipv4=True` option prevents 30-second libcurl timeouts on networks/routers with broken IPv6 resolution.
- **CLI Included**: Full-featured command-line tool (`freetrans` and `translate`).

---

## Installation

```bash
pip install freetrans-py
```

> **Note on Naming:** The PyPI package distribution is named **`freetrans-py`**, while the Python module namespace is **`freetrans`**:
> ```python
> from freetrans import SyncTranslator, Translator
> ```

---

## Quickstart

### 1. Synchronous Usage (`SyncTranslator`)

Ideal for scripts, data analysis, Jupyter notebooks, and legacy codebases:

```python
from freetrans import SyncTranslator

with SyncTranslator() as translator:
    result = translator.translate("Artificial intelligence is transforming our world.", dest="de")
    print(result.text)
    # Output: Künstliche Intelligenz verändert unsere Welt.
```

Or 1-line drop-in migration from legacy synchronous code:

```python
# Simply replace your import:
from freetrans import SyncTranslator as Translator

translator = Translator()
result = translator.translate("Hello world", dest="es")
print(result.text)  # ¡Hola Mundo!
translator.close()
```

### 2. Asynchronous Usage (`Translator`)

Native async/await for high-performance applications and web frameworks (FastAPI, Starlette, Quart, etc.):

```python
import asyncio
from freetrans import Translator

async def main():
    async with Translator() as translator:
        # Single translation
        result = await translator.translate("Bonjour le monde", dest="en")
        print(f"[{result.src} -> {result.dest}] {result.text}")
        # Output: [fr -> en] Hello World

        # Batch translation
        items = ["Good morning", "Good afternoon", "Good night"]
        translations = await translator.translate(items, dest="ja")
        for item in translations:
            print(f"{item.origin} -> {item.text}")

asyncio.run(main())
```

### 3. Language Detection

```python
from freetrans import SyncTranslator

with SyncTranslator() as translator:
    detection = translator.detect("이 문장은 한국어로 작성되었습니다.")
    print(f"Language: {detection.lang}, Confidence: {detection.confidence}")
    # Output: Language: ko, Confidence: 1.0
```

---

## Architecture & Providers

`freetrans` decouples the client API from translation backend providers:

```text
                  Application Code
                         │
                         │ from freetrans import Translator
                         ▼
                 ┌───────────────┐
                 │  freetrans    │
                 │  Translator   │
                 └───────┬───────┘
                         │
        ┌────────────────┼────────────────┐
        │ provider       │ provider       │ provider
        ▼                ▼                ▼
┌───────────────┐┌───────────────┐┌───────────────┐
│GoogleProvider ││ BingProvider  ││ DeepL Provider│
│  (Default)    ││   (Planned)   ││   (Planned)   │
└───────┬───────┘└───────────────┘└───────────────┘
        │
   ┌────┴────┐
   │transport│
   ▼         ▼
curl-cffi  httpx
(Chrome)
   │
   ▼
Free Translation Service
```

### Selecting Providers

```python
# Default provider is Google
translator = Translator(provider="google")
```

---

## Advanced Options

### Preventing IPv6 DNS Timeouts (`ipv4=True`)

Networks or Wi-Fi routers with broken IPv6 DNS frequently cause 30-second libcurl connection timeouts. Pass `ipv4=True` or `ip_resolve="v4"` to force IPv4 DNS queries:

```python
translator = Translator(ipv4=True)
# or
sync_trans = SyncTranslator(ipv4=True)
```

### Pluggable HTTP Transport

```python
# Auto-detects curl-cffi, falls back to httpx (default)
t1 = Translator(transport="auto")

# Enforce curl-cffi with custom browser impersonation
t2 = Translator(transport="curl", impersonate="safari")

# Use standard httpx
t3 = Translator(transport="httpx")
```

### Custom `curl_options`

Arbitrary libcurl options can be passed directly:

```python
from freetrans import CurlOpt, Translator

options = {
    CurlOpt.CONNECTTIMEOUT: 10,
    CurlOpt.FOLLOWLOCATION: 1,
}
translator = Translator(curl_options=options)
```

---

## Command Line Interface (CLI)

`freetrans` provides CLI tools via both `freetrans` and `translate` commands:

```bash
# Basic translation
freetrans "Hello world!" -d es
# Output:
# [en] Hello world!
#     ->
# [es] ¡Hola Mundo!

# Detect language
freetrans -c "Bonjour tout le monde"
# Output: [fr, 1.0] Bonjour tout le monde

# Force IPv4 resolution
freetrans "Welcome home" -d de -4

# Specify provider
freetrans "Hello friend" -d zh-cn -p google
```

---

## Migration Guide

### Migrating from `googletrans` or `googletrans-curl`

1. Change your package dependency from `googletrans` or `googletrans-curl` to `freetrans-py`:
   ```bash
   pip uninstall googletrans googletrans-curl
   pip install freetrans-py
   ```

2. Update your Python imports:
   ```python
   # Old:
   from googletrans import Translator, SyncTranslator, LANGUAGES

   # New:
   from freetrans import Translator, SyncTranslator, LANGUAGES
   ```

All parameters, methods, return objects (`Translated`, `Detected`), and exceptions are 100% compatible.

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
