---
name: devcard-agent-ready
description: |
  Make a GitHub profile readable by AI agents and coding assistants. Use when user
  wants to improve their "agent readiness score", deploy devcard.json, create llms.txt,
  generate AGENTS.md, or make their profile machine-readable for tools like Claude Code,
  Cursor, Copilot, or Windsurf. Covers the full agent-readiness optimization workflow.
---

# DevCard Agent-Ready

AI coding assistants (Claude Code, Cursor, Copilot, Windsurf) increasingly read
developer profiles to understand who they're working with. This skill optimizes
a GitHub profile for machine readability — structured data, agent instructions,
and LLM-friendly documentation.

## When to Use

- User asks about "agent readiness" or "agent score"
- User wants to deploy devcard.json, llms.txt, or AGENTS.md
- User asks "how do AI tools see my profile"
- User wants to improve their profile for coding assistants
- NOT for human-facing profile improvement — use `/devcard-profile-audit`
- NOT for generating visual cards — use `/devcard-generate`

## Prerequisites

- DevCard installed: `uv sync` in the devcard project
- GitHub token with repo write access for deploying files
- The user's profile repo must exist (github.com/username/username)

## What Makes a Profile Agent-Ready

| Signal | Points | What It Is |
|--------|--------|------------|
| `devcard.json` in profile repo | 20 | Structured identity data for agents |
| `AGENTS.md` in top repos | 20 | Instructions for coding agents |
| `llms.txt` in profile repo | 10 | LLM-friendly profile summary |
| Structured READMEs | 15 | Parseable documentation |
| Dependency files | 10 | Stack detection (pyproject.toml, package.json) |
| Topics on repos | 10 | Domain classification signals |
| Classification coverage | 10 | Repos tagged as library/tool/app |
| CI/CD adoption | 5 | Build automation signals |

## Process

1. **Check current agent readiness score.**
   ```bash
   uv run devcard advise <username> --format json --no-cache
   ```
   Look at `agent_score` in the output. Or via MCP: `audit_profile(username)`.

2. **Identify the biggest gaps.** The score breakdown shows which signals are missing.
   Prioritize by points: devcard.json (20) > AGENTS.md (20) > llms.txt (10).

3. **Deploy devcard.json.** This is the highest-value single action.
   ```bash
   # Via MCP (recommended):
   fix_profile(username, fixes=["devcard_json"], dry_run=true)
   # Preview, then:
   fix_profile(username, fixes=["devcard_json"], dry_run=false)
   ```

4. **Generate AGENTS.md for top repos.**
   ```bash
   # Via MCP:
   fix_repo(owner, repo, fixes=["agents_md"], dry_run=true)
   # Preview, then:
   fix_repo(owner, repo, fixes=["agents_md"], dry_run=false)
   ```

5. **Deploy llms.txt.**
   ```bash
   # Generate via CLI:
   uv run devcard generate <username> --format llms-txt > llms.txt
   # Then commit to profile repo
   ```

6. **Add topics to repos** that are missing them.
   ```bash
   fix_repo(owner, repo, fixes=["topics"], dry_run=true)
   ```

7. **Re-check score.** Run the audit again and compare.

## Common Rationalizations

| Shortcut | Why It Fails |
|----------|-------------|
| "devcard.json is just metadata, not important" | It's 20% of the agent score. Agents use it to understand you instantly. |
| "AGENTS.md is overkill for my repos" | Coding agents read AGENTS.md before touching your code. Without it, they guess. |
| "I'll add topics later" | Topics are how agents classify your repos. No topics = invisible to automated discovery. |
| "My README is good enough for agents" | Agents parse structure (headings, code blocks), not prose. Structured > well-written. |

## Anti-patterns

- **DO NOT** deploy devcard.json without previewing the content first
- **DO NOT** skip AGENTS.md for repos that coding agents might work on
- **DO NOT** generate llms.txt with stale data — always use `--no-cache`
- **DO NOT** assume the profile repo exists — check first, create if needed

## Verification Checklist

- [ ] `devcard.json` deployed to profile repo (username/username)
- [ ] `llms.txt` deployed to profile repo
- [ ] `AGENTS.md` added to top 3 repos
- [ ] All repos have at least 3 topics
- [ ] Agent readiness score improved (re-audit confirms)
