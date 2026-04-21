Find all files recently changed in `components/`, `pages/`, `services/`, and `utils/` by running:

```bash
git diff --name-only HEAD
git diff --name-only --cached
```

Filter results to only files under these directories: `components/`, `pages/`, `services/`, `utils/`.

For each changed file that is not `__init__.py`:

1. Read the file to understand what functions, classes, and logic it contains.
2. Determine the corresponding test file path: replace the top-level folder with `tests/` and prefix the filename with `test_`, e.g. `services/auth.py` → `tests/test_auth.py`.
3. If the test file already exists, read it and ADD new test cases for any functions or classes not yet covered — do not remove existing tests.
4. If the test file does not exist, create it from scratch.

Test requirements:
- Use `pytest` and `sqlite3` in-memory databases (`:memory:`) for any DB-dependent tests — never touch `chat.db`.
- Import schema via `conn.executescript(open("sql/init_schema.sql").read())` in fixtures.
- For Streamlit page files (`pages/`), only test pure helper functions if any exist; skip files that are pure UI with no testable logic.
- Cover: happy path, edge cases (empty input, duplicates, missing records), and permission/access-control logic where relevant.
- Each test function name must describe what it tests: `test_<function>_<scenario>`.

After writing all test files, run coverage for the changed files only:

```bash
python -m pytest tests/ -v --cov=. --cov-report=term-missing 2>&1 | tail -50
```

**Coverage requirement: each changed source file must reach ≥ 75% line coverage.**

If any file is below 75%:
1. Read the coverage report to identify which lines are not covered.
2. Add more test cases targeting those uncovered lines.
3. Re-run coverage and repeat until all changed files meet the 75% threshold.

`pytest-cov` may need to be installed — if the command fails, run `pip install pytest-cov` first.

Report which test files were created or updated, and the final per-file coverage percentages.
