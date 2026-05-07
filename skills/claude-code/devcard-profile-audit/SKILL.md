---
name: devcard-profile-audit
description: |
  Run a full GitHub profile audit with actionable advice. Use when user says "audit my
  profile", "what should I improve", "review my GitHub", "how's my profile", or wants
  profile advice. Combines DevCard's audit scoring, advisor rules, and fix pipelines
  into a guided improvement workflow.
---

# DevCard Profile Audit

A guided workflow that audits a GitHub profile, delivers honest scored feedback with
actionable advice, and helps the user fix issues one at a time. Uses the CLI `advise`
command for rules-based analysis and optionally the MCP tools for fixes.

## When to Use

- User asks "audit my profile" or "review my GitHub"
- User wants to know what to improve on their GitHub
- User asks "how do I look to recruiters" or "is my profile good"
- User says "advise me" or "what should I change"
- NOT for generating visual cards — use `/devcard-generate`
- NOT for just checking a specific developer's stats — use `/devcard`

## Prerequisites

- DevCard installed: `uv sync` in the devcard project
- GitHub token recommended for full data: `export GITHUB_TOKEN=<token>` or `gh auth login`

## Process

1. **Run the advisor.**
   ```bash
   uv run devcard advise <username> --format json --no-cache
   ```
   Or via MCP: `audit_profile(username)` + present scores.

2. **Present the report card.** Show:
   - Human Visibility Score: X/100
   - Agent Readiness Score: X/100
   - Category breakdown: how many praise vs critique vs suggestion verdicts

3. **Walk through critiques by severity.** Start with HIGH severity, then MEDIUM, then LOW.
   For each critique:
   - State the problem clearly
   - Show the specific action to fix it
   - Ask if the user wants to fix it now

4. **Apply fixes one at a time.** For each accepted fix:
   - Preview with `dry_run=true` (via MCP `fix_profile` or `fix_repo`)
   - Show exactly what will change
   - Apply only after "yes"

5. **Re-run audit** after fixes to show score improvement.
   ```bash
   uv run devcard advise <username> --no-cache --format json
   ```

6. **Highlight wins.** Show the praise verdicts — what the user is doing well.
   End on a positive note.

## Common Rationalizations

| Shortcut | Why It Fails |
|----------|-------------|
| "Just show the score, skip the details" | Score without context is meaningless. The verdicts explain WHY. |
| "Fix everything at once" | User loses control. One fix at a time with preview preserves trust. |
| "Skip the praise, focus on problems" | Praise calibrates — it shows the system recognizes good work too. |
| "Use --enrich for better advice" | Rules-based advice is already actionable. LLM adds a summary, not substance. |

## Anti-patterns

- **DO NOT** run advise without `--no-cache` when checking improvement — stale cache hides progress
- **DO NOT** apply fixes without dry-run preview first
- **DO NOT** skip HIGH severity critiques to focus on easy LOWs
- **DO NOT** present the advice as a generic checklist — it's personalized to THIS profile

## Verification Checklist

- [ ] Scores displayed with context (X/100, what it means)
- [ ] All HIGH severity critiques addressed or acknowledged
- [ ] Fixes previewed before applying
- [ ] Re-audit shows score change
- [ ] User understands their top 3 improvement priorities
