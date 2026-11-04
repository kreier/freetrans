# Contributing to freetrans

Contributions to `freetrans` are welcome! Here's how to get involved.

---

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/kreier/freetrans.git
   cd freetrans
   ```

2. Set up a virtual environment using `uv` or standard Python:
   ```bash
   uv venv
   source .venv/bin/activate
   uv sync --all-extras --all-groups
   ```

3. Run the test suite:
   ```bash
   pytest
   ```

---

## Adding a New Provider

To add a new free translation provider:

1. Create a new module under `freetrans/providers/<provider_name>.py`.
2. Inherit from `freetrans.providers.base.BaseProvider`.
3. Implement `translate()`, `detect()`, and `aclose()`.
4. Register the new provider in `freetrans/providers/__init__.py`.
5. Add unit and mocked tests in `tests/`.

---

## Pull Request Guidelines

- Follow existing code style and formatting (`ruff check .`).
- Ensure all tests pass (`pytest`).
- Document new features or providers in `CHANGELOG.md` and `README.md`.
