import random

import pytest

from srkit import srutf8


def test_ascii_and_pilcrow_are_single_bytes():
    assert srutf8.encode("A¶B") == b"A\xb6B"
    assert srutf8.decode(b"A\xb6B") == "A¶B"


def test_hangul_never_emits_0xb6():
    # 부(U+BD80)·권(U+AD8C)·삶(U+C0B6): 표준 UTF-8 에 0xB6 이 들어가는 음절
    for ch in "부북분불추출충권삶싶":
        assert 0xB6 in ch.encode("utf-8")
        assert 0xB6 not in srutf8.encode(ch)
    assert srutf8.encode("독일") == b"\xe6\x8f\x85\xec\x9d\xbc"      # 독: EB 8F 85 → 선두 E6, 일: EC 그대로
    assert srutf8.encode("우") == b"\xec\xf7\xb0"                    # 우: EC 9A B0 → 연속 9A 는 F7


def test_roundtrip_all_hangul_syllables():
    text = "".join(chr(c) for c in range(0xAC00, 0xD7A4))
    data = srutf8.encode(text)
    assert 0xB6 not in data
    assert srutf8.decode(data) == text


# 게임이 지도 라벨에 쓰는 대문자화(빌드 21347933, RVA 0x697c25 / 0x6984c9 의 표 그대로)
GAME_UPPER = {0x9A: 0x8A, 0x9E: 0x8E, 0xE1: 0xC1, 0xE2: 0xC2, 0xE4: 0xC4, 0xE7: 0xC7, 0xE9: 0xC9, 0xEA: 0xCA, 0xEB: 0xCB,
              0xED: 0xCD, 0xEE: 0xD8, 0xF1: 0xD1, 0xF3: 0xD3, 0xF4: 0xD4, 0xF6: 0xD6, 0xFA: 0xDA, 0xFC: 0xDC, 0xFD: 0xDD}


def game_upper(data: bytes) -> bytes:
    return bytes(b - 32 if 0x61 <= b <= 0x7A else GAME_UPPER.get(b, b) for b in data)


def test_survives_the_games_uppercasing():
    """지도를 축소하면 나라 이름이 대문자화된다. 한글 바이트가 그 표에 걸리면 '독일' 이 '**일' 로 깨진다(실제로 그랬다)."""
    hangul = "".join(chr(c) for c in range(0xAC00, 0xD7A4))
    data = srutf8.encode(hangul)
    assert game_upper(data) == data                      # 한글은 한 바이트도 바뀌지 않는다
    assert srutf8.decode(game_upper(srutf8.encode("독일 프랑스 영국 아일랜드 우크라이나 일본"))) == "독일 프랑스 영국 아일랜드 우크라이나 일본"
    assert srutf8.decode(game_upper(srutf8.encode("서독 (west) · 2030"))) == "서독 (WEST) · 2030"
    assert srutf8.decode(game_upper("München, Köln".encode("cp1252"))) == "MÜNCHEN, KÖLN"   # 원본 데이터는 원래대로


def test_reads_bytes_written_before_the_remap():
    """이전 빌드가 쓴 바이트(표준 UTF-8 선두 바이트, 연속 바이트 9A·9E 그대로)도 읽는다."""
    for ch in "독일프랑우자":
        old = bytes(0xFF if b == 0xB6 and i else b for i, b in enumerate(ch.encode("utf-8")))
        assert srutf8.decode(old) == ch


def test_unsupported_characters_are_reported():
    """바꿔 쓴 선두 바이트(E0·E5·E6·E8) 자리의 원래 문자는 쓸 수 없다: 한자의 일부가 여기에 든다."""
    assert srutf8.unsupported("성일(聖日)") == ["日", "聖"]        # U+65E5(선두 E6), U+8056(선두 E8)
    assert srutf8.unsupported("北") == ["北"]                      # U+5317(선두 E5)
    assert srutf8.unsupported("한글 café “인용” ㄱ · 해외 도(道)") == []   # U+9053 은 선두 E9 라 쓸 수 있다
    with pytest.raises(ValueError):
        srutf8.encode("聖")


def test_roundtrip_mixed_text():
    text = "정부 예산: %s¶\\42 북한 — “인용” café 100% ㄱㄴ · 道"
    assert srutf8.decode(srutf8.encode(text)) == text


def test_cp1252_fallback_for_stock_data():
    assert srutf8.decode("São Paulo".encode("cp1252")) == "São Paulo"
    assert srutf8.decode("Köln, Düsseldorf".encode("cp1252")) == "Köln, Düsseldorf"
    assert srutf8.decode("café".encode("cp1252")) == "café"
    assert srutf8.decode(b"don\x92t") == "don’t"


def test_truncated_tail_is_dropped():
    data = srutf8.encode("가나")
    assert srutf8.decode(data[:-1]) == "가"      # 리드+연속1 로 끝남 → 버림
    assert srutf8.decode(data[:1]) == "å"         # 한글이 없는 문자열의 리드 단독(0xE5)은 CP1252 문자로 본다


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
