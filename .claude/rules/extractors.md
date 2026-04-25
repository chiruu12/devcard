---
paths:
  - "src/devcard/extractors/**/*.py"
---

# Extractor Conventions

## Pattern-Matching
Before writing a new extractor, read `src/devcard/extractors/identity.py` (simplest) and `src/devcard/extractors/stack.py` (most complex) to match existing patterns.

## Rules
- Every extractor is an async function with signature: `async def extract_<name>(client: GitHubClient, user: GitHubUser, repos: list[GitHubRepo], **kwargs) -> <PydanticModel> | None`
- Return `None` on failure, never raise — the pipeline handles partial results gracefully
- Use `asyncio.gather` with `return_exceptions=True` for concurrent sub-fetches within an extractor
- Use the client's built-in semaphore for concurrent API calls — never create your own
- Minimize API calls: reuse the shared `root_listings` dict (fetched once per repo in the pipeline) instead of re-fetching directory contents
- All extractors must be importable and usable independently — no hidden coupling between extractors
- The `expertise` extractor depends on `stack` and `languages` extractor output. Declare this dependency in pipeline orchestration, not inside the extractor itself.
- Log API failures with `logger.warning`, not `logger.error` — partial data is expected behavior, not an error
