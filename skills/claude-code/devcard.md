---
name: devcard
description: |
  Orchestrate DevCard MCP tools for GitHub profile analysis. Use when user wants to
  check a developer profile, compare developers, audit GitHub presence, generate a
  DevCard, or improve their profile. Entry point for all DevCard MCP interactions.
  Not for CLI-only operations — use devcard-generate skill for that.
---

# DevCard — MCP Tool Orchestration

DevCard's MCP server exposes 10 tools for analyzing, scoring, and improving GitHub
profiles. This skill ensures you use them in the right order and handle edge cases.

## When to Use

- User asks to "check", "analyze", or "look at" a GitHub profile
- User wants to compare two developers
- User mentions DevCard, profile scores, or agent readiness
- User wants to fix profile issues or improve their GitHub presence
- NOT when user just wants to generate a card file — use `/devcard-generate`
- NOT when user only needs agent-readiness — use `/devcard-agent-ready`

## Available Tools

### Read-Only (no token needed)
| Tool | Purpose | Returns |
|------|---------|---------|
| `get_devcard` | Full profile as structured JSON | DevCard with 14+ signals |
| `get_developer_summary` | Concise agent-friendly text | One-paragraph summary |
| `compare_developers` | Side-by-side with scores | Comparison with quality deltas |
| `check_developer_stack` | Technology lookup | Found/not-found per tech |
| `render_card` | Visual SVG card | SVG string (5 themes) |

### Analysis (no token needed)
| Tool | Purpose | Returns |
|------|---------|---------|
| `audit_profile` | Score + find issues | human_score, agent_score, issues[] |
| `analyze_repo` | Deep-dive single repo | classification, issues, suggestions |

### Write (token required, dry_run by default)
| Tool | Purpose | Changes |
|------|---------|---------|
| `fix_profile` | Fix profile-level issues | README, devcard.json, descriptions |
| `fix_repo` | Fix repo-level issues | AGENTS.md, topics, description |
| `agent_ready` | Full audit + fix cycle | All of the above |

## Process

1. **Start with `audit_profile`** to get the dual scores and issue list.
2. **Present scores honestly.** Human visibility (0-100) and agent readiness (0-100). Don't sugarcoat.
3. **Show top 3-5 issues** sorted by severity (high → medium → low).
4. **Ask the user** which issues they want to address. Don't auto-fix.
5. **Preview with `dry_run=true`** before any write operation. Show exactly what will change.
6. **Apply only after explicit confirmation** with `dry_run=false`.
7. **Re-audit** to show score improvement after fixes.

## Common Rationalizations

| Shortcut | Why It Fails |
|----------|-------------|
| "Skip audit, just fix everything" | User needs to see what's wrong first. Blind fixes erode trust. |
| "Apply fixes without preview" | Dry-run exists for a reason. One bad description update is hard to revert. |
| "Combine multiple fix types in one call" | Each fix type should be previewed separately so user can accept/reject individually. |

## Anti-patterns

- **DO NOT** call `fix_profile` or `fix_repo` without showing `dry_run=true` preview first
- **DO NOT** skip `audit_profile` and jump straight to fixes
- **DO NOT** inflate scores or hide bad signals — the user needs honest data
- **DO NOT** use write tools without confirming the user has a GitHub token set
