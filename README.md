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
# Clone the repo
git clone https://github.com/chiruu12/devcard.git
cd devcard

# Install dependencies (requires uv — https://docs.astral.sh/uv/)
uv sync

# (Recommended) Set your GitHub token for 5000 req/hr instead of 60
export GITHUB_TOKEN=$(gh auth token)   # or: export GITHUB_TOKEN=ghp_your_token

# Generate your card
uv run devcard generate YOUR_USERNAME

# Get an SVG for your GitHub README
uv run devcard generate YOUR_USERNAME --format svg --theme dark

# Get actionable profile advice
uv run devcard advise YOUR_USERNAME

# Compare two developers
uv run devcard compare karpathy torvalds

# AI-powered insights (requires Fireworks API key)
export FIREWORKS_API_KEY=your-key
uv run devcard generate YOUR_USERNAME --enrich
```

> **Note:** DevCard is not yet published to PyPI. Install from source as shown above.

## What It Extracts

DevCard analyzes public GitHub data to build a structured developer profile with 14+ signals:

| Signal | Source | Example |
|--------|--------|---------|
| **Identity** | User profile | Name, bio, location, followers |
| **Languages** | Repo language stats | Python 72% (logic), CSS 8% (presentation) |
| **Tech Stack** | Dependency files | PyTorch, FastAPI, PostgreSQL |
| **Activity** | Events + search API | Active, 679 commits/year, consistency 75/100 |
| **Top Projects** | Repos ranked by impact | Signature project with narrative |
| **Collaboration** | PRs, issues, orgs | Maintainer style, external contributions |
| **Quality** | Repo file structure | CI 80%, tests 60% + actionable recommendations |
| **Expertise** | Topics + stack + stars | Machine Learning (0.95, advanced) |
| **Notable Contributions** | PRs to popular repos | Merged PRs in keras, flask, kubernetes |
| **Coding Habits** | Commit patches | Spaces indentation, 39 chars/line avg |
| **Commit Quality** | Commit messages | Avg 160 chars, 20% multi-line |
| **README Depth** | README content analysis | 748 words avg, 78% have code blocks |
| **Code Reviews** | PR review events | 5 reviews given, 3 approved |
| **Responsiveness** | Comment events | Issue comments, PR discussion activity |

All signals are extracted from public GitHub API data.

## Commands

### `uv run devcard generate <username>`

Generate a DevCard for any public GitHub user.

```bash
uv run devcard generate torvalds                              # Terminal output (default)
uv run devcard generate torvalds --format svg --theme dark    # Dark SVG card
uv run devcard generate torvalds --format json -o out.json    # Save JSON to file
uv run devcard generate torvalds --token ghp_xxx              # Explicit token
uv run devcard generate torvalds --enrich                     # AI-powered insights
uv run devcard generate torvalds --no-cache                   # Fresh data
uv run devcard generate torvalds --verbose                    # Debug logging
```

### `uv run devcard advise <username>`

Get actionable profile advice with scores, praise, and critiques.

```bash
uv run devcard advise chiruu12                    # Rules-based advice (no LLM needed)
uv run devcard advise chiruu12 --enrich           # Add LLM-generated summary
uv run devcard advise chiruu12 --format json      # Machine-readable advice
uv run devcard advise chiruu12 --format markdown  # GFM output
```

Outputs:
- **Human Visibility Score** (0-100) -- how visible to recruiters
- **Agent Readiness Score** (0-100) -- how readable by AI tools
- **Verdicts** -- praise (what's good), critiques (what to fix), suggestions (nice-to-have)
- Each critique includes a specific **action** to fix it

### `uv run devcard compare <user1> <user2>`

Compare two developers side by side.

```bash
uv run devcard compare karpathy torvalds             # Terminal comparison
uv run devcard compare karpathy torvalds --format json   # JSON with both cards
```

### `uv run devcard validate <file>`

Validate a `devcard.json` against the schema.

```bash
uv run devcard validate my-devcard.json
```

### `uv run devcard me`

Generate a DevCard for your own GitHub account (detected via `gh` CLI).

```bash
uv run devcard me --format svg --theme neon
```

## Output Formats

```bash
uv run devcard generate <username> --format terminal   # Rich terminal panels (default)
uv run devcard generate <username> --format json        # Structured devcard.json
uv run devcard generate <username> --format yaml        # Human-friendly YAML
uv run devcard generate <username> --format svg         # Embeddable SVG card
uv run devcard generate <username> --format markdown    # GitHub Flavored Markdown
uv run devcard generate <username> --format agent       # Machine-readable key:value
uv run devcard generate <username> --format llms-txt    # llms.txt spec for AI agents
uv run devcard generate <username> --format all         # Everything at once
```

## AI Enrichment (Optional)

With a Fireworks API key, `--enrich` adds LLM-powered analysis:

- **Developer archetype** -- creative label like "ML Craftsman" or "Full-Stack Polyglot"
- **AI summary** -- 1-2 sentence narrative citing your actual projects
- **Evidence-backed strengths** -- "Strong ML foundations -- uses PyTorch across 3 projects"
- **Actionable suggestions** -- "Add CI to FungiClassifier -- it's your top project"
- **Smart project ranking** -- by significance, not just star count

```bash
export FIREWORKS_API_KEY=your-key
uv sync --extra enrich                                   # Install AI dependencies
uv run devcard generate karpathy --enrich                # Generate with AI insights
uv run devcard advise chiruu12 --enrich                  # Advice with AI summary
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

## Add DevCard to Your GitHub Profile

1. Generate your SVG:
   ```bash
   uv run devcard generate YOUR_USERNAME --format svg --theme dark -o devcard.svg
   ```

2. Add `devcard.svg` to your profile repo (`YOUR_USERNAME/YOUR_USERNAME`)

3. Reference it in your `README.md`:
   ```markdown
   <p align="center">
     <img src="devcard.svg" alt="My DevCard" width="495">
   </p>
   ```

## Claude Code Skills

DevCard ships with 4 skills for Claude Code users. Add them to your Claude Code config to get guided workflows:

| Skill | What It Does |
|-------|-------------|
| `devcard` | MCP tool orchestration — audit, compare, fix profiles |
| `devcard-profile-audit` | Full audit + advise + fix cycle |
| `devcard-generate` | Card generation in all formats |
| `devcard-agent-ready` | Make your profile AI-agent readable |

Skills are in `skills/claude-code/`. To use them, point your Claude Code skill path to this directory.

## MCP Server

DevCard includes an MCP server for AI agents (Claude Desktop, Cursor, etc.). See [devcard-mcp/README.md](devcard-mcp/README.md) for setup.

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
                 |-- Extractors (14 parallel: identity, languages, stack, activity,
                 |               projects, collaboration, quality, expertise, notable,
                 |               habits, reviews, lines, commit_quality, readme_depth,
                 |               responsiveness)
                 |-- Analyzers (developer type, project classifier, contribution style, scoring)
                 |-- Advisor (YAML rules engine + optional LLM)
                 |-- Enrichment (optional LLM via Fireworks AI)
                 |-- Renderers (terminal, SVG, markdown, JSON, YAML, agent, llms.txt)
```

## Development

```bash
uv sync                             # Install dependencies
uv run pytest                       # Run tests (357 tests)
uv run ruff check src/ tests/       # Lint
uv run devcard generate chiruu12    # Test locally
uv run devcard advise chiruu12      # Test advisor
```

## Contributing

Contributions are welcome! Here are the easiest ways to help:

### Add dependency mappings

Know a popular package we're missing? Edit [`mappings/dependencies.yaml`](mappings/dependencies.yaml):

```yaml
python:
  my-package: { category: "framework", name: "My Package" }
```

### Add advisor rules

Want to improve the profile advice? Edit [`mappings/advisor_rules.yaml`](mappings/advisor_rules.yaml). Each rule has a condition, message, and optional fix action.

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

## Roadmap

- [x] Terminal, SVG, JSON, YAML, Markdown output
- [x] Compare command
- [x] AI enrichment via Fireworks (`--enrich`)
- [x] Profile advisor with YAML rules engine (`devcard advise`)
- [x] 14 extraction signals (identity through responsiveness)
- [x] Dual scoring (human visibility + agent readiness)
- [x] Notable contributions detection
- [x] MCP server (10 tools)
- [x] Claude Code skills (4 skills)
- [ ] Web app -- connect GitHub, generate your card, share a link
- [ ] GitHub Action -- auto-update your DevCard SVG on push
- [ ] PNG export -- for social sharing
- [ ] PyPI publishing -- `pip install devcard`

## License

[Apache 2.0](LICENSE)
