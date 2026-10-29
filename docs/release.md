# Release versioning

Operator order 2026-10-29: "the release versioning should not go 0.2.3 to
0.4.99 in one run when it could have been appropriately handled as 0.2.4 but
also not being so strict that it can only happen at x time or after x days."

Follows the fleet convention seen in sibling trees (EW, CS, RSC): SemVer 0.x,
annotated tags `v0.MINOR.PATCH`.

## Rules

1. SemVer pre-1.0: `v0.MINOR.PATCH`. 1.0.0 is an operator call, not a bump.
2. A release bumps exactly ONE step from the last released tag. From 0.M.P the
   only legal next versions are 0.M.(P+1) and 0.(M+1).0. The first release is
   0.1.0 (or 0.0.1).
3. The step size follows the largest change in the batch:
   - patch: fixes, docs, internal or test-only changes;
   - minor: a user-visible feature, or a breaking config change.
   Never more than one step per release, whatever the batch holds.
4. Several commits in one run are batched into a single release, so the
   version never jumps across steps (0.2.3 -> 0.2.4, not 0.2.3 -> 0.4.99).
5. No time or day gate: a release is cut whenever a coherent, gate-green batch
   is pushed (the /done push, per CLAUDE.md push policy).
6. The tagged commit is an ancestor of the pushed `origin/main`; push the single
   tag ref only (`git push origin refs/tags/v0.X.Y` through fleet_gitlock),
   never `--tags`.

## Check

    python tools/vw_release.py latest
    python tools/vw_release.py check 0.2.4

`check` exits 1 with `REFUSED:` for any version that is not exactly one patch
or minor step from the latest tag. Guard: `tests/test_release.py`.
