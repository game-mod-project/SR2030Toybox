import numpy as np

from srkit import spritefont as sf


def _tiny_font() -> sf.SpriteFont:
    alpha = np.zeros((8, 8), dtype=np.uint8)
    alpha[1:5, 1:4] = 255
    alpha[1:5, 5:7] = 170
    glyphs = [sf.Glyph(ord("A"), 1, 1, 4, 5, 0.0, 2.0, 1.0), sf.Glyph(ord("B"), 5, 1, 7, 5, 0.0, 2.0, 1.0)]
    return sf.SpriteFont(glyphs, 8.0, ord("A"), alpha)


def test_dump_load_roundtrip(tmp_path):
    font = _tiny_font()
    path = tmp_path / "t.spritefont"
    sf.save(font, path)
    back = sf.load(path)
    assert back.glyphs == font.glyphs
    assert back.line_spacing == font.line_spacing and back.default_char == font.default_char
    assert np.array_equal(back.alpha, font.alpha)


def test_augment_keeps_existing_pixels_and_adds_new():
    font = _tiny_font()
    extra = sf.NewGlyph(0xAC00, np.full((6, 6), 255, np.uint8), 1.0, 1.0, 1.0)
    out = sf.augment(font, [extra, sf.blank_glyph(0xE000, 7.0)])
    assert [g.char for g in out.glyphs] == sorted(g.char for g in out.glyphs)
    assert np.array_equal(out.bitmap(out.find(ord("A"))), font.bitmap(font.find(ord("A"))))
    assert out.bitmap(out.find(0xAC00)).shape == (6, 6)
    cell = out.find(0xE000)
    assert cell.width + cell.xadv == 7.0 and not out.bitmap(cell).any()
    assert out.alpha.shape[0] % 4 == 0 and out.alpha.shape[1] % 4 == 0
    assert sf.dumps(out)[:8] == sf.MAGIC


def test_game_fonts_reserialize_byte_exact(game_dir):
    """원본 글꼴을 읽어 다시 쓰면 바이트가 같아야 한다(BC2 코덱 검증).

    일부 원본은 stride*rows 뒤에 쓰이지 않는 투명 블록이 더 붙어 있어, 의미 있는 앞부분만 비교한다.
    """
    fonts = sorted((game_dir / "Localize" / "LOCALEN" / "Fonts").glob("*.spritefont"))
    assert len(fonts) >= 39
    for path in fonts:
        mine, orig = sf.dumps(sf.load(path)), path.read_bytes()
        assert mine == orig[:len(mine)], path.name
