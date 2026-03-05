# CLAUDE.md — subscription-sanity codebase guide

## What this is

`subscription-sanity` audits a RevenueCat project configuration and flags common
wiring mistakes before they become support tickets. It validates products,
entitlements, offerings, and packages are correctly connected.

## Stack

- **Python 3.12**, strict typing throughout
- **`uv`** for dependency management
- **`ruff`** for lint + format — always `uv run ruff`, never bare `ruff`
- **`pytest`** for tests
- **RevenueCat v2 REST API** (no SDK dependency)

## Conventions

- TDD: write tests first, watch fail, implement
- Always `uv run ruff format` before committing (not bare `ruff format`)
- All API calls use `urllib.request` (stdlib only, no httpx dependency)
- Auth: `RC_API_KEY` env var, `RC_PROJECT_ID` env var

## Running

```bash
# Audit a project
RC_API_KEY=sk_... RC_PROJECT_ID=projXXX uv run python audit.py

# Tests
uv run pytest

# Lint
uv run ruff check .
uv run ruff format --check .
```

## Key checks performed

1. All products attached to at least one entitlement
2. All entitlements have at least one product
3. Default offering exists and is marked `is_current: true`
4. All packages have products attached
5. No orphaned products (created but unattached)

## RevenueCat API notes

- Base: `https://api.revenuecat.com/v2`
- Auth: `Authorization: Bearer <v2_secret_key>`
- `expand` param must be repeated: `?expand=a&expand=b` (not comma-separated)
- 409 = `resource_already_exists` (not `already_exists`)
