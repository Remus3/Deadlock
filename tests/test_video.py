"""vw_video: changes only keys already present; reads values back."""
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
