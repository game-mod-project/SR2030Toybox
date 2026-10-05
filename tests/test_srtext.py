from srkit import srtext

SAMPLE = (
    "\n\r\n\r\n// OUTPUT - 4\n"
    "&&ORDERSTEXT, 0\n"
    '0, "IDLE"\n'
    '1, "MOVE TO"\n'
    "&&END\n"
    "\n"
    "&&TIPOFDAYTEXT, 0\n"
    '1, 300.000, 1.000, "Fuel Capacity", "Amount of fuel remaining."\n'
    '100, "", "", "Game speed", "Paused. See http://x//y", ""\n'
    '100, "", "", "Duplicate id", "second"\n'
    "&&END\n"
)

GUI = '// header\n&&GUITRANS\n"# Cities", "# Städte", \n"Accept", "Akzeptieren", \n'


def test_roundtrip_is_lossless():
    assert srtext.parse(SAMPLE).serialize() == SAMPLE
    assert srtext.parse(GUI).serialize() == GUI


def test_units_have_stable_keys():
    units = {u.key: u.text for u in srtext.parse(SAMPLE).units()}
    assert units["ORDERSTEXT|0|0"] == "IDLE"
    assert units["TIPOFDAYTEXT|1|1"] == "Amount of fuel remaining."
    assert units["TIPOFDAYTEXT|100|2"] == "Game speed"        # 빈 문자열도 순번에는 포함
    assert units["TIPOFDAYTEXT|100#2|2"] == "Duplicate id"    # 중복 행 키
    assert "TIPOFDAYTEXT|100|0" not in units                  # 빈 문자열은 번역 단위가 아님


def test_directives_inside_sections_are_not_units():
    doc = srtext.parse('&&REGIONTEXT\n801,,"Briefing"\n#include "LocalText-RegionsGC.csv", "SCENARIO\\"\n')
    assert [u.key for u in doc.units()] == ["REGIONTEXT|801|0"]


def test_guitrans_key_is_english_source():
    units = {u.key: u.text for u in srtext.parse(GUI).units()}
    assert units["GUITRANS|# Cities|0"] == "# Cities"
    assert units["GUITRANS|# Cities|1"] == "# Städte"


def test_apply_replaces_only_target_strings():
    doc = srtext.parse(SAMPLE)
    assert doc.apply({"ORDERSTEXT|1|0": "이동", "NOPE|1|0": "x"}) == 1
    out = doc.serialize()
    assert '1, "이동"\n' in out
    assert out.replace("이동", "MOVE TO") == SAMPLE


def test_apply_rejects_double_quote():
    doc = srtext.parse(SAMPLE)
    try:
        doc.apply({"ORDERSTEXT|1|0": '이"동'})
    except ValueError:
        return
    raise AssertionError("큰따옴표가 든 번역문은 거부해야 한다")


def test_tokens_keep_order_and_code_width():
    assert srtext.tokens(r"\42 %s has %.1f%% of %d¶next") == ["\\42 ", "%s", "%.1f", "%%", "%d", "¶"]
    assert srtext.tokens(r"\LEF %s : %s") == ["\\LEF", "%s", "%s"]
    assert srtext.tokens("\\42독일") == []          # 공백이 빠진 코드는 코드로 치지 않는다 → 원문과 불일치로 잡힌다
    assert srtext.tokens("%d of %s") != srtext.tokens("%s 중 %d")
    assert srtext.tokens("at 50% discount, % condition") == []   # 퍼센트 뒤 공백은 서식이 아니다


def test_game_files_roundtrip(game_dir):
    """모든 언어의 현지화 텍스트가 바이트 단위로 왕복되는지 확인."""
    checked = 0
    for path in (game_dir / "Localize").glob("LOCAL*/*"):
        if path.suffix.lower() not in (".csv", ".ini"):
            continue
        raw = path.read_bytes()
        text = raw.decode("latin-1")  # 바이트 보존용
        assert srtext.parse(text).serialize().encode("latin-1") == raw, path
        checked += 1
    assert checked > 40
