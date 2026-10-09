"""ToyBox: 주소 찾기(새 찾기 = 서명, 옛 찾기 = 치트 닻) · 게임 상태 읽기 · 나라 이름표 (native/srtoybox 의 locate · game · regions)."""
import ctypes
import struct
from ctypes import wintypes

import pytest

import toybox_fake_exe
from toybox_fake_game import INDEX, MODE, MULTIPLAYER, OPTIONS, POINTER, PROGRAM, TABLE, FakeGame
from srkit import toybox

# build 21347933 (게임 12.1.1360, PE TimeDateStamp 0x695377b6) 의 주소. docs/11-game-internals.md 의 표와 같다.
BUILD_21347933 = {"handler": 0x522330, "context": 0x1764310, "multiplayer": 0xF19634, "options": 0x1EB556C,
                  "program_state": 0x1EED11C, "mode_state": 0xE7BE30, "player_index": 0x18294E0, "player_pointer": 0x18295F8,
                  "region_table": 0x1AF78C0, "region_count": 0x18294D8}
BUILD_21347933_STAMP = 0x695377B6
BUILD_STATE = {name: BUILD_21347933[name] for name in toybox.STATE_FIELDS}
BUILD_LEGACY = {name: BUILD_21347933[name] for name in toybox.LEGACY_FIELDS}
BUILD_VALUES = {"world_pointer": 0x1AF5868, "treasury": 0x14B88, "stock_first": 0x14DA4, "stock_step": 0x150,
                "used_first": 0x18, "used_step": 0x84}
GARBAGE = [b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)]
GARBAGE_IDS = ["empty", "two-bytes", "zeros", "header-far-outside"]


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_game_state.argtypes = [ctypes.c_void_p, ctypes.POINTER(toybox.GameAddresses), ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_region_label.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_region_view.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                         ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_dbcs.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint]
    return lib


@pytest.fixture(scope="module")
def sigs(lib):
    """DLL 에 든 서명 표: [(찾을 것, 서명 글)] — 찾을 것마다 셋, 표의 순서대로."""
    return [(row.name, row.text) for row in toybox.state_of(lib, b"")[2]]


@pytest.fixture(scope="module")
def value_sigs(lib):
    """DLL 에 든 값 묶음의 서명 표: [(찾을 것, 서명 글)] — 찾을 것마다 셋, 표의 순서대로."""
    return [(row.name, row.text) for row in toybox.values_of(lib, b"")[2]]


def installed_image(game_dir) -> bytes:
    """설치된 게임의 실행 파일을 펼친 것. 아는 빌드(21347933)가 아니면 건너뛴다."""
    exe = (game_dir / "SupremeRuler2030.exe").read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    if stamp != BUILD_21347933_STAMP:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x})")
    return toybox.image_of(exe)


def test_the_signature_table_has_three_signatures_per_address(sigs):
    assert [name for name, _ in sigs] == [name for name in toybox.STATE_FIELDS for _ in range(3)]
    assert len({text for _, text in sigs}) == 21


def test_state_is_found_in_an_image_without_any_cheat_string(lib, sigs):
    """새 찾기는 치트 문자열에 기대지 않는다 — 게임이 치트를 없애도 상태를 읽는다."""
    image = toybox_fake_exe.sig_image(sigs)
    assert b"cheat" not in image
    found, why, rows = toybox.state_of(lib, image)
    assert found == toybox_fake_exe.STATE, why
    assert [row.count for row in rows] == [1] * 21


@pytest.mark.parametrize("which", range(7))
def test_state_survives_one_broken_signature_per_address(lib, sigs, which):
    """업데이트로 서명 하나가 깨져도 나머지 둘이 같은 주소를 내면 찾은 것이다."""
    found, why, rows = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, broken={3 * which}))
    assert found == toybox_fake_exe.STATE, why
    assert rows[3 * which].count == 0


def test_state_is_not_found_when_two_signatures_of_one_address_break(lib, sigs):
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, broken={0, 1}))
    assert found is None and "멀티플레이 표시" in why and "3개 가운데 1개" in why


def test_a_signature_that_matches_twice_does_not_count(lib, sigs):
    found, why, rows = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, twice={0}))
    assert found == toybox_fake_exe.STATE and rows[0].count == 2, why        # 나머지 둘로 찾는다
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, twice={0}, broken={1}))
    assert found is None and "3개 가운데 1개" in why                          # 두 번 맞은 것은 표가 아니다


def test_signatures_that_disagree_are_refused(lib, sigs):
    """셋이 모두 맞았는데 하나가 다른 주소를 낸다 — 다수결로 고르지 않고 못 찾은 것으로 친다."""
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, stray={12}))
    assert found is None and "플레이어 포인터" in why and "서로 다른 주소" in why


def test_a_state_address_outside_the_image_is_refused(lib, sigs):
    targets = {"region_table": toybox_fake_exe.SIZE - 0x100}      # 지역 표(8바이트 × 1024칸)가 이미지의 끝을 넘는다
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, targets=targets))
    assert found is None and "지역 표" in why and "실행 파일 밖" in why


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_state_survives_garbage(lib, image):
    found, why, _ = toybox.state_of(lib, image)
    assert found is None and why


def test_state_survives_an_image_with_a_page_it_cannot_read(lib, sigs):
    """올라와 있는 실행 파일에 읽을 수 없는 쪽이 있어도(보호된 구역) 죽지 않고 "못 찾았다"로 친다."""
    image = toybox_fake_exe.sig_image(sigs)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    memory = kernel32.VirtualAlloc(None, len(image), 0x3000, 0x04)            # 예약+확정, 읽기 · 쓰기
    ctypes.memmove(memory, image, len(image))
    old = wintypes.DWORD()
    assert kernel32.VirtualProtect(memory + toybox_fake_exe.PLANT, 0x1000, 0x01, ctypes.byref(old))   # 서명이 든 쪽: PAGE_NOACCESS
    found, error = toybox.GameAddresses(), ctypes.create_string_buffer(256)
    try:
        result = lib.srtoybox_locate_state(ctypes.c_char_p(memory), len(image), ctypes.byref(found), error, len(error), None, 0)
    finally:
        kernel32.VirtualFree(memory, 0, 0x8000)
    assert result == -1 and "읽을 수 없는 곳" in error.value.decode("utf-8")


def test_state_on_the_installed_game(lib, game_dir):
    """build 21347933: 서명 21개가 저마다 실행 구역에 정확히 한 번 맞고, 읽어 낸 주소가 docs/11 의 표와 같다."""
    found, why, rows = toybox.state_of(lib, installed_image(game_dir))
    assert found == BUILD_STATE, why
    assert [row.count for row in rows] == [1] * 21
    assert all(row.value == BUILD_STATE[row.name] for row in rows)


def test_signatures_lie_outside_the_cheat_code(lib, game_dir):
    """요구 3: 서명은 치트 코드(명령 처리 함수와, 치트 코드에서만 불리는 함수들)에서 뽑지 않는다."""
    sigmine = pytest.importorskip("srkit.sigmine", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    cheats = sigmine.cheat_ranges(sigmine.Image(image))
    assert len(cheats) == 12
    for row in toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2]:
        assert not any(begin <= row.at < end for begin, end in cheats), row


def test_each_item_takes_its_signatures_from_different_functions(lib, game_dir):
    image = installed_image(game_dir)
    rows = toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2]
    for i in range(0, len(rows), 3):
        roots = {lib.srtoybox_function_root(image, len(image), row.at) or -row.at for row in rows[i:i + 3]}   # 함수 표에 없으면 0
        assert len(roots) == 3, rows[i].name


def test_state_agrees_with_what_the_cheat_code_says(lib, game_dir):
    """치트 코드가 남아 있는 빌드에서의 대조: 새 찾기(서명)의 값 == 2단계의 방식(치트 닻)으로 읽은 값."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    assert toybox.state_of(lib, image)[0] == oracle.state(image)


def test_an_address_outside_the_writable_data_is_refused(lib, sigs, value_sigs):
    """서명들이 서로 맞아도, 읽어 낸 주소가 전역 변수가 있을 수 없는 구역(코드 · 읽기 전용 자료)이면 엉뚱한 것을 읽은 것이다."""
    for target in (toybox_fake_exe.RDATA + 0x100, toybox_fake_exe.TEXT + 0x100):
        found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, targets={"player_index": target}))
        assert found is None and "플레이어 인덱스" in why and "자료 구역" in why, why
        found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, targets={"world_pointer": target}))
        assert found is None and "세계 자료 포인터" in why and "자료 구역" in why, why


def test_state_addresses_that_overlap_are_refused(lib, sigs):
    targets = {"region_count": toybox_fake_exe.STATE["player_pointer"] + 4}     # 지역 수(4바이트)가 플레이어 포인터(8바이트) 안이다
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, targets=targets))
    assert found is None and "지역 수" in why and "겹칩니다" in why, why


def test_the_value_table_has_three_signatures_per_item(lib, value_sigs):
    assert [name for name, _ in value_sigs] == [name for name in ("world_pointer", "treasury", "stock", "used") for _ in range(3)]
    assert len({text for _, text in value_sigs}) == 12
    assert lib.srtoybox_stock_slots() == toybox.STOCK_SLOTS == 12


def test_values_are_found_in_an_image_without_any_cheat_string(lib, value_sigs):
    """값의 자리도 치트 문자열에 기대지 않고 찾는다."""
    image = toybox_fake_exe.sig_image(value_sigs)
    assert b"cheat" not in image
    found, why, rows = toybox.values_of(lib, image)
    assert found == toybox_fake_exe.VALUE_LAYOUT, why
    assert [row.count for row in rows] == [1] * 12
    assert (rows[6].value, rows[6].value2) == (0x20, 0x2000)                    # 재고의 서명은 (간격, 첫 칸)을 함께 읽는다
    assert (rows[9].value, rows[9].value2) == (0x44, 0x28)


@pytest.mark.parametrize("which", range(4))
def test_values_survive_one_broken_signature_per_item(lib, value_sigs, which):
    found, why, rows = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, broken={3 * which + 1}))
    assert found == toybox_fake_exe.VALUE_LAYOUT, why
    assert rows[3 * which + 1].count == 0


def test_values_are_not_found_when_two_signatures_of_one_item_break(lib, value_sigs):
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, broken={3, 4}))
    assert found is None and "국고 칸" in why and "3개 가운데 1개" in why


def test_value_signatures_that_disagree_are_refused(lib, value_sigs):
    """셋이 모두 맞았는데 하나가 다른 자리를 낸다 — 다수결로 고르지 않는다(틀린 칸에 쓰느니 쓰지 않는다)."""
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, stray={7}))
    assert found is None and "재고 칸" in why and "서로 다른 값" in why


@pytest.mark.parametrize("targets, reason", [
    ({"treasury": 0x2040}, "국고 칸과 재고 칸이 겹칩니다"),      # 국고 8바이트가 재고의 셋째 칸(0x2040)을 덮는다
    ({"stock": (0x22, 0x2000)}, "재고 칸"),                     # 간격이 4 의 배수가 아니다
    ({"stock": (0x20, 0x100000)}, "재고 칸"),                   # 자리가 터무니없이 멀다
    ({"used": (0, 0x28)}, "쓰는 물자 표"),                      # 간격이 0
    ({"treasury": 0}, "국고 칸"),                               # 자리가 0
], ids=["overlap", "odd-step", "far", "zero-step", "zero-offset"])
def test_values_that_do_not_add_up_are_refused(lib, value_sigs, targets, reason):
    """서명들이 서로 맞아도 읽어 낸 자리가 말이 안 되면 못 찾은 것이다."""
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, targets=targets))
    assert found is None and reason in why, why


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_values_survive_garbage(lib, image):
    found, why, _ = toybox.values_of(lib, image)
    assert found is None and why


def test_values_on_the_installed_game(lib, game_dir):
    """build 21347933: 값 묶음의 서명 12개가 저마다 실행 구역에 정확히 한 번 맞고, 읽어 낸 값이 docs/11 의 표와 같다."""
    found, why, rows = toybox.values_of(lib, installed_image(game_dir))
    assert found == BUILD_VALUES, why
    assert [row.count for row in rows] == [1] * 12


def test_values_agree_with_what_the_cheat_code_says(lib, game_dir):
    """치트 코드가 남아 있는 빌드에서의 대조: 서명으로 읽은 값 == 치트 treasury · products 의 본문에서 읽은 값. 칸 수도 거기서 센다."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    said = oracle.values(image)
    assert said.pop("slots") == toybox.STOCK_SLOTS
    assert toybox.values_of(lib, image)[0] == said


def test_legacy_finds_the_handler_from_the_cheat_anchor(lib, sigs):
    """옛 찾기(전환 기간): 아직 내장 치트로 도는 기능이 쓰는 셋만 치트 문자열을 닻으로 찾는다."""
    assert toybox.legacy_of(lib, toybox_fake_exe.build(sigs)) == (toybox_fake_exe.LEGACY, "")


@pytest.mark.parametrize("flaw, reason", [
    ("extra_anchor", "닻 문자열"),                   # 같은 문자열이 둘이면 어느 것이 진짜인지 모른다
    ("second_call", "부르는 곳"),                    # 부르는 곳이 둘이면 this 를 어디서 얻을지 모른다
    ("no_options", "치트 허용 비트"),                # 함수 머리의 모양이 다르다 = 다른 함수이거나 바뀐 빌드
    ("outside", "실행 파일 밖"),                     # 찾은 주소가 이미지 밖이다
])
def test_legacy_refuses_an_image_that_does_not_add_up(lib, flaw, reason):
    found, why = toybox.legacy_of(lib, toybox_fake_exe.build(**{flaw: True}))
    assert found is None and reason in why, why


def test_an_image_without_cheats_gives_the_state_but_not_the_handler(lib, sigs):
    """게임이 치트를 없앤 빌드: 상태는 읽고(새 찾기) 명령 처리 함수는 못 찾는다(옛 찾기) — 옮기지 않은 기능만 글쇠 방식이 된다."""
    image = toybox_fake_exe.sig_image(sigs)
    assert toybox.state_of(lib, image)[0] == toybox_fake_exe.STATE
    found, why = toybox.legacy_of(lib, image)
    assert found is None and "닻 문자열" in why


def test_an_image_with_both_gives_both(lib, sigs):
    """치트의 닻과 서명이 함께 든 이미지(지금의 게임): 두 찾기가 서로를 방해하지 않는다."""
    image = toybox_fake_exe.build(sigs)
    assert toybox.state_of(lib, image)[0] == toybox_fake_exe.STATE
    assert toybox.legacy_of(lib, image)[0] == toybox_fake_exe.LEGACY


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_legacy_survives_garbage(lib, image):
    found, why = toybox.legacy_of(lib, image)
    assert found is None and why


def test_legacy_survives_an_image_with_a_page_it_cannot_read(lib):
    image = toybox_fake_exe.build()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    memory = kernel32.VirtualAlloc(None, len(image), 0x3000, 0x04)            # 예약+확정, 읽기 · 쓰기
    ctypes.memmove(memory, image, len(image))
    old = wintypes.DWORD()
    assert kernel32.VirtualProtect(memory + toybox_fake_exe.TEXT, 0x1000, 0x01, ctypes.byref(old))   # 코드의 첫 쪽: PAGE_NOACCESS
    found, error = toybox.GameAddresses(), ctypes.create_string_buffer(256)
    try:
        result = lib.srtoybox_locate_legacy(ctypes.c_char_p(memory), len(image), ctypes.byref(found), error, len(error))
    finally:
        kernel32.VirtualFree(memory, 0, 0x8000)
    assert result == -1 and "읽을 수 없는 곳" in error.value.decode("utf-8")


def test_legacy_on_the_installed_game(lib, game_dir):
    assert toybox.legacy_of(lib, installed_image(game_dir)) == (BUILD_LEGACY, "")


def test_srkit_locate_reports_every_search(lib, cfg, game_dir):
    located = toybox.locate(cfg)
    assert located.state is not None and set(located.state) == set(toybox.STATE_FIELDS), located.state_why
    assert len(located.rows) == 21 and located.ms >= 0
    assert located.values is not None and set(located.values) == set(toybox.VALUE_FIELDS), located.values_why
    assert len(located.value_rows) == 12
    assert located.legacy is not None and set(located.legacy) == set(toybox.LEGACY_FIELDS), located.legacy_why


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


def test_game_state_in_a_lobby_that_already_has_a_player_pointer(lib):
    """캠페인의 로비에서는 메뉴 상태(프로그램 3 / 모드 1)인데 플레이어 포인터가 이미 차 있다(샌드박스의 로비에서는 비어 있다)
    [확인: 실행, build 21347933]. 포인터만 보고 "진행 중"이라고 하면 안 된다 — 게임의 함수는 그때 불러도 되는지 검사하지 않는다."""
    fake = germany()
    fake.poke(PROGRAM, "<i", 3)
    fake.poke(MODE, "<i", 1)
    assert state(lib, fake) == {"known": "1", "in_game": "0", "multiplayer": "0", "cheats": "0", "player": "0", "regions": ""}


def test_game_state_reads_the_cheat_bit_and_the_multiplayer_flag(lib):
    fake = germany()
    fake.poke(OPTIONS, "<I", 0x6072B0C1)
    fake.poke(MULTIPLAYER, "<B", 1)
    got = state(lib, fake)
    assert got["cheats"] == "1" and got["multiplayer"] == "1"
    fake.poke(OPTIONS, "<I", 0x6072B081)            # 비트 0x40 만 꺼진 값(다른 비트는 다른 옵션이다)
    assert state(lib, fake)["cheats"] == "0"


def test_game_state_without_the_legacy_addresses(lib):
    """옛 찾기가 실패하면(치트가 없는 빌드) 옵션 묶음의 주소가 없다(0). 그래도 상태는 읽는다 — 치트 허용만 모르고, 꺼진 것으로 친다."""
    fake = germany()
    fake.at.options = 0
    fake.at.handler = 0
    fake.at.context = 0
    fake.poke(OPTIONS, "<I", 0x40)
    assert state(lib, fake) == {"known": "1", "in_game": "1", "multiplayer": "0", "cheats": "0", "player": "1499",
                                "regions": "1106,1201,1499"}


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
    fake.region(20, 1403, alive=5)                                            # 이번 판에 없는 지역(남독일 같은 것)
    fake.region(21, 2922, alive=5)
    fake.region(22, 7, alive=1)                                               # 유엔 같은 특수한 것
    assert state(lib, fake)["regions"] == "1106,1201,1499"                    # 사람(2)과 AI(3)가 맡은 나라만


def label(lib, number: int) -> str:
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_region_label(number, out, len(out)) >= 0
    return out.value.decode("utf-8")


def test_region_names(lib):
    """이름표는 저장소의 번역 테이블에서 온다. 표에 없는 번호는 #번호 로 보인다."""
    assert label(lib, 1499) == "독일" and label(lib, 1106) == "폴란드"
    assert label(lib, 109) == "수에즈 운하 지대"          # localtext-regions.extra.csv 에만 있는 지역
    assert label(lib, 12345) == "#12345" and label(lib, -7) == "#-7"


def product(lib, slot: int) -> str:
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_product_label(slot, out, len(out)) >= 0
    return out.value.decode("utf-8")


def test_product_names(lib):
    """물자 이름표도 저장소의 번역 테이블에서 온다(재고 칸의 순서 = 게임의 물자 목록의 순서). 표에 없는 칸은 "물자 #칸" 으로 보인다."""
    assert [product(lib, slot) for slot in range(11)] == ["농산물", "고무", "목재", "석유", "석탄", "금속 광석", "우라늄", "전력", "소비재",
                                                           "산업재", "군수품"]
    assert product(lib, 11) == "물자 #11" and product(lib, 12) == "물자 #12" and product(lib, -1) == "물자 #-1"   # 열두째 칸에는 이름이 없다
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_product_names(3, out, len(out)) > 0 and out.value.decode("utf-8") == "석유\tPetroleum"
    assert lib.srtoybox_product_names(11, out, len(out)) == -1


def test_product_rows_come_from_the_translation_table(cfg):
    rows = toybox.product_rows(cfg)
    assert [slot for slot, _, _ in rows] == list(range(11))                  # 같은 목록의 11(전체) · 12(금융) · 13(인구) … 는 물자가 아니다
    assert rows[3] == (3, "석유", "Petroleum") and rows[10] == (10, "군수품", "Military Goods")
    assert toybox.products_inc(rows[:1]) == '{0, "농산물", "Agriculture"},\n'


def test_region_rows_come_from_the_translation_table(cfg):
    rows = toybox.region_rows(cfg)
    assert [n for n, _, _ in rows] == sorted({n for n, _, _ in rows}) and len(rows) > 300
    assert (1499, "독일", "Germany") in rows
    assert (109, "수에즈 운하 지대", "Suez Canal Zone") in rows      # 덧붙인 표(.extra)의 지역도 들어간다
    assert all(ko and en for _, ko, en in rows)


def test_region_table_escapes_names():
    """이름에 따옴표나 역슬래시가 있어도 생성물이 C++ 문자열로 컴파일되어야 한다."""
    assert toybox.c_string('Côte d\'Ivoire') == '"Côte d\'Ivoire"'
    assert toybox.c_string('a"b') == '"a\\"b"'
    assert toybox.c_string("a\\b") == '"a\\\\b"'
    assert toybox.regions_inc([(7, 'x"y', "z\\")]) == '{7, "x\\"y", "z\\\\"},\n'


def view(lib, numbers: list[int], player: int, picked: int, search: str = "") -> tuple[int, list[tuple[int, str]]]:
    """창의 나라 목록: (유지된 선택, [(번호, 이름) …])."""
    out = ctypes.create_string_buffer(1 << 16)
    array = (ctypes.c_int * len(numbers))(*numbers)
    assert lib.srtoybox_region_view(array, len(numbers), player, picked, search.encode("utf-8"), out, len(out)) >= 0
    head, *rows = out.value.decode("utf-8").splitlines()
    return int(head.removeprefix("picked=")), [(int(n), name) for n, name in (row.split("\t") for row in rows)]


GAME = [1106, 1201, 1499, 12345]      # 폴란드, 덴마크, 독일, 이름표에 없는 지역


def test_region_view_lists_this_games_regions(lib):
    """이번 게임에 있는 나라만, 플레이어 자신은 빼고, 한글 이름순으로. 이름표에 없는 번호는 #번호 로 보이고 고를 수 있다."""
    picked, rows = view(lib, GAME, player=1499, picked=12345)
    assert rows == [(12345, "#12345"), (1201, "덴마크"), (1106, "폴란드")]
    assert picked == 12345


def test_region_view_filters_by_name_and_number(lib):
    assert [n for n, _ in view(lib, GAME, 1499, 0, "폴란")[1]] == [1106]
    assert [n for n, _ in view(lib, GAME, 1499, 0, "DEN")[1]] == [1201]            # 영문 이름, 대소문자를 가리지 않는다
    assert [n for n, _ in view(lib, GAME, 1499, 0, "12")[1]] == [12345, 1201]       # 번호의 일부
    assert view(lib, GAME, 1499, 0, "없는이름")[1] == []
    assert view(lib, GAME, 1499, 1106, "덴마")[0] == 1106                           # 검색으로 가려져도 선택은 그대로다


def test_region_view_drops_a_pick_that_is_gone(lib):
    """다른 판을 불러와 고른 나라가 없어졌거나, 그 나라로 플레이하게 됐으면 선택을 지운다."""
    assert view(lib, [1201, 1499], player=1499, picked=1106)[0] == 0
    assert view(lib, GAME, player=1106, picked=1106)[0] == 0
    assert view(lib, [], player=0, picked=1106) == (0, [])


def test_two_byte_characters_are_put_back_together(lib):
    """게임 창은 ANSI 창이라 한글 한 글자가 WM_CHAR 두 번(CP949 의 앞 · 뒤 바이트)으로 온다. 합쳐서 한 글자로 넘긴다."""
    lead, trail = "독".encode("cp949")
    assert lib.srtoybox_dbcs(lead, trail, 949) == ord("독")
    assert lib.srtoybox_dbcs(lead, 0x20, 949) == 0          # 앞 바이트 뒤에 엉뚱한 것이 왔다
    assert lib.srtoybox_dbcs(0x41, 0x42, 949) == 0          # 2바이트 글자가 아니다
