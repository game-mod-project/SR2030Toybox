"""자동 테스트의 대조용: 2단계가 쓰던 방식(치트 문자열을 닻으로)으로 실행 파일의 이미지에서 상태 전역의 주소를 읽는다.

게임 안에서 도는 DLL 은 이 방식을 쓰지 않는다(docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md 의 요구 3).
치트 코드가 남아 있는 빌드에서 "새 찾기(서명)가 낸 값이 치트 코드에서 읽은 값과 같은가"를 보는 데만 쓴다.
pytest 가 직접 모으는 테스트 파일이 아니다(tests/test_toybox_game.py 가 쓴다).
"""
import re
import struct

from srkit import sigmine

LEA = rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]"     # lea r64,[rip+d]


def _target(data: bytes, at: int, disp: int, length: int) -> int:
    """rip 상대 주소가 든 명령이 가리키는 곳. at: 명령의 시작, disp: 변위의 자리, length: 명령의 길이."""
    return at + length + struct.unpack_from("<i", data, at + disp)[0]


def _uses(image: sigmine.Image, text: str) -> list[int]:
    """그 치트 문자열을 가리키는 lea 의 자리들."""
    string = image.data.find(b"\0" + text.encode() + b"\0") + 1
    assert string > 0, text
    return [lo + m.start() for lo, hi in image.code for m in re.finditer(LEA, image.data[lo:hi])
            if _target(image.data, lo + m.start(), 3, 7) == string]


def _after(image: sigmine.Image, text: str, span: int, pattern: bytes) -> int:
    """그 치트 문자열을 쓰는 자리 뒤 span 바이트 안에서 pattern(정규식)이 처음 맞는 자리."""
    for use in _uses(image, text):
        m = re.search(pattern, image.data[use:use + span], re.S)
        if m:
            return use + m.start()
    raise AssertionError(f"{text}: 서명이 맞지 않는다")


def handler(image_bytes: bytes) -> tuple[int, int]:
    """치트 명령 처리 함수의 [시작, 끝)."""
    found = sigmine.handler_range(sigmine.Image(image_bytes))
    assert found is not None, "치트 문자열이 없는 이미지다"
    return found


def state(image_bytes: bytes) -> dict[str, int]:
    """상태 전역 일곱의 RVA — 치트 코드에서 읽은 것."""
    image = sigmine.Image(image_bytes)
    data = image.data
    begin, _end = handler(image_bytes)
    out = {}
    at = begin + re.search(rb"\x80\x3d....\x00", data[begin:begin + 0x60], re.S).start()        # cmp byte ptr [멀티플레이],0
    out["multiplayer"] = _target(data, at, 2, 7)
    at = _after(image, "cheat georgew", 0x40, rb"\x48\x8b\x05....\xf2\x0f\x10\x80")              # mov rax,[플레이어 포인터]
    out["player_pointer"] = _target(data, at, 3, 7)
    at = _after(image, "cheat populate", 0x40, rb"\x48\x63\x05....\x4c\x8d\x3d....")             # movsxd rax,[인덱스] / lea r15,[월드]
    out["player_index"] = _target(data, at, 3, 7)
    world = _target(data, at + 7, 3, 7)
    m = re.search(rb"\x49\x8b\x8c\xc7", data[at:at + 0x40])                                     # mov rcx,[r15+rax*8+지역 표]
    out["region_table"] = world + struct.unpack_from("<I", data, at + m.start() + 4)[0]
    at = _after(image, "cheat becomeregion", 0x190,
                rb"\x44\x8b\x0d....\x45\x33\xf6\x45\x85\xc9\x0f\x88....\x48\x8d\x0d....")       # mov r9d,[지역 수] … lea rcx,[지역 표]
    out["region_count"] = _target(data, at, 3, 7)
    calls = [lo + m.start() for lo, hi in image.code for m in re.finditer(rb"\xe8", data[lo:hi])
             if _target(data, lo + m.start(), 1, 5) == begin]
    assert len(calls) == 1                                                                      # 명령 처리 함수를 부르는 곳
    caller = image.root(calls[0])
    at = caller + re.search(rb"\x83\x3d....\x06", data[caller:caller + 0x40], re.S).start()     # cmp dword ptr [프로그램 상태],6
    out["program_state"] = _target(data, at, 2, 7)
    enter = [lo + m.start() for lo, hi in image.code
             for m in re.finditer(rb"\xc7\x05....\x02\x00\x00\x00\xc7\x05....\x01\x00\x00\x00", data[lo:hi], re.S)]
    assert len(enter) == 1                                                                      # mov [모드 상태],2 / mov [프로그램 상태],1
    out["mode_state"] = _target(data, enter[0], 2, 10)
    return out
