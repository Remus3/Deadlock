# VeilWalker - Deadlock config and tuning

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Versioned settings and small tools for Valve's Deadlock on Windows: an
autoexec, Steam launch options and video settings kept in git, a script that
re-applies them with backups and read-back, and a measurement method for
deciding what stays.

It never touches game binaries, archives, memory or network traffic, and it
never sends input to the game. Only user-facing settings the game and Steam
expose are written.

Status: settings applied and read back on one Windows 10 PC; performance
baseline not yet measured; the companion app is in early development.

## Use

```
python tools/vw_paths.py              # find the install (paths redacted)
python tools/vw_launch.py check       # Steam launch options vs config/
python tools/vw_video.py check        # video file vs config/ (after first launch)
python tools/vw_frametime.py run1.csv run2.csv run3.csv   # fps and lows from PresentMon
powershell -NoProfile -ExecutionPolicy Bypass -File tools\Apply-DeadlockConfig.ps1 -WhatIf
```

## Documentation

- [docs/optimization.md](docs/optimization.md) - what each setting does and how to undo it.
- [docs/measurement.md](docs/measurement.md) - how a change is measured.
- [docs/controls.md](docs/controls.md) - controls and binds.

## Companion app

`app/` is an Electron desktop companion for Deadlock, in early development.
It reads only public data, post-match data and the game's own outputs, and
never attaches to the game.

## Development

Python 3.11+ standard library only; tests use pytest. `python -m pytest -q`.
Hooks: `git config core.hooksPath .githooks` (identity check, privacy scan,
commit subject at most 72 characters).

## How this repo is built

Maintained by one operator with AI coding agents working under written rules
(`CLAUDE.md`): every change is tested, committed through a lock and pushed in
batches; a privacy scan blocks machine paths and account ids; a game safety
floor limits writes to the autoexec and the game's own video file. Work is
tracked in `ROADMAP.md`.

## License

Apache-2.0 ([LICENSE](LICENSE), [NOTICE](NOTICE)). Not affiliated with Valve.
