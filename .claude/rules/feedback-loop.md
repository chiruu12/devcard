# Continuous Feedback & Learning

## After Completing a Feature

1. **Self-review** before declaring done:
   - Did I miss any edge cases?
   - Is this the simplest solution?
   - Did I update all places that needed updating?

2. **Ask for feedback**:
   - "Does this work as expected?"
   - "Anything that felt clunky or could be improved?"

3. **Capture learnings**: Proactively identify things worth remembering:
   - Technical gotchas or surprises
   - Patterns that worked well
   - Mistakes to avoid repeating
   - API quirks (especially GitHub API behavior)

   When identified, propose the specific addition:

   > "This seems worth adding to learnings.md:
   > `## [Category]`
   > `- [Specific learning]`
   > Want me to add it?"

## During Work - Watch for Friction

If the user seems frustrated, confused, or an approach isn't working:

- Pause and acknowledge: "This doesn't seem to be working well. What's off?"
- Ask what they'd prefer instead
- Offer to log the feedback for future sessions

## Automatic Retro Triggers

After any of these events, if a retro hasn't happened yet this session, offer to run `/retro`:

- Creating a PR (via `/commit-push-pr` or `gh pr create`)
- Receiving and addressing code review feedback

Lightweight prompt: "Good moment for a quick retro. Want me to run `/retro`?"
Do NOT auto-run — just offer. User can decline.
If a retro already happened this session, skip the offer.

## Elevating to Learnings

During retros or after fixing issues, actively look for things that should change future Claude behavior:

- Did we hit a gotcha that will recur?
- Did we discover something about the codebase/tools?
- Did an approach work particularly well or poorly?

**Propose specific additions** to `context/process/learnings.md` - don't just ask "anything to add?"

## When Logging Learnings

Format for `context/process/learnings.md`:

```markdown
## [Category]

- [Specific gotcha or discovery]
```

Format for `context/process/retrospective.md`:

```markdown
## YYYY-MM-DD - [Context]

**What worked:** ...
**What didn't:** ...
**Action:** ...
```
