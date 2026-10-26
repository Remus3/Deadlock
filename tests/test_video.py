"""vw_video: changes only keys already present; reads values back."""
import json

import pytest

import vw_video as V

FILE = ('"video.cfg"\n{\n\t"setting.defaultres"\t\t"1920"\n\t"setting.mat_vsync"\t\t"1"\n'
        '\t"setting.other"\t\t"5"\n}\n')


def test_patch_changes_present_keys_only():
    new, changed = V.patch(FILE, {"setting.defaultres": "2560", "setting.mat_vsync": "0",
                                  "setting.absent": "1"})
    assert changed == {"setting.defaultres": ("1920", "2560"), "setting.mat_vsync": ("1", "0")}
    assert "setting.absent" not in new and '"setting.other"\t\t"5"' in new
    assert V.read_values(new, {"setting.defaultres"}) == {"setting.defaultres": "2560"}


def test_patch_is_idempotent_and_keeps_crlf():
    crlf = FILE.replace("\n", "\r\n")
    once, _ = V.patch(crlf, {"setting.defaultres": "2560"})
    twice, changed = V.patch(once, {"setting.defaultres": "2560"})
    assert changed == {} and once == twice and once.count("\r\n") == crlf.count("\r\n")


def test_recommended_keys_target_the_display():
    k = V.recommended_keys()
    assert (k["setting.defaultres"], k["setting.defaultresheight"]) == ("2560", "1440")
    assert k["setting.refreshrate_numerator"] == "240" and k["setting.mat_vsync"] == "0"


def test_recommended_latency_and_clarity_keys():
    k = V.recommended_keys()
    assert k["setting.r_low_latency"] == "2"
    assert k["setting.fullscreen"] == "1" and k["setting.nowindowborder"] == "0"
    for key in ("setting.r_depth_of_field", "setting.r_effects_bloom", "setting.r_post_bloom"):
        assert k[key] == "false"


def test_menu_transcript_keys():
    k = V.recommended_keys()
    assert k["setting.r_citadel_shadow_quality"] == "1"  # Med, confirmed by diff
    assert k["setting.r_citadel_fog_quality"] == "0" and k["setting.r_arealights"] == "false"
    assert not V.MENU_ONLY.intersection(k)


def test_menu_has_no_particle_or_aa_control():
    menu = json.loads(V.RECOMMENDED.read_text(encoding="ascii"))["menu"]
    for label in menu:
        assert "particle" not in label.lower() and "anti-aliasing" not in label.lower(), label
    assert menu["Display > Window mode"].startswith("Fullscreen")


def test_menu_only_key_refused(tmp_path):
    f = tmp_path / "rec.json"
    f.write_text(json.dumps({"keys": {"setting.r_citadel_upscaling": "0"}}), encoding="ascii")
    with pytest.raises(ValueError):
        V.recommended_keys(f)
