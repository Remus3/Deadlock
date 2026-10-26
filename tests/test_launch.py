"""dl_launch: only LaunchOptions inside apps/1422450 changes; nothing is invented."""
import dl_launch as L

VDF = (
    '"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n'
    '\t\t\t\t"apps"\n\t\t\t\t{\n'
    '\t\t\t\t\t"730"\n\t\t\t\t\t{\n\t\t\t\t\t\t"LaunchOptions"\t\t"-other"\n\t\t\t\t\t}\n'
    '\t\t\t\t\t"1422450"\n\t\t\t\t\t{\n\t\t\t\t\t\t"LastPlayed"\t\t"0"\n\t\t\t\t\t}\n'
    '\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n')


def _lines(t):
    return t.splitlines(keepends=True)


def test_finds_the_app_block_not_another_app():
    lines = _lines(VDF)
    s, e = L.find_app_block(lines)
    assert '"1422450"' in lines[s - 1] or '"1422450"' in lines[s]
    assert L.get_option(lines, (s, e)) is None


def test_insert_then_replace_keeps_other_apps():
    lines = _lines(VDF)
    out = L.set_option(lines, L.find_app_block(lines), "+exec autoexec")
    assert L.get_option(out, L.find_app_block(out)) == "+exec autoexec"
    out2 = L.set_option(out, L.find_app_block(out), "-novid +exec autoexec")
    text = "".join(out2)
    assert L.get_option(out2, L.find_app_block(out2)) == "-novid +exec autoexec"
    assert '"LaunchOptions"\t\t"-other"' in text and text.count('"LaunchOptions"') == 2


def test_no_block_is_never_invented():
    assert L.find_app_block(_lines(VDF.replace("1422450", "999"))) is None


def test_wanted_is_one_line():
    assert L.wanted() == "+exec autoexec"
