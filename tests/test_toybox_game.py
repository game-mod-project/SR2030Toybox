"""ToyBox 2단계: 주소 찾기 · 게임 상태 읽기 · 나라 이름표 (native/srtoybox 의 locate · game · regions)."""
import ctypes
import struct

import pytest

import toybox_fake_exe
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
    return toybox.library(cfg)


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
