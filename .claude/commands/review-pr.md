---
description: Review a PR using the reviewer agent (different model)
context: fork
agent: reviewer
---

Review pull request #$ARGUMENTS on chiruu12/devcard.

## Step 1: Read context

Run `gh pr view $ARGUMENTS --repo chiruu12/devcard` to understand the PR — what it does, what issue it fixes.

## Step 2: Read the diff

Run `gh pr diff $ARGUMENTS --repo chiruu12/devcard` to see every change.

## Step 3: Read full files

For each modified file, read the complete file (not just the diff) so you understand the surrounding code and can catch issues the diff alone won't reveal.

## Step 4: Check parity

If any of these file groups were touched, check whether the others need matching changes:

**Model <-> Schema:**
- `src/devcard/models.py` <-> `schema/devcard.v1.schema.json`

**Extractor <-> Pipeline:**
- New extractor in `src/devcard/extractors/` <-> `src/devcard/pipeline.py` (is it wired in?)
- New extractor <-> `src/devcard/extractors/__init__.py` (is it exported?)

**Mapping <-> Extractor:**
- New entries in `mappings/*.yaml` <-> corresponding extractor that consumes them

**Renderer <-> Theme:**
- New renderer in `src/devcard/renderers/` <-> theme support (does it accept Theme?)

## Step 5: Check test coverage

Are new extractors/analyzers/renderers tested? Are edge cases covered? Run `gh pr diff $ARGUMENTS --repo chiruu12/devcard` again filtered to test files if needed.

## Step 6: Post review

Use `gh pr review $ARGUMENTS --repo chiruu12/devcard` with your assessment:
- `--approve` if the PR is clean
- `--request-changes --body "..."` if there are blocking issues
- `--comment --body "..."` if there are only suggestions

For inline comments on specific files/lines, first get the head commit SHA, then post:

```
COMMIT_ID=$(gh pr view $ARGUMENTS --repo chiruu12/devcard --json headRefOid --jq '.headRefOid')
gh api repos/chiruu12/devcard/pulls/$ARGUMENTS/comments \
  -f body="..." -f path="..." -F line=N -f side="RIGHT" -f commit_id="$COMMIT_ID"
```

Be thorough. This is the only review gate before merge.
