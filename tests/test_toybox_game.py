"""ToyBox 2단계: 주소 찾기 · 게임 상태 읽기 · 나라 이름표 (native/srtoybox 의 locate · game · regions)."""
import ctypes
import struct

import pytest

import toybox_fake_exe
from toybox_fake_game import INDEX, MULTIPLAYER, OPTIONS, POINTER, TABLE, FakeGame
from srkit import toybox

# build 21347933 (게임 12.1.1360, PE TimeDateStamp 0x695377b6) 의 주소. docs/11-game-internals.md 의 표와 같다.
BUILD_21347933 = {"handler": 0x522330, "context": 0x1764310, "multiplayer": 0xF19634, "options": 0x1EB556C,
                  "program_state": 0x1EED11C, "mode_state": 0xE7BE30, "player_index": 0x18294E0, "player_pointer": 0x18295F8,
                  "region_table": 0x1AF78C0, "region_count": 0x18294D8}
BUILD_21347933_STAMP = 0x695377B6


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_game_state.argtypes = [ctypes.c_void_p, ctypes.POINTER(toybox.GameAddresses), ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_region_label.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return lib


def find(lib, image: bytes) -> tuple[dict[str, int] | None, str]:
    found, error = toybox.GameAddresses(), ctypes.create_string_buffer(256)
    if lib.srtoybox_locate(image, len(image), ctypes.byref(found), error, len(error)) != 0:
        return None, error.value.decode("utf-8")
    return {name: getattr(found, name) for name in toybox.ADDRESS_FIELDS}, ""


def test_locate_finds_every_address_from_the_anchor_string(lib):
    found, why = find(lib, toybox_fake_exe.build())
    assert found == toybox_fake_exe.EXPECTED, why


@pytest.mark.parametrize("flaw, reason", [
    ("extra_anchor", "닻 문자열"),                   # 같은 문자열이 둘이면 어느 것이 진짜인지 모른다
    ("second_call", "부르는 곳"),                    # 부르는 곳이 둘이면 this 를 어디서 얻을지 모른다
    ("no_head_check", "멀티플레이"),                 # 함수 머리의 모양이 다르다 = 다른 함수이거나 바뀐 빌드
    ("other_pointer", "georgeww"),                   # 두 치트가 서로 다른 플레이어 포인터를 쓴다
    ("other_table", "지역 표"),                      # 지역 표의 주소가 두 곳에서 다르다
    ("outside", "실행 파일 밖"),                     # 찾은 주소가 이미지 밖이다
])
def test_locate_refuses_an_image_that_does_not_add_up(lib, flaw, reason):
    """대조가 하나라도 어긋나면 "못 찾았다"다 — 그때 ToyBox 는 1단계의 글쇠 방식으로 동작한다."""
    found, why = find(lib, toybox_fake_exe.build(**{flaw: True}))
    assert found is None and reason in why, why


@pytest.mark.parametrize("image", [b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)],
                         ids=["empty", "two-bytes", "zeros", "header-far-outside"])
def test_locate_survives_garbage(lib, image):
    found, why = find(lib, image)
    assert found is None and why


def test_locate_on_the_installed_game(lib, cfg, game_dir):
    """설치된 게임의 실행 파일에서. 아는 빌드(21347933)면 주소까지 대조하고, 다른 빌드면 찾았는지 못 찾았는지만 적는다."""
    exe = (game_dir / "SupremeRuler2030.exe").read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    found, why = find(lib, toybox.image_of(exe))
    if stamp != BUILD_21347933_STAMP:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x}): " + ("주소를 찾았다" if found else f"못 찾았다 — {why}"))
    assert found == BUILD_21347933, why


def test_srkit_locate_reports_the_addresses(lib, cfg, game_dir):
    found, why = toybox.locate(cfg)
    assert why == "" and found is not None and set(found) == set(toybox.ADDRESS_FIELDS)


def state(lib, fake: FakeGame) -> dict[str, str]:
    out = ctypes.create_string_buffer(8192)
    assert lib.srtoybox_game_state(fake.base, ctypes.byref(fake.at), out, len(out)) >= 0
    return dict(pair.split("=", 1) for pair in out.value.decode().split())


def germany() -> FakeGame:
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임. 폴란드(141, 1106)와 덴마크(150, 1201)가 있다."""
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(150, 1201)
    fake.region(176, 1499)
    fake.play(176)
    return fake


def test_game_state_in_a_game(lib):
    assert state(lib, germany()) == {"known": "1", "in_game": "1", "multiplayer": "0", "cheats": "0", "player": "1499",
                                     "regions": "1106,1201,1499"}


def test_game_state_outside_a_game(lib):
    """메뉴 · 로비: 플레이어 포인터가 비어 있다. 인덱스에 낡은 값이 남아 있어도 진행 중이 아니다."""
    fake = germany()
    fake.menu()
    assert state(lib, fake) == {"known": "1", "in_game": "0", "multiplayer": "0", "cheats": "0", "player": "0", "regions": ""}


def test_game_state_reads_the_cheat_bit_and_the_multiplayer_flag(lib):
    fake = germany()
    fake.poke(OPTIONS, "<I", 0x6072B0C1)
    fake.poke(MULTIPLAYER, "<B", 1)
    got = state(lib, fake)
    assert got["cheats"] == "1" and got["multiplayer"] == "1"
    fake.poke(OPTIONS, "<I", 0x6072B081)            # 비트 0x40 만 꺼진 값(다른 비트는 다른 옵션이다)
    assert state(lib, fake)["cheats"] == "0"


def test_game_state_survives_a_pointer_it_cannot_read(lib):
    """낡은 포인터를 만나도 죽지 않는다. 읽을 수 없으면 모르는 것으로 친다(→ 글쇠 방식)."""
    fake = germany()
    for address in (0x00007FFFFFFF0000, 0x8000000000000000, 8):
        fake.poke(POINTER, "<Q", address)
        fake.poke(TABLE + 8 * 176, "<Q", address)
        assert state(lib, fake)["known"] == "0"


@pytest.mark.parametrize("flaw", ["table", "number", "dead", "index", "self_index"])
def test_game_state_that_does_not_add_up_is_unknown(lib, flaw):
    """게임 안인데 읽은 값이 서로 맞지 않으면 구조가 바뀐 빌드일 수 있다 — 모르는 것으로 친다."""
    fake = germany()
    if flaw == "table":
        fake.poke(TABLE + 8 * 176, "<Q", fake.peek(TABLE + 8 * 141, "<Q"))    # 표[인덱스] 가 플레이어 포인터와 다르다
    elif flaw == "number":
        struct.pack_into("<H", fake.objects[176], 8, 0)                       # 지역 번호가 0
    elif flaw == "dead":
        struct.pack_into("<I", fake.objects[176], 0, 0)                       # 죽은 지역
    elif flaw == "index":
        fake.poke(INDEX, "<i", 2000)                                          # 표 밖의 인덱스
    else:
        struct.pack_into("<H", fake.objects[176], 4, 175)                     # 객체가 아는 자기 인덱스가 다르다
    got = state(lib, fake)
    assert got["known"] == "0" and got["in_game"] == "0"


def test_regions_skip_empty_dead_and_inconsistent_slots(lib):
    fake = germany()
    fake.region(10, 500, alive=0)                                             # 죽은 지역
    fake.region(11, 501)
    struct.pack_into("<H", fake.objects[11], 4, 12)                           # 자기 인덱스가 칸과 다르다
    fake.region(12, 0)                                                        # 번호가 없다
    fake.poke(TABLE + 8 * 13, "<Q", 0x00007FFFFFFF0000)                       # 읽을 수 없는 포인터
    assert state(lib, fake)["regions"] == "1106,1201,1499"


def label(lib, number: int) -> str:
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_region_label(number, out, len(out)) >= 0
    return out.value.decode("utf-8")


def test_region_names(lib):
    """이름표는 저장소의 번역 테이블에서 온다. 표에 없는 번호는 #번호 로 보인다."""
    assert label(lib, 1499) == "독일" and label(lib, 1106) == "폴란드"
    assert label(lib, 12345) == "#12345" and label(lib, 0) == "#0" and label(lib, -7) == "#-7"


def test_region_rows_come_from_the_translation_table(cfg):
    rows = toybox.region_rows(cfg)
    assert [n for n, _, _ in rows] == sorted({n for n, _, _ in rows}) and len(rows) > 300
    assert (1499, "독일", "Germany") in rows
    assert all(ko and en for _, ko, en in rows)


def test_region_table_escapes_names():
    """이름에 따옴표나 역슬래시가 있어도 생성물이 C++ 문자열로 컴파일되어야 한다."""
    assert toybox.c_string('Côte d\'Ivoire') == '"Côte d\'Ivoire"'
    assert toybox.c_string('a"b') == '"a\\"b"'
    assert toybox.c_string("a\\b") == '"a\\\\b"'
    assert toybox.regions_inc([(7, 'x"y', "z\\")]) == '{7, "x\\"y", "z\\\\"},\n'
