# make_task

Resolves one backlog row from README.md "Tasks to be finished" by requirement section mask (`x.y` or `x.y.z`), implements the fix, updates the table, and runs `fire`.

## Parameter: `$ARGUMENTS`

The argument is a **section mask** of shape `x.y` or `x.y.z` (non-negative integers), e.g. `2.1.4`, `4.1.1`, `3.2`.

The mask refers to the **`section number`** column in `README.md` → section **Tasks to be finished** (the markdown table with columns `index`, `section number`, `feature`, `notes`).

**Resolve the row:**
1. Read the table in `README.md`.
2. Normalize the mask to a string (e.g. `2.1.4`).
3. Prefer a row whose `section number` cell **equals** the mask (after trimming).
4. If none, take the **first** row (lowest `index`) whose `section number` cell **contains** the mask as a substring (e.g. `2.2.2` matches `2.2.2–2.2.3`; `4.4` matches `2.7.1 / 4.4`).
5. If still none, stop and tell the user the mask does not match any row.

> Do **not** treat the mask as the table `index` column unless the user explicitly asks to match by index; default is **section number** only.

---

## Execution steps

### 1. Analyse the task

- Open `README.md`, locate the resolved row.
- Read **feature** and **notes** plus surrounding codebase (services, pages, SQL, tests).
- Infer acceptance criteria from the notes and the cited requirement sections in `2026_04_18_AI_herders_jam_-_requirements_v3 1.txt` when needed.

### 2. Implement

- Add the minimal code and schema changes to satisfy the task.
- Add or extend **tests** when behavior is non-trivial or regression-prone.
- Match existing project patterns (Streamlit, SQLite, service layer).

### 3. Update README

- **Remove** the resolved row from the table.
- **Renumber** the `index` column to consecutive integers starting at `1` for all remaining rows.
- Keep the section title `# Tasks to be finished` and the intro paragraph above the table unchanged unless the table becomes empty (then write "All listed tasks completed." and remove only the table).

### 4. Run `fire`

```bash
fire
```

If `fire` is not on `PATH`, report that clearly and do not invent a substitute unless the repo documents one (e.g. `npm run fire`).

---

## Examples

| User mask | Resolves to row (by section number) |
|-----------|--------------------------------------|
| `2.1.4`   | Working password reset (`2.1.4`)     |
| `2.2.2`   | AFK / multi-tab row (`2.2.2–2.2.3`) |
| `4.1.1`   | Rooms on the right (`4.1.1`)         |
| `4.4`     | Unread badges row (`2.7.1 / 4.4`)   |

---

## Anti-patterns

- Do not remove a row without implementing anything unless the notes confirm the work is already done on disk.
- Do not skip tests when the change touches auth, sessions, bans, or messages.
- Do not renumber indexes before the implementation is complete and verified (run tests if present).
