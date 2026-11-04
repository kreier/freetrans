# AGENTS.md

## Project Overview

`freetrans` is a free, open-source multi-provider translation library for Python without API keys, logins, or paid tiers.

It was created to expand beyond `googletrans-curl`, providing the same anti-429 `curl-cffi` browser impersonation benefits, sync/async ergonomics, and drop-in compatibility for googletrans users, while architecting a modular foundation for multiple free translation providers.

---

## Core Principles

1. **Free by Design**: Never require API keys, credentials, sign-ups, or credit cards for any supported provider.
2. **Backward & Drop-in Compatibility**: Retain complete drop-in signature parity with `googletrans` and `googletrans-curl` (`Translator`, `SyncTranslator`, `translate`, `detect`, `Translated`, `Detected`, `LANGUAGES`, etc.).
3. **Pluggable Architecture**: All translation services implement `BaseProvider`. The public `Translator` interface remains uniform regardless of which backend is invoked.
4. **Anti-429 Protection**: Use `curl-cffi` with browser fingerprint impersonation (default: Chrome) to prevent bot-detection rate limits.
5. **Deterministic Testing**: Ensure unit tests run offline with mocks and pass quickly without network flakiness. Live network tests are isolated with `@pytest.mark.live`.
6. **Sync & Async Parity**: Always ensure synchronous scripts (`SyncTranslator`) and asynchronous services (`Translator`) work seamlessly with identical return types.
