---
name: devcard-generate
description: |
  Generate DevCard outputs in various formats (SVG, JSON, terminal, markdown).
  Use when user wants to "generate a card", "create my devcard", "make an SVG",
  "show my profile card", embed a card in their README, or export developer data.
  Covers all output formats, themes, and enrichment options.
---

# DevCard Generate

Generate developer identity cards from GitHub profiles in multiple formats.
DevCard extracts 14+ signals (languages, stack, activity, quality, expertise,
coding habits, commit quality, notable contributions, and more) and renders
them as visual cards, structured data, or terminal output.

## When to Use

- User wants to generate a DevCard for themselves or someone else
- User wants an SVG card for their GitHub README
- User wants structured JSON/YAML for agent consumption
- User wants to compare their profile to another developer
- NOT for auditing/fixing profiles — use `/devcard-profile-audit`
- NOT for agent-readiness optimization — use `/devcard-agent-ready`

## Prerequisites

- DevCard installed: `uv sync` in the devcard project
- For enriched output: `export FIREWORKS_API_KEY=<key>`
- For higher API limits: `export GITHUB_TOKEN=<token>` or `gh auth login`

## Process

1. **Determine the target.** Ask who to generate for:
   ```bash
   uv run devcard generate <username>          # Specific user
   uv run devcard me                           # Current git user
   ```

2. **Choose the format.**
   | Format | Command | Best For |
   |--------|---------|----------|
   | Terminal | `--format terminal` (default) | Quick look |
   | JSON | `--format json` | Agent consumption, APIs |
   | SVG | `--format svg` | GitHub README embed |
   | Markdown | `--format markdown` | Documentation |
   | YAML | `--format yaml` | Config files |
   | All | `--format all` | Export everything at once |

3. **Choose a theme** (SVG only).
   ```bash
   uv run devcard generate <username> --format svg --theme dark
   ```
   Themes: `default`, `dark`, `minimal`, `neon`, `terminal-green`

4. **Optional: enrich with LLM.**
   ```bash
   uv run devcard generate <username> --enrich
   ```
   Adds AI-generated summary, archetype, strengths, suggestions, and project highlights.

5. **Embed in README** (SVG). Add to the user's profile README:
   ```markdown
   <img src="./devcard.svg" alt="DevCard" width="800" />
   ```

6. **Compare two developers.**
   ```bash
   uv run devcard compare <user1> <user2>
   uv run devcard compare <user1> <user2> --format json
   ```

## Common Rationalizations

| Shortcut | Why It Fails |
|----------|-------------|
| "Just use terminal format, it's fine" | JSON is better for pipelines, SVG for READMEs. Match format to use case. |
| "Skip --no-cache, it's fast enough" | Cached data can be up to 1 hour old. Use --no-cache for fresh results. |
| "Always use --enrich" | Enrichment needs an API key and costs money. Only use when the user wants AI insights. |

## Anti-patterns

- **DO NOT** generate SVG without asking which theme the user wants
- **DO NOT** assume terminal format — ask about the intended use first
- **DO NOT** use `--enrich` without confirming the user has a Fireworks API key
- **DO NOT** generate for a private-only user without warning about limited data (60 req/hr without token)
