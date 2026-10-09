"""ToyBox 의 서명(native/srtoybox/sigs): 서명 글 읽기, 실행 구역에서 맞추기, 투표.

게임의 코드를 옮긴 것이 아니다 — 서명이 다루는 명령의 꼴만 작은 버퍼에 놓고 본다.
"""
import ctypes
import struct

import pytest

from srkit import toybox


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_sig_find.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p,
                                      ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return lib


def find(lib, image: bytes, sigs: list[str], begin: int = 0, end: int | None = None, need: int = 2):
    """서명마다 (맞은 횟수, 처음 맞은 자리, 값0, 값1) 또는 "bad". 그리고 투표 (찾았는가, 한 번만 맞은 수, 값0, 값1)."""
    out = ctypes.create_string_buffer(4096)
    assert lib.srtoybox_sig_find(image, len(image), begin, len(image) if end is None else end, "\n".join(sigs).encode(), need,
                                 out, len(out)) >= 0
    lines = out.value.decode().splitlines()
    rows = ["bad" if line == "bad" else tuple(int(x, 16) for x in line.split()) for line in lines[:-1]]
    vote = lines[-1].split()
    assert vote[0] == "vote"
    return rows, (vote[1] == "1", int(vote[2]), int(vote[3], 16), int(vote[4], 16))


def image_with(*pieces: tuple[int, bytes], size: int = 0x400) -> bytes:
    image = bytearray(size)
    for at, data in pieces:
        image[at:at + len(data)] = data
    return bytes(image)


def test_a_signature_reads_an_address_relative_to_the_end_of_its_instruction(lib):
    """rip 상대 거리는 명령의 끝이 기준이다. 거리 뒤에 상수가 붙는 명령은 그만큼 더 뒤가 끝이다."""
    image = image_with(
        (0x40, bytes([0x80, 0x3D]) + struct.pack("<i", 0x150 - 0x47) + bytes([0x00, 0x8B, 0xD8])),   # cmp byte ptr [rip+d],0 / mov ebx,eax
        (0x80, bytes([0x48, 0x8B, 0x05]) + struct.pack("<i", 0x150 - 0x87) + b"\x90"),               # mov rax,[rip+d] / nop
        (0xC0, bytes([0xC7, 0x05]) + struct.pack("<i", 0x150 - 0xCA) + struct.pack("<I", 2)))        # mov dword ptr [rip+d],2
    rows, _ = find(lib, image, ["80 3D [rip+1] 00 8B D8", "48 8B 05 [rip] 90", "C7 05 [rip+4] 02 00 00 00"])
    assert rows == [(1, 0x40, 0x150, 0), (1, 0x80, 0x150, 0), (1, 0xC0, 0x150, 0)]


def test_a_signature_reads_constants(lib):
    """구조체 안의 자리와 간격 같은 상수를 4바이트나 1바이트로 읽는다. 한 서명에서 둘까지. 16진수는 소문자여도 된다."""
    image = image_with(
        (0x100, bytes([0x48, 0x69, 0xC0]) + struct.pack("<I", 0x150) + bytes([0x48, 0x81, 0xC1]) + struct.pack("<I", 0x14DA4)),
        (0x140, bytes([0xF3, 0x0F, 0x10, 0x44, 0x01, 0x18, 0x90])))                                  # movss xmm0,[rcx+rax+18h]
    rows, _ = find(lib, image, ["48 69 C0 [u32] 48 81 C1 [u32]", "f3 0F 10 44 01 [u8] ?"])
    assert rows == [(1, 0x100, 0x150, 0x14DA4), (1, 0x140, 0x18, 0)]


def test_matches_are_counted_and_the_count_stops_at_two(lib):
    piece = bytes([0x48, 0x8B, 0x05, 1, 2, 3, 4, 0x90])
    image = image_with((0x40, piece), (0x80, piece), (0xC0, piece))
    rows, _ = find(lib, image, ["48 8B 05 [rip] 90", "48 8B 05 [rip] 91", "48 8B 05 ? ? ? ? [u8]"])
    assert [row[0] for row in rows] == [2, 0, 2]      # 알고 싶은 것은 "정확히 한 번인가"뿐이다
    assert rows[0][1] == 0x40                         # 처음 맞은 자리


def test_overlapping_matches_are_all_counted(lib):
    rows, _ = find(lib, image_with((0x40, bytes([0xAA, 0xAA, 0xAA, 0x01]))), ["AA AA [u8]"])
    assert rows[0][0] == 2


def test_a_match_must_lie_inside_the_range(lib):
    """서명이 구역의 끝이나 이미지의 끝에 걸치면 맞지 않은 것이다 — 범위 밖을 읽지 않는다."""
    piece = bytes([0x80, 0x3D, 0, 0, 0, 0, 0x00, 0x8B, 0xD8])
    sig = ["80 3D [rip+1] 00 8B D8"]
    image = image_with((0x40, piece))
    assert find(lib, image, sig, begin=0x40, end=0x49)[0][0][0] == 1
    assert find(lib, image, sig, begin=0x40, end=0x48)[0][0][0] == 0        # 끝이 구역 밖이다
    assert find(lib, image, sig, begin=0x41, end=0x100)[0][0][0] == 0       # 시작이 구역 밖이다
    assert find(lib, image, sig, begin=0, end=0x100000)[0][0][0] == 1       # 이미지보다 큰 구역은 이미지에서 잘린다
    at_the_end = image_with((0x400 - 9, piece))
    assert find(lib, at_the_end, sig, end=0x100000)[0][0][0] == 1           # 이미지의 마지막 바이트까지
    cut = image_with((0x400 - 5, piece[:5]))
    assert find(lib, cut, sig, end=0x100000)[0][0][0] == 0                  # 이미지의 끝에서 잘린 꼴


@pytest.mark.parametrize("text", ["", "? 48 [rip]", "48 8B 05", "48 [rip] [rip] [rip]", "48 8 [rip]", "48 [rop]", "48 [RIP]",
                                  " ".join(["90"] * 61) + " [rip]"],
                         ids=["empty", "hole-first", "nothing-to-read", "three-reads", "half-byte", "unknown-word", "upper-case-word",
                              "too-long"])
def test_a_signature_that_is_not_well_formed_is_refused(lib, text):
    rows, vote = find(lib, bytes(0x100), [text])
    assert rows == ["bad"] and vote[0] is False


A, B, C, OTHER, NOWHERE = "48 8B 05 [rip]", "48 8B 0D [rip]", "48 8B 15 [rip]", "48 8B 1D [rip]", "48 8B 3D [rip]"


def vote_image() -> bytes:
    """같은 곳(0x300)을 가리키는 서로 다른 꼴 셋(A · B · C)과, 다른 곳(0x308)을 가리키는 꼴 하나(OTHER)."""
    def mov(at: int, opcode: bytes, target: int) -> tuple[int, bytes]:
        return at, opcode + struct.pack("<i", target - (at + len(opcode) + 4))
    return image_with(mov(0x40, bytes([0x48, 0x8B, 0x05]), 0x300), mov(0x80, bytes([0x48, 0x8B, 0x0D]), 0x300),
                      mov(0xC0, bytes([0x48, 0x8B, 0x15]), 0x300), mov(0x100, bytes([0x48, 0x8B, 0x1D]), 0x308))


def test_the_vote_needs_two_signatures_that_agree(lib):
    image = vote_image()
    assert find(lib, image, [A, B, C])[1] == (True, 3, 0x300, 0)
    assert find(lib, image, [A, B, NOWHERE])[1] == (True, 2, 0x300, 0)        # 하나가 깨져도 된다
    assert find(lib, image, [A, NOWHERE, NOWHERE])[1][:2] == (False, 1)       # 하나만으로는 믿지 않는다
    assert find(lib, image, [A, B, OTHER])[1][:2] == (False, 3)               # 둘이 같아도 하나가 다른 값을 내면 못 찾은 것이다
    assert find(lib, image, [A, OTHER, NOWHERE])[1][:2] == (False, 2)


def test_a_signature_that_matches_twice_has_no_vote(lib):
    """두 번 맞는 서명은 어느 자리가 진짜인지 모른다 — 처음 맞은 자리의 값을 표로 치지 않는다."""
    image = image_with(*[(at, bytes([0x48, 0x8B, 0x05]) + struct.pack("<i", 0x300 - (at + 7))) for at in (0x40, 0x80)],
                       (0xC0, bytes([0x48, 0x8B, 0x0D]) + struct.pack("<i", 0x300 - 0xC7)))
    rows, vote = find(lib, image, [A, B, NOWHERE])
    assert rows[0][0] == 2 and vote[:2] == (False, 1)
