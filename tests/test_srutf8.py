import random

from srkit import srutf8


def test_ascii_and_pilcrow_are_single_bytes():
    assert srutf8.encode("A¶B") == b"A\xb6B"
    assert srutf8.decode(b"A\xb6B") == "A¶B"


def test_hangul_never_emits_0xb6():
    # 부(U+BD80)·권(U+AD8C)·삶(U+C0B6): 표준 UTF-8 에 0xB6 이 들어가는 음절
    for ch in "부북분불추출충권삶싶":
        assert 0xB6 in ch.encode("utf-8")
        assert 0xB6 not in srutf8.encode(ch)


def test_roundtrip_all_hangul_syllables():
    text = "".join(chr(c) for c in range(0xAC00, 0xD7A4))
    data = srutf8.encode(text)
    assert 0xB6 not in data
    assert srutf8.decode(data) == text


def test_roundtrip_mixed_text():
    text = "정부 예산: %s¶\\42 북한 — “인용” café 100%"
    assert srutf8.decode(srutf8.encode(text)) == text


def test_cp1252_fallback_for_stock_data():
    assert srutf8.decode("São Paulo".encode("cp1252")) == "São Paulo"
    assert srutf8.decode("Köln, Düsseldorf".encode("cp1252")) == "Köln, Düsseldorf"
    assert srutf8.decode("café".encode("cp1252")) == "café"
    assert srutf8.decode(b"don\x92t") == "don’t"


def test_truncated_tail_is_dropped():
    data = srutf8.encode("가나")
    assert srutf8.decode(data[:-1]) == "가"      # 리드+연속1 로 끝남 → 버림
    assert srutf8.decode(data[:1]) == "ê"         # 한글이 없는 문자열의 리드 단독은 CP1252 문자로 본다


def test_trailing_lead_byte_dropped_only_after_hangul():
    # 게임이 제목을 칸에 맞춰 바이트 단위로 자르면 끝에 리드 바이트만 남는다
    data = srutf8.encode("오신 것을 환영")
    assert srutf8.decode(data[:-2]) == "오신 것을 환"
    assert srutf8.decode("Bogotá".encode("cp1252")) == "Bogotá"      # 원본 이름의 끝 글자는 살린다
    assert srutf8.decode(srutf8.encode("수도: ") + "Bogotá".encode("cp1252") + b" ") == "수도: Bogotá "


def test_measure_single_byte_placeholders():
    data = srutf8.encode("가")
    widths = [srutf8.decode(bytes([b]), measure=True) for b in data]
    assert widths == [chr(srutf8.PH_CELL), chr(srutf8.PH_ZERO), chr(srutf8.PH_ZERO)]
    assert srutf8.decode(b"A", measure=True) == "A"
    assert srutf8.decode(b"\xb6", measure=True) == "¶"
    assert srutf8.decode(b"\xc9", measure=True) == "É"


def test_decode_never_raises_on_random_bytes():
    rng = random.Random(2030)
    for _ in range(2000):
        blob = bytes(rng.randrange(1, 256) for _ in range(rng.randrange(0, 12)))
        srutf8.decode(blob)
        srutf8.decode(blob, measure=True)
