from pathlib import Path


ROOT = Path(__file__).parent / "static" / "dadada-millionaire"


def test_dadada_game_assets_are_complete():
    required = (
        "index.html",
        "style.css",
        "game.js",
        "manifest.json",
        "assets/icon.svg",
        "assets/city-progression.jpg",
    )
    for relative_path in required:
        assert (ROOT / relative_path).is_file(), relative_path


def test_dadada_game_has_complete_core_loop_and_storage():
    html = (ROOT / "index.html").read_text()
    script = (ROOT / "game.js").read_text()

    for screen in ("business", "property", "market", "life", "record"):
        assert f'id="{screen}"' in html
    assert "localStorage.setItem" in script
    assert "offlineCash" in script
    assert "function tap(" in script
    assert "function invest(" in script
    assert "setInterval(save" in script


def test_dadada_game_is_responsive_and_lightweight():
    css = (ROOT / "style.css").read_text()
    assert "@media(min-width:720px)" in css
    assert "@media(max-width:420px)" in css
    assert not list(ROOT.rglob("*.mp4"))
    assert (ROOT / "assets" / "city-progression.jpg").stat().st_size < 1_000_000
