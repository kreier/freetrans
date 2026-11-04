# freetrans Roadmap

This document outlines the planned progression for **freetrans**.

---

## Phase 1: Foundation (v0.1.0) — *Current*
- [x] Initial release of `freetrans`.
- [x] Full feature parity and drop-in compatibility with `googletrans-curl`.
- [x] Decoupled multi-provider architecture (`BaseProvider` + provider registry).
- [x] Default `GoogleProvider` with `gtx` and `webapp` endpoints.
- [x] Anti-429 rate limit protection via `curl-cffi` TLS/fingerprint impersonation.
- [x] Dual sync (`SyncTranslator`) and async (`Translator`) support.
- [x] IPv4 DNS override (`ipv4=True`).
- [x] CLI entrypoints (`freetrans`, `translate`).
- [x] 100% test suite passing with CI workflow.

---

## Phase 2: Provider Expansion (v0.2.0 - v0.4.0)
- [ ] **Bing Translator Provider**: Free web translation endpoint without Azure credentials.
- [ ] **DuckDuckGo Translation Provider**: Free translation endpoint powered by DuckDuckGo.
- [ ] **DeepL Free Web Provider**: Reverse-engineered free web translator endpoint for European languages.
- [ ] **LibreTranslate Provider**: Integration with public/open LibreTranslate mirrors.
- [ ] **Multi-provider Language Mapping**: Unified language code normalizer across disparate provider codes.

---

## Phase 3: Resilience & Automatic Fallback (v0.5.0)
- [ ] **Provider Fallback Chains**: Automatically fall back to secondary providers (e.g. Google -> Bing -> DeepL) if the primary provider is rate-limited or temporarily unavailable.
- [ ] **Dynamic Provider Health Tracking**: Monitor provider response latency and error rates to select the healthiest provider.
- [ ] **Proxy Rotation & Pools**: Built-in support for proxy pools with round-robin health checks.

---

## Phase 4: Production Maturity (v1.0.0)
- [ ] Comprehensive documentation site with Sphinx / MkDocs.
- [ ] Full coverage of language pairs and dialect mappings across all providers.
- [ ] Benchmark dashboard tracking response times, success rates, and translation quality.
