Execute the following steps in order:

## Step 1 — Check changes

Run:
```bash
git status --short
git diff --name-only HEAD
git ls-files --others --exclude-standard
```

Identify all modified, staged, and untracked files. If there are no changes at all, stop and report "Nothing to commit."

## Step 2 — Run /add-tests

Execute the full `/add-tests` skill for any changed files in `components/`, `pages/`, `services/`, or `utils/`. Follow the skill exactly, including the ≥75% coverage requirement and iteration until coverage is met.

If no files in those directories changed, skip this step.

## Step 3 — Stage all changes

Run:
```bash
git add -A
```

## Step 4 — Commit with a short description

Write a commit message that:
- Summarises what actually changed (not generic filler)
- Is between **5 and 13 words** — count them, do not exceed 13
- Uses imperative mood ("Add", "Fix", "Update", not "Added", "Fixed")
- Has no period at the end

Then commit:
```bash
git commit -m "<your message>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

Report the final commit hash and message.
