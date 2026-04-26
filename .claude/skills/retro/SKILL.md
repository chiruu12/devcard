---
name: retro
user-invocable: true
description: Run a retrospective with transcript analysis and log feedback. Use when the user explicitly invokes /retro, when a full plan implementation is complete, or after creating a PR or addressing code review feedback (if a retro hasn't happened yet this session).
---
# Retrospective

Run this skill when:
- The user explicitly invokes `/retro`
- A full plan implementation is complete (all work packages done and verified)
- After creating a PR (offer a quick retro, if a retro hasn't happened yet this session)
- After receiving and addressing code review feedback (offer, if a retro hasn't happened yet this session)

For the last two triggers, use a lightweight prompt: "Good moment for a quick retro. Want me to run `/retro`?" Do NOT auto-run — just offer. If the user declines, move on.

## Steps

1. **Session time analysis**: Read the actual conversation transcript JSONL file to extract real timestamps and produce a time breakdown. Do NOT estimate or guess times from memory. Note the current time before starting — you'll record how long this analysis took in the retro log.

   **How to read the transcript:**
   - The transcript is at: `~/.claude/projects/<project-path>/<session-id>.jsonl`
   - Find the correct path by checking the context compaction summary (which includes the file path) or by globbing `~/.claude/projects/**/*.jsonl` sorted by modification time
   - Use a subagent (Agent tool with `general-purpose` type) to read the JSONL file, extract timestamps from each JSON object, and calculate durations between phases
   - Each line is a JSON object — look for timestamp fields (`timestamp`, `ts`, `createdAt`, or similar) and role fields (`user`/`human` vs `assistant`) to identify who was active when

   **What to calculate:**
   - Break the session into phases based on what was being worked on (use user messages as phase boundaries)
   - For each phase: start time, end time, duration in minutes
   - Flag user idle gaps (>5 min between user messages with no assistant activity)
   - Flag user hands-on time (auth steps, manual actions, active back-and-forth)
   - Calculate totals: session wall-clock, active work time, user hands-on time, fully automated agent time, user idle time

   Present as a time breakdown table with proportional bars and a metrics summary:

   | Started | Phase | Hands-On Time | Agent Time | Problems |
   |---------|-------|-----------------|---------------|----------|
   | ... | ... | ... | ... | ... |

   | Metric | Duration |
   |--------|----------|
   | Total wall-clock | X hours |
   | Hands-on | X hours (Y%) |
   | Automated agent time | X hours (Y%) |
   | Idle/testing/away | X hours (Y%) |

2. **Key observations from transcript**: Before asking the user for feedback, identify patterns yourself:
   - Where did Claude work most independently? Why?
   - Where were the most user interactions needed? What caused them?
   - Were there avoidable back-and-forth cycles (bugs that better testing would have caught, unclear requirements that better planning would have resolved)?
   - What was the ratio of productive work to debugging/rework?

   Present these observations to the user as conversation starters. For each observation, also suggest what kind of action might address it (see Step 5 for action types).

3. **Ask the user**:
  - What worked well in how we approached this?
  - What was frustrating or slower than expected?
  - Anything I should do differently?

4. **Wait for their response** - don't assume or fill in answers. If the user responds without proposing specific actions, that's fine — you propose them in Step 5.

5. **Propose concrete actions**: For each issue identified (from your observations in Step 2 AND the user's feedback in Step 4), investigate the right action and propose a specific deliverable.

   **5a. Launch CLAUDE.md review in parallel.** While investigating actions below, invoke the `/claude-md-improver` skill (via the Skill tool) with the key observations from Step 2 and the user's feedback from Step 4 as context.

   **5b. Investigate actions for each issue.** Each action must be one of these types:

   | Action Type | When to use | What to do |
   |-------------|-------------|------------|
   | **Update a skill** | A skill's behavior caused the issue, or a skill should enforce a new practice | Read the skill's SKILL.md, propose the specific edit |
   | **Update CLAUDE.md** | A new rule or convention should be followed in all future sessions | Propose the specific addition to the relevant section |
   | **Update docs** | Architecture, decisions, or learnings are wrong/missing | Propose the specific edit to the doc |
   | **Create a ticket** | The fix requires implementation work beyond a doc/config change | Draft the ticket title + description |
   | **No action needed** | The issue was a one-off or already resolved | Explain why no systemic fix is needed |

   For each proposed action:
   1. Read the file you'd change (skill, CLAUDE.md, doc)
   2. Identify the specific section to edit
   3. Draft the exact change (not a vague suggestion)
   4. Present to the user for approval before making changes

   **5c. Merge CLAUDE.md review results.** When the subagent returns, incorporate its recommendations into your action proposals. Deduplicate with actions you've already proposed.

6. **Get approval and execute actions**: Present all proposed actions to the user and ask which ones they'd like to take. Then execute the approved actions. Skip any the user declines.

7. **Log to `context/process/retrospective.md`** using this format:
```markdown
   ## YYYY-MM-DD - [Brief context of what we worked on]

   ### Time Breakdown
   | Started | Phase | Hands-On Time | Agent Time | Problems |
   |---------|-------|-----------------|---------------|----------|
   | ... | ... | ... | ... | ... |

   ### Metrics
   | Metric | Duration |
   |--------|----------|
   | Total wall-clock | X hours |
   | Hands-on | X hours (Y%) |
   | Automated agent time | X hours (Y%) |
   | Idle/testing/away | X hours (Y%) |
   | Retro analysis time | X min |

   ### Key Observations
   - [Patterns identified from transcript]

   ### Feedback
   **What worked:** [User's feedback]
   **What didn't:** [User's feedback]

   ### Actions Taken
   | Issue | Action Type | Change |
   |-------|-------------|--------|
   | [Issue description] | Skill / CLAUDE.md / Doc / Ticket | [Specific change made or ticket created] |
```

8. **Elevate to learnings**: Review the session for things worth adding to `context/process/learnings.md`:
  - Technical gotchas or surprises
  - Patterns that worked well
  - Mistakes to avoid repeating
  - API quirks, environment issues, or tooling discoveries

   **Propose specific additions**, e.g.:
   > "Based on this session, I'd suggest adding to learnings.md:
   > `## [Category]`
   > `- [Specific learning]`
   > Want me to add it?"

   Don't just ask "anything to add?" - identify candidates yourself.

9. **Commit** all retro changes (actions, retrospective log, learnings) with message: `docs: retro for [brief context]`

10. **Confirm** what was logged and what actions were taken.
