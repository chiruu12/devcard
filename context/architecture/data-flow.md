# DevCard Data Flow

## Pipeline Stages

```mermaid
flowchart TD
    CLI[CLI: devcard generate username] --> Pipeline
    Pipeline --> Fetch[GitHub Client: fetch user + repos]
    Fetch --> RootListings[Fetch root dir listings for top N repos]

    Fetch --> E1[Identity Extractor]
    Fetch --> E2[Languages Extractor]
    RootListings --> E3[Stack Extractor]
    Fetch --> E4[Activity Extractor]
    Fetch --> E5[Projects Extractor]
    Fetch --> E6[Collaboration Extractor]
    RootListings --> E7[Quality Extractor]

    E2 & E3 --> E8[Expertise Extractor]

    E1 & E2 & E3 & E4 & E5 & E6 & E7 & E8 --> Analyzers

    Analyzers --> A1[Developer Type]
    Analyzers --> A2[Project Classifier]
    Analyzers --> A3[Contribution Style]
    Analyzers --> A4[Quality Scoring]

    A1 & A2 & A3 & A4 --> DevCard[DevCard Model]

    DevCard --> R1[Terminal Renderer]
    DevCard --> R2[SVG Renderer]
    DevCard --> R3[JSON Output]
    DevCard --> R4[Markdown Renderer]
    DevCard --> R5[HTML Renderer]
```

## API Call Budget

For a user with N repos (capped at `max_repos`, default 30):
- 1 call: user profile
- 1-3 calls: repos list (paginated)
- N calls: languages per repo
- N calls: root directory listing per repo (shared by stack + quality extractors)
- 1 call: user events (last 300)
- 1 call: user orgs
- Selective calls: dependency file contents (only when dep files found in root listing)

**Total estimate**: ~65-100 calls for a 30-repo user. Well within 5000/hr authenticated limit. Without auth (60/hr), a single generation may exhaust the budget.

## Concurrency Model

- `asyncio.Semaphore(10)` gates all GitHub API requests
- Independent extractors run concurrently via `asyncio.gather`
- Within an extractor, per-repo fetches run concurrently (using the shared semaphore)
- Dependent extractors (expertise) wait for their dependencies (stack, languages)
- All caching happens at the HTTP layer (diskcache), transparent to extractors
