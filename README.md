# DevCard

**Auto-generate beautiful, agent-readable developer identity cards from GitHub.**

No sign-up. No scraping. Paste a GitHub username -- get a visual card, structured JSON, AI-powered insights, and terminal output in seconds.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)
![Schema](https://img.shields.io/badge/schema-v1.0-orange.svg)

<p align="center">
  <img src="gallery/karpathy-dark.svg" alt="DevCard for Andrej Karpathy" width="495">
</p>

## Quick Start

```bash
# Install
pip install devcard        # or: uv pip install devcard

# Generate your card
devcard generate karpathy

# Get an SVG for your GitHub README
devcard generate karpathy --format svg --theme dark

# Compare two developers
devcard compare karpathy torvalds

# AI-powered insights (requires Fireworks API key)
export FIREWORKS_API_KEY=your-key
devcard generate karpathy --enrich
```

## Setup

```bash
# Clone and install
git clone https://github.com/chiruu12/devcard.git
cd devcard
uv sync

# Copy the env template
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN (required) and FIREWORKS_API_KEY (optional)

# Generate a card
uv run devcard generate YOUR_USERNAME
```

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Recommended | GitHub personal access token (60 req/hr without, 5000 with) |
| `FIREWORKS_API_KEY` | Optional | Fireworks AI key for `--enrich` (AI summaries, archetypes) |

Create a GitHub token at [github.com/settings/tokens](https://github.com/settings/tokens) -- no special scopes needed.

## What It Extracts

DevCard analyzes public GitHub data to build a structured developer profile:

| Signal | Source | Example |
|--------|--------|---------|
| **Identity** | User profile | Name, bio, location, followers |
| **Languages** | Repo language stats | Python 72% (logic), CSS 8% (presentation) |
| **Tech Stack** | Dependency files | PyTorch, FastAPI, PostgreSQL |
| **Activity** | Events + push dates | Active, consistency 75/100, bursty Fri & Sat |
| **Top Projects** | Repos ranked by impact | Signature project with narrative |
| **Collaboration** | PRs, issues, orgs | Maintainer style, external contributions |
| **Quality** | Repo file structure | CI 80%, tests 60% + actionable recommendations |
| **Expertise** | Topics + stack + stars | Machine Learning (0.95, advanced) |

All signals are extracted from pure GitHub API data -- fully deterministic.

## AI Enrichment (Optional)

With a Fireworks API key, `--enrich` adds LLM-powered analysis:

- **Developer archetype** -- creative label like "ML Craftsman" or "Full-Stack Polyglot"
- **AI summary** -- 1-2 sentence narrative citing your actual projects
- **Evidence-backed strengths** -- "Strong ML foundations -- uses PyTorch across 3 projects"
- **Actionable suggestions** -- "Add CI to FungiClassifier -- it's your top project"
- **Smart project ranking** -- by significance, not just star count

```bash
export FIREWORKS_API_KEY=your-key
uv sync --extra enrich                     # Install AI dependencies
uv run devcard generate karpathy --enrich  # Generate with AI insights
```

## Themes

<table>
<tr>
<td align="center"><strong>Default</strong></td>
<td align="center"><strong>Dark</strong></td>
</tr>
<tr>
<td><img src="gallery/karpathy-default.svg" width="400"></td>
<td><img src="gallery/karpathy-dark.svg" width="400"></td>
</tr>
<tr>
<td align="center"><strong>Minimal</strong></td>
<td align="center"><strong>Neon</strong></td>
</tr>
<tr>
<td><img src="gallery/karpathy-minimal.svg" width="400"></td>
<td><img src="gallery/karpathy-neon.svg" width="400"></td>
</tr>
<tr>
<td align="center" colspan="2"><strong>Terminal Green</strong></td>
</tr>
<tr>
<td colspan="2" align="center"><img src="gallery/karpathy-terminal-green.svg" width="400"></td>
</tr>
</table>

## Output Formats

```bash
devcard generate <username> --format terminal   # Rich terminal panels (default)
devcard generate <username> --format json        # Structured devcard.json
devcard generate <username> --format yaml        # Human-friendly YAML
devcard generate <username> --format svg         # Embeddable SVG card
devcard generate <username> --format markdown    # GitHub Flavored Markdown
devcard generate <username> --format agent       # Machine-readable key:value
devcard generate <username> --format llms-txt    # llms.txt spec for AI agents
devcard generate <username> --format all         # Everything at once
```

## Commands

### `devcard generate <username>`

Generate a DevCard for any public GitHub user.

```bash
devcard generate torvalds                              # Terminal output
devcard generate torvalds --format svg --theme dark    # Dark SVG card
devcard generate torvalds --format json -o out.json    # Save JSON to file
devcard generate torvalds --token ghp_xxx              # Authenticated (5000 req/hr)
devcard generate torvalds --enrich                     # AI-powered insights
devcard generate torvalds --verbose                    # Debug logging
devcard generate torvalds --no-cache                   # Skip cache
```

### `devcard compare <user1> <user2>`

Compare two developers side by side.

```bash
devcard compare karpathy torvalds           # Terminal comparison
devcard compare karpathy torvalds --format json  # JSON with both cards
```

Shows: language overlap, stack overlap (shared frameworks), expertise comparison, quality head-to-head, activity comparison, and top projects.

### `devcard validate <file>`

Validate a `devcard.json` against the schema.

```bash
devcard validate my-devcard.json
```

### `devcard me`

Generate a DevCard for your own GitHub account (detected via `gh` CLI).

```bash
devcard me --format svg --theme neon
```

## Add DevCard to Your GitHub Profile

1. Generate your SVG:
   ```bash
   devcard generate YOUR_USERNAME --format svg --theme dark -o devcard.svg
   ```

2. Add `devcard.svg` to your profile repo (`YOUR_USERNAME/YOUR_USERNAME`)

3. Reference it in your `README.md`:
   ```markdown
   <p align="center">
     <img src="devcard.svg" alt="My DevCard" width="495">
   </p>
   ```

## The devcard.json Schema

Every DevCard produces a `devcard.json` -- a structured, agent-readable profile:

```json
{
  "$schema": "https://devcard.dev/schema/v1",
  "version": "1.0",
  "identity": {
    "username": "karpathy",
    "name": "Andrej Karpathy",
    "bio": "I like to train neural nets",
    "followers": 95000
  },
  "languages": [
    { "name": "Python", "percentage": 72.3, "category": "logic" }
  ],
  "expertise": {
    "domains": [
      { "name": "Machine Learning", "confidence": 1.0, "skill_level": "expert" }
    ],
    "profile_type": "ml"
  }
}
```

The full schema is at [`schema/devcard.v1.schema.json`](schema/devcard.v1.schema.json).

## Architecture

```
CLI (typer) --> Pipeline
                 |-- GitHub Client (async httpx, cached, rate-limited)
                 |-- Extractors (identity, languages, stack, activity, projects,
                 |               collaboration, quality, expertise)
                 |-- Analyzers (developer type, project classifier, contribution style, scoring)
                 |-- Enrichment (optional LLM via Fireworks AI)
                 |-- Renderers (terminal, SVG, markdown, JSON, YAML, agent, llms.txt)
```

Key principle: Extractors return `None` on failure -- the pipeline assembles whatever data it can. A DevCard with just an identity section is valid.

## Contributing

Contributions are welcome! Here are the easiest ways to help:

### Add dependency mappings

Know a popular package we're missing? Edit [`mappings/dependencies.yaml`](mappings/dependencies.yaml):

```yaml
python:
  my-package: { category: "framework", name: "My Package" }
```

### Add a theme

Create a new file in `src/devcard/renderers/themes/`:

```python
from devcard.renderers.themes.base import Theme

THEME = Theme(
    name="my-theme",
    background="#...",
    foreground="#...",
    secondary="#...",
    accent="#...",
    border="#...",
)
```

### Development

```bash
uv sync                           # Install dependencies
uv run pytest                     # Run tests
uv run ruff check src/ tests/     # Lint
uv run devcard generate chiruu12  # Test locally
```

## Roadmap

- [x] Terminal, SVG, JSON, YAML, Markdown output
- [x] Compare command (`devcard compare user1 user2`)
- [x] AI enrichment via Fireworks (`--enrich`)
- [x] Language DNA (logic vs presentation split)
- [x] Activity consistency score + sparkline
- [x] Quality recommendations
- [x] Signature project detection
- [ ] Web app -- connect GitHub, generate your card, share a link
- [ ] GitHub Action -- auto-update your DevCard SVG on push
- [ ] MCP server -- let AI agents query DevCards programmatically
- [ ] PNG export -- for social sharing

## License

[Apache 2.0](LICENSE)
