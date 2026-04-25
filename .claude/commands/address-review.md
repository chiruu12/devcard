---
description: Address PR review comments, file follow-up issues, push fixes
---

Address review comments on PR #$ARGUMENTS for chiruu12/devcard.

## Step 1: Read all review feedback

```
gh pr view $ARGUMENTS --repo chiruu12/devcard --comments
gh api repos/chiruu12/devcard/pulls/$ARGUMENTS/reviews
gh api repos/chiruu12/devcard/pulls/$ARGUMENTS/comments
```

## Step 2: Checkout the PR branch

```
gh pr checkout $ARGUMENTS --repo chiruu12/devcard
```

If already on the correct branch, skip this.

## Step 3: Categorize each comment

For every review comment, decide:

- **Fix needed**: A legitimate issue introduced by this PR. Fix it.
- **Out of scope / pre-existing**: A real problem, but not introduced by this PR. File a GitHub issue to track it.
- **Disagree**: The reviewer is wrong or it's a style preference. Reply explaining why.

Present the categorization to the user before proceeding. Wait for confirmation.

## Step 4: Make fixes

For each comment categorized as "fix needed":

1. Make the code fix
2. Create a **separate commit per fix** so the review trail stays visible. Use descriptive messages that reference the review comment (e.g., `fix: validate input before processing per review feedback`)

After all fixes:

```
uv run pytest && uv run ruff check src/ tests/
```

If tests fail, fix and re-run before continuing.

## Step 5: File follow-up issues

For each out-of-scope finding, create a tracked issue:

```
gh issue create --repo chiruu12/devcard \
  --title "<concise description>" \
  --body "Identified during review of #$ARGUMENTS.

## Context
<what was found and why it matters>

## Suggested approach
<if you have one>"
```

Do NOT skip this. The whole point is to avoid losing track of work.

## Step 6: Reply to review comments

For each comment that was addressed, reply confirming the fix. Use the appropriate endpoint for each comment type:

**Inline review comments** (from `pulls/$ARGUMENTS/comments`):

```
gh api repos/chiruu12/devcard/pulls/$ARGUMENTS/comments/{comment_id}/replies \
  -f body="Fixed in <commit sha>"
```

**Top-level PR comments** (from `gh pr view --comments`):

```
gh api repos/chiruu12/devcard/issues/$ARGUMENTS/comments \
  -f body="Re: <summary of feedback> — Fixed in <commit sha>"
```

For disagreements, reply with your reasoning.

## Step 7: Push

```
git push
```

## Step 8: Summary

Print a final summary:

- Comments addressed (with commit references)
- Comments disagreed with (with reasoning)
- Follow-up issues filed (with issue numbers and links)
- Reminder: consider running `/retro` to capture learnings
