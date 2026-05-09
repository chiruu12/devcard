# DevCard

<p align="center">
  <img src="gallery/karpathy-dark.svg" alt="DevCard for Andrej Karpathy" width="495">
</p>

<p align="center">
  <strong>Auto-generate beautiful, agent-readable developer identity cards from GitHub.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/devcard/"><img src="https://img.shields.io/pypi/v/devcard.svg" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License">
  <img src="https://img.shields.io/badge/schema-v1.0-orange.svg" alt="Schema">
</p>

No sign-up. No scraping. Paste a GitHub username -- get a visual card, structured JSON, AI-powered insights, and terminal output in seconds.

## Why DevCard?

We optimize GitHub profiles for humans -- clean READMEs, pinned repos, contribution graphs. But AI agents are already evaluating developer capabilities, and they're scraping GitHub the same ad-hoc way we scraped resumes 10 years ago.

DevCard creates a **structured protocol for developer identity**. A `devcard.json` that says "I'm an ML engineer who ships production PyTorch, with 95% test coverage across my repos" -- readable by both humans and machines.

- **14+ signals** extracted from public GitHub data (languages, stack, activity, code quality, collaboration style)
- **Dual scoring** -- Human Visibility (recruiters) + Agent Readiness (AI tools)
- **MCP server** -- AI agents query developer profiles as structured data, not scraped HTML

## Quick Start

```bash
pip install devcard

# (Recommended) Set your GitHub token for 5000 req/hr instead of 60
export GITHUB_TOKEN=$(gh auth token)

# Generate your card
devcard generate YOUR_USERNAME

# Get an SVG for your GitHub README
devcard generate YOUR_USERNAME --format svg --theme dark

# Get actionable profile advice
devcard advise YOUR_USERNAME

# Compare two developers
devcard compare karpathy torvalds
```

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

### `devcard generate <username>`

Generate a DevCard for any public GitHub user.

```bash
devcard generate torvalds                              # Terminal output (default)
devcard generate torvalds --format svg --theme dark    # Dark SVG card
devcard generate torvalds --format json -o out.json    # Save JSON to file
devcard generate torvalds --token ghp_xxx              # Explicit token
devcard generate torvalds --enrich                     # AI-powered insights
devcard generate torvalds --no-cache                   # Fresh data
devcard generate torvalds --verbose                    # Debug logging
```

### `devcard advise <username>`

Get actionable profile advice with scores, praise, and critiques.

```bash
devcard advise chiruu12                    # Rules-based advice (no LLM needed)
devcard advise chiruu12 --enrich           # Add LLM-generated summary
devcard advise chiruu12 --format json      # Machine-readable advice
devcard advise chiruu12 --format markdown  # GFM output
```

Outputs:
- **Human Visibility Score** (0-100) -- how visible to recruiters
- **Agent Readiness Score** (0-100) -- how readable by AI tools
- **Verdicts** -- praise (what's good), critiques (what to fix), suggestions (nice-to-have)
- Each critique includes a specific **action** to fix it

### `devcard compare <user1> <user2>`

Compare two developers side by side.

```bash
devcard compare karpathy torvalds             # Terminal comparison
devcard compare karpathy torvalds --format json   # JSON with both cards
```

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

## Made for AI Agents

DevCard outputs are designed for machine consumption, not just human eyes.

```bash
devcard generate torvalds --format agent      # Key:value pairs for AI tools
devcard generate torvalds --format llms-txt   # llms.txt protocol spec
devcard generate torvalds --format json       # Structured devcard.json
```

DevCard ships as an **MCP server**, so AI agents like Claude can query developer profiles directly:

```python
# An AI agent calls:
get_devcard("torvalds")  # Returns typed fields for every signal
compare("karpathy", "torvalds")  # Side-by-side structured comparison
```

See [devcard-mcp/README.md](devcard-mcp/README.md) for MCP setup.

## AI Enrichment (Optional)

With a Fireworks API key, `--enrich` adds LLM-powered analysis:

- **Developer archetype** -- creative label like "ML Craftsman" or "Full-Stack Polyglot"
- **AI summary** -- 1-2 sentence narrative citing your actual projects
- **Evidence-backed strengths** -- "Strong ML foundations -- uses PyTorch across 3 projects"
- **Actionable suggestions** -- "Add CI to FungiClassifier -- it's your top project"
- **Smart project ranking** -- by significance, not just star count

```bash
export FIREWORKS_API_KEY=your-key
pip install devcard[enrich]                            # Install AI dependencies
devcard generate karpathy --enrich                     # Generate with AI insights
devcard advise chiruu12 --enrich                       # Advice with AI summary
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
   devcard generate YOUR_USERNAME --format svg --theme dark -o devcard.svg
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
git clone https://github.com/chiruu12/devcard.git
cd devcard
uv sync --dev                       # Install dependencies
uv run pytest                       # Run tests (361 tests)
uv run ruff check src/ tests/       # Lint
devcard generate chiruu12            # Test locally
devcard advise chiruu12              # Test advisor
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

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
- [x] PyPI publishing -- `pip install devcard`
- [ ] GitHub Action -- auto-update your DevCard SVG on push
- [ ] PNG export -- for social sharing
- [ ] Web app -- connect GitHub, generate your card, share a link

## License

[Apache 2.0](LICENSE)
