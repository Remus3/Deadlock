# Deadlock config and tuning

Versioned settings and small tools for Valve's Deadlock on Windows: an
autoexec, Steam launch options and video settings kept in git, a script that
re-applies them with backups and read-back, and a measurement method for
deciding what stays.

It never touches game binaries, archives, memory or network traffic, and it
never sends input to the game. Only user-facing settings the game and Steam
expose are written.

## Use

```
python tools/dl_paths.py              # find the install (paths redacted)
python tools/dl_launch.py check       # Steam launch options vs config/
python tools/dl_video.py check        # video file vs config/ (after first launch)
powershell -NoProfile -ExecutionPolicy Bypass -File tools\Apply-DeadlockConfig.ps1 -WhatIf
```

What each setting does and how to undo it: `docs/optimization.md`.
How a change is measured: `docs/measurement.md`.

## Development

Python 3.11+ standard library only; tests use pytest. `python -m pytest -q`.
Hooks: `git config core.hooksPath .githooks` (identity check, privacy scan).

Licensed under Apache-2.0 (`LICENSE`, `NOTICE`). Not affiliated with Valve.
