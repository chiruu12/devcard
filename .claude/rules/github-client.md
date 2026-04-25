---
paths:
  - "src/devcard/github/**/*.py"
---

# GitHub Client Conventions

## Rules
- All HTTP methods are async (`async def`)
- Rate limit handling: read `X-RateLimit-Remaining` from response headers. When below 10, log a warning. When 0, sleep until `X-RateLimit-Reset` timestamp. Never silently fail on rate limits.
- Caching: all GET requests go through diskcache with key `"GET:{url}"`. Default TTL is 1 hour. Cache stores raw JSON, not Pydantic models.
- Pagination: follow `Link` headers for paginated endpoints. Use an async generator or collect all pages — never silently return only the first page.
- Concurrency: use `asyncio.Semaphore(10)` for request throttling. The semaphore is shared across all methods on a client instance.
- Token detection order: `--token` CLI flag > `GITHUB_TOKEN` env var > `gh auth token` subprocess. Log a warning if no token found (60 req/hr limit).
- Response models: parse responses into `src/devcard/github/models.py` Pydantic models with `model_config = ConfigDict(extra="ignore")`. This ensures forward compatibility when GitHub adds new fields.
- Error responses: raise `GitHubAPIError` with status code, endpoint, and message. The pipeline catches these.
- Never hardcode GitHub API URLs — use a base URL from config (enables testing with mocked servers).
