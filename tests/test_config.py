"""config/autoexec.cfg: frame cap under refresh, no cheat-protected cvars."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTO = (ROOT / "config" / "autoexec.cfg").read_text(encoding="ascii")
FORBIDDEN = ("sv_cheats", "r_drawothermodels", "mat_wireframe", "cl_draw_only_deathnotices",
             "host_timescale", "noclip", "god", "bind ")


def _cvars():
    out = {}
    for line in AUTO.splitlines():
        line = line.split("//", 1)[0].strip()
        if line and not line.startswith("echo"):
            k, _, v = line.partition(" ")
            out[k] = v.strip()
    return out


def test_frame_cap_is_three_under_240():
    assert _cvars()["fps_max"] == "237"


def test_no_forbidden_commands():
    low = AUTO.lower()
    for word in FORBIDDEN:
        assert not re.search(r"(^|\n)\s*" + re.escape(word), low), word


def test_every_line_is_a_known_safe_cvar():
    assert set(_cvars()) <= {"con_enable", "fps_max", "fps_max_ui", "rate",
                             "engine_low_latency_sleep_after_client_tick"}
