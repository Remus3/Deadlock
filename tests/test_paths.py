"""dl_paths: library parsing and install discovery on a fake Steam tree."""
import dl_paths


def test_library_paths_unescape():
    bs = chr(92)
    vdf = '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"D:%sGames%sSteam"\n\t}\n}\n' % (bs * 2, bs * 2)
    assert dl_paths.library_paths(vdf) == ["D:" + bs + "Games" + bs + "Steam"]


def test_find_install_in_second_library(tmp_path):
    steam, lib = tmp_path / "steam", tmp_path / "lib2"
    (steam / "steamapps").mkdir(parents=True)
    (lib / "steamapps" / "common" / "Deadlock").mkdir(parents=True)
    (lib / "steamapps" / "appmanifest_1422450.acf").write_text("x", encoding="ascii")
    esc = str(lib).replace("\\", "\\\\")
    (steam / "steamapps" / "libraryfolders.vdf").write_text(
        '"libraryfolders"\n{\n"1"\n{\n"path"\t\t"%s"\n}\n}\n' % esc, encoding="ascii")
    got_lib, game = dl_paths.find_install(steam)
    assert got_lib == lib and game == lib / "steamapps" / "common" / "Deadlock"


def test_missing_install(tmp_path):
    assert dl_paths.find_install(tmp_path) == (None, None)


def test_redact_hides_real_prefixes(tmp_path):
    steam = str(tmp_path / "s")
    game = steam + "/steamapps/common/Deadlock"
    doc = dl_paths.redact({"steam": steam, "game": game, "cfg": game + "/game/citadel/cfg",
                           "video": [game + "/v.txt"]})
    assert doc["steam"] == "<Steam>" and doc["game"] == "<Deadlock>"
    assert doc["cfg"].startswith("<Deadlock>") and doc["video"][0].startswith("<Deadlock>")
