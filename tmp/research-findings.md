# DevCard Enhancement Research — Community & Recruiter Feedback

## Sources
- DEV.to articles on GitHub profile stats
- GitHub community discussions  
- Recruiter/hiring manager perspectives (Medium, DEV.to)
- lowlighter/metrics community
- Agent-readability standards (llms.txt, AGENTS.md, A2A)

## What DevCard Already Has (validated by research)
- Activity consistency/recency (recruiters care most about recent + steady)
- Code review activity (community said "PR reviews are vital but not counted")
- Coding habits from actual code patches (community wanted "real language stats from commits")
- Quality signals (CI, testing, docs, license, linting)
- Notable contributions to popular repos
- Organization contribution breakdown
- llms.txt and AGENTS.md generation

## High-Impact Gaps Identified

### 1. Commit Message Quality (HIGH — recruiter signal)
Recruiters explicitly look at commit messages for "clear, descriptive" messages.
- Average commit message length
- Conventional commits format detection (feat:, fix:, etc.)
- Presence of multi-line commit messages (body + subject)
- Languages: all from PushEvent payload

### 2. README Depth Analysis (HIGH — recruiter signal)  
Beyond "has a README" — recruiters want "Quick Start guide, screenshots/GIFs, thinking process."
- Word count / section count
- Has code blocks (setup instructions)
- Has headings (structured)
- Has images/badges
- Has "Getting Started" / "Installation" / "Usage" section

### 3. Response Time / Community Engagement (MEDIUM)
"Thoughtfully responds to feedback" matters to recruiters.
- Average time to first response on issues in owned repos
- Number of issue comments made
- PR review turnaround time

### 4. Dependency Freshness (MEDIUM — agent signal)
Are their projects using outdated dependencies?
- Compare detected stack versions to latest
- Flag severely outdated deps

### 5. Commit Frequency Distribution (LOW — already partially covered)
"Coding regularly, even if not daily" matters.
- Already have consistency_score and heatmap
- Could add: longest gap between commits, avg commits/week

### 6. Cross-Platform Presence (LOW)
- StackOverflow profile linked?
- Blog with recent posts?
- Twitter/social activity?
- Already partially covered by identity extractor
