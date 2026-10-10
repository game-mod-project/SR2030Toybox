"""자동 테스트의 대조용: 2단계가 쓰던 방식(치트 문자열을 닻으로)으로 실행 파일의 이미지에서 상태 전역의 주소와 값의 자리를 읽는다.

게임 안에서 도는 DLL 은 이 방식을 쓰지 않는다(docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md 의 요구 3).
치트 코드가 남아 있는 빌드에서 "새 찾기(서명)가 낸 값이 치트 코드에서 읽은 값과 같은가"를 보는 데만 쓴다.
(3단계 2 의 "더 쓰는 값"은 치트 finalexam · shelovesme · love · neutral 의 본문과, 3단계 3 의 연구는 치트 technology 의 본문과 댄다.)
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


def values(image_bytes: bytes) -> dict[str, int]:
    """값 묶음(세계 자료 포인터, 국고 칸, 재고와 "쓰는 물자"의 첫 칸 · 간격)과 재고의 칸 수(slots) — 치트 treasury · products 의 본문에서 읽은 것."""
    image = sigmine.Image(image_bytes)
    data = image.data
    out = {}
    at = _after(image, "cheat treasury", 0x80, rb"\xf2\x0f\x58\x80....\xf2\x0f\x11\x80")        # addsd xmm0,[rax+국고] / movsd [rax+국고],xmm0
    out["treasury"] = struct.unpack_from("<I", data, at + 4)[0]
    use = _uses(image, "cheat products")[0]
    skip = re.search(rb"\x0f\x84(....)", data[use:use + 0x20], re.S)                             # je <다음 치트> — 거기까지가 본문이다
    body = data[use:use + skip.start() + 6 + struct.unpack("<i", skip.group(1))[0]]
    first = re.search(rb"\x48\x8b\x05....\x4c\x8d\x3d....\xf3\x0f\x10\x40(.)", body, re.S)       # mov rax,[세계 자료] / lea r15,[월드] / movss xmm0,[rax+첫 칸]
    out["world_pointer"] = _target(data, use + first.start(), 3, 7)
    used = [first.group(1)[0]] + [struct.unpack("<I", d)[0] for d in re.findall(rb"\xf3\x0f\x10\x80(....)\x0f\x2f\xc2", body, re.S)]
    stock = [struct.unpack("<I", d)[0]                                                           # addss xmm,[rcx+칸] / movss [rcx+칸],xmm
             for d in re.findall(rb"\xf3\x0f\x58[\x81\x89](....)\xf3\x0f\x11[\x81\x89]", body, re.S)]
    out["used_first"], out["used_step"] = used[0], used[1] - used[0]
    out["stock_first"], out["stock_step"] = stock[0], stock[1] - stock[0]
    assert used == [out["used_first"] + out["used_step"] * i for i in range(len(used))], used    # 물자마다 펼쳐 놓았다 — 간격이 고르다
    assert stock == [out["stock_first"] + out["stock_step"] * i for i in range(len(stock))], stock
    assert len(used) == len(stock), (len(used), len(stock))
    out["slots"] = len(stock)
    return out


def _body(image: sigmine.Image, text: str) -> bytes:
    """그 치트의 본문: 치트 문자열을 쓰는 자리부터, 글이 다를 때 건너뛰는 곳(다음 치트)까지."""
    use = _uses(image, text)[0]
    skip = re.search(rb"\x85\xc0(?:\x0f\x84(....)|\x75(.))", image.data[use:use + 0x20], re.S)     # test eax,eax / je(먼) · jne(가까운) <다음 치트>
    jump = struct.unpack("<i", skip.group(1))[0] if skip.group(1) is not None else struct.unpack("<b", skip.group(2))[0]
    return image.data[use:use + skip.end() + jump]


def _relation_writes(body: bytes) -> dict[str, list[int]]:
    """love · neutral 의 본문이 쓰는 칸(표의 첫 칸): 플레이어 객체 쪽(mine)과 그 나라 객체 쪽(theirs), 1.0 을 쓰는 것과 0 을 쓰는 것."""
    def found(pattern: bytes) -> list[int]:
        return sorted(struct.unpack("<I", d)[0] for d in re.findall(pattern, body, re.S))

    return {"mine_one": found(rb"\xc7\x84\x88(....)\x00\x00\x80\x3f"),                          # mov dword ptr [rax+rcx*4+표],1.0
            "mine_zero": found(rb"\x44\x89\xb4\x88(....)"),                                      # mov [rax+rcx*4+표],r14d (0)
            "theirs_one": found(rb"\xc7\x84\x82(....)\x00\x00\x80\x3f"),                        # mov dword ptr [rdx+rax*4+표],1.0
            "theirs_zero": found(rb"\x44\x89\xb4\x82(....)")}                                    # mov [rdx+rax*4+표],r14d


def more(image_bytes: bytes) -> dict[str, int]:
    """더 쓰는 값의 자리 일곱 — 치트 finalexam · shelovesme · love 의 본문에서 읽은 것. neutral 이 love 와 같은 여섯 칸을 쓰는지도 본다."""
    image = sigmine.Image(image_bytes)
    data = image.data
    out = {}
    at = _after(image, "cheat finalexam", 0x40,
                rb"\xf3\x0f\x10\x80(....)\xf3\x0f\x58\x05....\xf3\x0f\x11\x80\1")              # movss xmm0,[rax+칸] / addss xmm0,[1.0] / movss [rax+칸],xmm0
    out["tech"] = struct.unpack_from("<I", data, at + 4)[0]
    cells = sorted(struct.unpack("<I", d)[0]                                                    # mov dword ptr [rax+칸],1.0 셋
                   for d in re.findall(rb"\xc7\x80(....)\x00\x00\x80\x3f", _body(image, "cheat shelovesme"), re.S))
    assert len(cells) == 3, cells
    out["opinion0"], out["opinion1"], out["opinion2"] = cells
    love, neutral = _relation_writes(_body(image, "cheat love")), _relation_writes(_body(image, "cheat neutral"))
    assert love["mine_one"] == love["theirs_one"] and len(love["mine_one"]) == 2, love          # 관계 표 둘에 1.0 — 양쪽 객체에
    assert love["mine_zero"] == love["theirs_zero"] and len(love["mine_zero"]) == 1, love       # 전쟁 명분 표에 0
    six = sorted(love["mine_one"] + love["mine_zero"])
    assert neutral == {"mine_one": [], "mine_zero": six, "theirs_one": [], "theirs_zero": six}, neutral   # 중립은 같은 칸들에 0
    out["relation0"], out["relation1"] = love["mine_one"]
    out["casus"] = love["mine_zero"][0]
    return out


def research(image_bytes: bytes) -> dict[str, int]:
    """연구 묶음 가운데 치트 technology 의 본문에서 읽을 수 있는 것: 세계 객체 · 기술 수 · 기술 표 · 연구 목록의 자리 · 다시 셈 함수,
    그리고 꼴의 상수(tech_size · tech_level · tech_owners · owners_bytes · node_kind · node_id · node_next).
    부대 설계의 표는 이 치트가 건드리지 않는다 — 여기에 없다."""
    image = sigmine.Image(image_bytes)
    data = image.data
    use = _uses(image, "cheat technology")[0]
    body = _body(image, "cheat technology")

    def find(pattern: bytes) -> re.Match:
        m = re.search(pattern, body, re.S)
        assert m is not None, pattern
        return m

    out = {}
    m = find(rb"\x4c\x8d\x3d....\x44\x39\x35....")                          # lea r15,[세계 객체] / cmp [기술 수],r14d
    out["world"] = _target(data, use + m.start(), 3, 7)
    out["tech_count"] = _target(data, use + m.start() + 7, 3, 7)
    m = find(rb"\x48\x8d\x0c\x52\x49\x8b\x94\xcf(....)")                    # lea rcx,[rdx+rdx*2] / mov rdx,[r15+rcx*8+연구 목록]
    out["lists"] = struct.unpack("<I", m.group(1))[0]
    m = find(rb"\x80\x7f(.)\x01\x75.\x44\x3b\x77(.)")                       # cmp byte ptr [rdi+종류],1 / jne / cmp r14d,[rdi+번호]
    out["node_kind"], out["node_id"] = m.group(1)[0], m.group(2)[0]
    out["node_next"] = find(rb"\x48\x8b\x40(.)\x48\x8b\xf8").group(1)[0]     # mov rax,[rax+다음] / mov rdi,rax
    m = find(rb"\x48\x8b\x0d....\x41\x0f\xb6\x44\x0c(.)")                    # mov rcx,[기술 표] / movzx eax,byte ptr [r12+rcx+수준]
    out["tech_table"] = _target(data, use + m.start(), 3, 7)
    out["tech_level"] = m.group(1)[0]
    out["tech_owners"] = find(rb"\x48\x8d\x79(.)\x49\x03\xfc").group(1)[0]   # lea rdi,[rcx+보유 묶음] / add rdi,r12
    out["owners_bytes"] = struct.unpack("<I", find(rb"\xb9(....)\xe8....\x4c\x8b\xc8").group(1))[0]   # mov ecx,묶음의 크기 / call / mov r9,rax
    out["tech_size"] = struct.unpack("<I", find(rb"\x49\x81\xc4(....)").group(1))[0]                  # add r12,레코드의 크기
    m = find(rb"\xba\xff\xff\xff\xff\x49\x8b\xcf\xe8....")                  # mov edx,-1 / mov rcx,r15 / call 다시 셈
    out["recompute"] = _target(data, use + m.start() + 8, 1, 5)
    return out
