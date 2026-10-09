# Contributing to ActivityFlow

Thanks for helping make ActivityFlow better! Bug reports, ideas, translations and pull requests are all welcome.
Issues and pull requests can be written in **English or Persian (فارسی)**.

## Reporting bugs and requesting features

- Search [existing issues](https://github.com/miladdhs/activityflow-persian-time-tracker/issues) first.
- Use the **Bug report** or **Feature request** template.
- For bugs, include your ActivityFlow version (Settings → About), Windows version, steps to reproduce and,
  if possible, the log file from `%LOCALAPPDATA%\ActivityFlow\logs`.

## Development setup

```powershell
git clone https://github.com/miladdhs/activityflow-persian-time-tracker.git
cd activityflow-persian-time-tracker
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\scripts\run.ps1 -Demo        # run with sample data in a separate folder
```

## Before opening a pull request

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest
```

- Keep pull requests focused on one change and describe *why* it is needed.
- Add or update tests for behavior changes (`tests/`).
- If the UI changes, regenerate the screenshots with `python scripts/screenshots.py` and the banner with
  `python scripts/make_banner.py`.
- Add a line to the `[Unreleased]` section of [CHANGELOG.md](CHANGELOG.md).

## Code guidelines

- **Layering:** UI code (`app/ui`) calls services (`app/services`); only services and the database layer touch SQLAlchemy.
- **No magic values:** colors, sizes and fonts come from `app/ui/theme/tokens.py`; setting names and defaults from
  `app/core/settings_keys.py`; product name, version and URLs from `app/__init__.py`.
- **Persian text:** user-facing strings are Persian; normalize user input with `app.core.text` and format numbers,
  dates and durations only through `app.core.formatting` so the digit and calendar settings are respected.
- **Schema changes:** append a new migration to `app/database/migrations.py`; never edit a released one.
- Follow the existing style (Ruff, 120-column lines, type hints, small focused functions).

## Releasing (maintainers)

1. Update `APP_VERSION` in `app/__init__.py` and move the `[Unreleased]` notes in `CHANGELOG.md` under the new version.
2. Commit, then tag and push: `git tag v1.2.3 && git push origin v1.2.3`.
3. The **Release** workflow builds the EXE, verifies the tag matches `APP_VERSION` and publishes the GitHub release.
