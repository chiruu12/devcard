# DevCard Value Proposition

DevCard auto-generates structured, agent-readable developer identity cards from any public GitHub profile.

## Three audiences, three outputs

1. **For AI agents**: A standardized schema (`devcard.json`) that replaces ad-hoc GitHub scraping with a structured protocol. Agents get typed fields for languages, stack, expertise, activity patterns, and quality signals.
2. **For developers**: A beautiful visual card (SVG) that auto-updates from GitHub activity. Embeddable in READMEs, shareable on social media, no maintenance required.
3. **For recruiters/team leads**: Structured, comparable developer profiles with quality signals that go beyond "years of experience."

## Key differentiator

DevCard is not opt-in. It works on ANY public GitHub profile. The developer doesn't need to do anything. This is the Gravatar model, not the LinkedIn model.

## No LLM required

All extraction is GitHub API + heuristics. The dependency mapping (`mappings/dependencies.yaml`) is deterministic, reproducible, free, and fast. LLM enrichment is optional (`--enrich` flag) for developers who want richer summaries.

## Distribution strategy

The visual card (SVG) is the Trojan horse. Developers embed cards in their GitHub profile READMEs (proven model — GitHub stats cards have 70k+ stars). The JSON schema rides along for free.
