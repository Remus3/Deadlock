"""DL test root: installs the fleet kit test guard (FLEET-COMMON 16 d).

A suite that changes live state (ops/loop/control, the inbox, the outbox)
fails; runtime roots would point at tmp_path (none are declared yet).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "fleet_kit"))
sys.path.insert(0, str(ROOT / "tools"))

import fleet_test_guard  # noqa: E402

fleet_test_guard.install(globals(), root=ROOT, env_roots={})
