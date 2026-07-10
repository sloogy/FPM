# Manual GUI smoke test v0.2.77

This test is mandatory before a public release because unit tests cannot replace real Qt interaction on Windows/Linux.

## Preparation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

For a clean test, use a temporary data directory:

```bash
FPM_DATA_DIR=/tmp/fpm-smoke-data python main.py
```


## Automated quick check

Before the manual test, also run:

```bash
python tools/gui_smoke_test.py
```

Return code `77` means PySide6/Qt is not installed in this environment; in that case the manual GUI test on a real target system is required.

## Required check

1. App starts without a second main window and without traceback.
2. App starts in Simple mode: Dashboard, Pens, Inks, Rotation, Help and Settings are visible.
3. The four dashboard actions are visible: Add pen, Add ink, Fill pen, Log cleaning.
4. Enable the expert area via the sidebar button: all groups appear again.
5. `Ctrl+1` to `Ctrl+9` and `Alt+1` to `Alt+5` open the expected modules in Expert mode.
6. Switch back to Simple mode: expert modules are hidden again.
7. Create a new database or use an empty test database.
8. Add a pen: brand, model, filling system and nib data save correctly.
9. Add an ink: brand, name, color and fill level save correctly.
10. Fill a pen with ink.
11. Open rotation and generate suggestions.
12. Clean the fill and optionally refill directly.
13. Enable Expert mode, open rules and enable/disable at least one rule.
14. Switch language to English, restart, check rotation/rule texts.
15. Switch language to French, restart, check rotation/rule texts.
16. Create a wishlist item and transfer it into an expense.
17. Open expenses, check entry, test CSV export.
18. Open settings, change UI scaling, restart.
19. Create backup and restore it in a clean temporary data folder.
20. Open help and start/cancel the tour.
21. Close and restart the app: no data loss, no startup errors.

## Release criterion

Release is allowed only when all required checks work without crashes, unclear error messages or data loss.

GitHub release path in v0.2.77: https://github.com/sloogy/FPM/releases. The updater uses latest.json via /releases/latest/download/latest.json.
