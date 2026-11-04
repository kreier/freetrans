# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-11-04

### Added
- **Initial Release of freetrans**: A free, open-source multi-provider translation package for Python without API keys, logins, or paid services.
- **googletrans & googletrans-curl Drop-in Compatibility**: 100% API parity with `googletrans-curl` 4.1.1, providing `Translator`, `SyncTranslator`, `LANGUAGES`, `LANGCODES`, `Translated`, `Detected`, `TranslationError`, and `RateLimitError`.
- **Pluggable Provider Architecture**:
  - Introduced `BaseProvider` abstract base class and provider registry (`freetrans.providers`).
  - Implemented `GoogleProvider` (gtx and webapp endpoints with automated token acquisition, neural model detection fallback, and pronunciation parsing).
  - Designed for straightforward future addition of free translation providers (Bing, DeepL Free, DuckDuckGo, LibreTranslate).
- **Anti-429 Rate-Limiting Protection**:
  - Integrated `curl-cffi` with Chrome TLS/JA3/HTTP2 fingerprint impersonation to bypass automated client blocks.
  - Pluggable transport modes: `'auto'` (default), `'curl'`, or `'httpx'`.
- **Synchronous & Asynchronous Support**:
  - `Translator` for native `async`/`await` workflows.
  - `SyncTranslator` wrapper with thread-isolated event loop for blocking scripts and 1-line legacy migration.
  - Convenience methods `Translator.translate_sync()` and `Translator.detect_sync()`.
- **IPv4 DNS Resolution Safeguard**:
  - Added `ipv4=True` and `ip_resolve="v4"` options to bypass broken IPv6 DNS setups and prevent 30-second libcurl timeouts.
- **Custom libcurl Options**:
  - Added `curl_options` parameter and exposed `CurlOpt` from top-level `freetrans` namespace.
- **Dual CLI Tooling**:
  - Installed command-line entry points `freetrans` and `translate` supporting text translation, language detection, IPv4 enforcement, and provider selection.
