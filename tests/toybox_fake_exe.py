"""주소 찾기(native/srtoybox/locate.cpp) 테스트용: 작은 가짜 실행 파일 이미지(RVA 대로 펼친 것).

게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다 — 상태 묶음, 값 묶음, 더 쓰는 값, 연구)과, 옛 찾기가 보는
닻(치트 문자열)과 명령의 바이트 꼴만 같은 자리 관계로 놓았다. pytest 가 직접 모으는 테스트 파일이 아니다.
"""
import re
import struct

SIZE = 0x10000                                # 지역 표(8바이트 × 1024칸)와 그 뒤의 연구 목록(24바이트 × 1024칸)이 들어갈 만큼
TEXT, RDATA, PDATA, DATA = 0x1000, 0x3000, 0x4000, 0x5000
HANDLER, CALLER = 0x1000, 0x1800
RECOMPUTE = TEXT + 0xC00                      # 가짜 "다시 셈 함수" — 함수 표에 그 시작으로 들어 있다
WORLD = DATA + 0x180                          # 지역 표 = WORLD + 0x80
ANCHOR = RDATA                                # "cheat allowcheats"
# 새 찾기(상태 묶음)의 가짜 주소
STATE = {"multiplayer": DATA, "program_state": DATA + 8, "mode_state": DATA + 12, "player_index": DATA + 16,
         "player_pointer": DATA + 24, "region_table": WORLD + 0x80, "region_count": DATA + 20}
# 옛 찾기(치트 닻)의 가짜 주소
LEGACY = {"handler": HANDLER, "context": DATA + 0x100, "options": DATA + 4}
# 새 찾기(값 묶음)의 가짜 값: 서명의 이름 → 읽어 낼 것. 둘을 읽는 서명은 (간격, 첫 칸).
# 진짜 게임의 값과 다르게 뒀다 — 코드에 박아 둔 값으로는 통과하지 못한다
VALUES = {"world_pointer": DATA + 0x40, "treasury": 0x1230, "stock": (0x20, 0x2000), "used": (0x44, 0x28)}
VALUE_LAYOUT = {"world_pointer": DATA + 0x40, "treasury": 0x1230, "stock_first": 0x2000, "stock_step": 0x20,
                "used_first": 0x28, "used_step": 0x44}
# 새 찾기(더 쓰는 값)의 가짜 자리 — 지역 객체 안의 자리다(이미지 안이 아니다). 표 셋은 저마다 0x1000(4바이트 × 1024칸)을 차지한다
MORE = {"tech": 0x3120, "opinion0": 0x3004, "opinion1": 0x3008, "opinion2": 0x3020, "relation0": 0x4000, "relation1": 0x5000,
        "casus": 0x6000}
# 새 찾기(연구)의 가짜 값. 세계 객체의 서명은 (주소, 지역 표까지의 거리)를 함께 읽는다. 연구 목록은 세계 객체 안의 자리다 —
# 지역 표(WORLD + 0x80 부터 0x2000 바이트)의 뒤, 0x6000 바이트
RESEARCH = {"tech_table": DATA + 0x48, "tech_count": DATA + 0x50, "design_table": DATA + 0x58, "design_count": DATA + 0x54,
            "world": (WORLD, 0x80), "lists": 0x2100, "recompute": RECOMPUTE}
RESEARCH_LAYOUT = {**RESEARCH, "world": WORLD}
PLANT, AGAIN = TEXT + 0x1000, TEXT + 0x1800     # 서명을 심는 곳, 같은 서명을 한 번 더 심는 곳
TOKEN = re.compile(r"\[rip(?:\+([14]))?\]|\[u(?:8|32)\]|\?|[0-9A-Fa-f]{2}")   # 서명 글의 낱말(native/srtoybox/sigs.h)


def shell(functions: list[tuple[int, int]], size: int = SIZE) -> bytearray:
    """머리말 · 구역 표 · 함수 표만 있는 빈 이미지. functions: 함수 표에 넣을 [시작, 끝) 들(시작순)."""
    image = bytearray(size)
    image[0:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x98] = b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664, 4, 0, 0, 0, 0xF0, 0x22)
    optional = 0x98
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<II", image, optional + 56, size, 0x400)                 # SizeOfImage, SizeOfHeaders
    struct.pack_into("<I", image, optional + 108, 16)                          # NumberOfRvaAndSizes
    struct.pack_into("<II", image, optional + 112 + 3 * 8, PDATA, 12 * len(functions))
    for i, (name, rva, flags) in enumerate([(b".text", TEXT, 0x60000020), (b".rdata", RDATA, 0x40000040),
                                            (b".pdata", PDATA, 0x40000040), (b".data", DATA, 0xC0000040)]):
        struct.pack_into("<8sIIIIIIHHI", image, optional + 0xF0 + 40 * i, name, 0x2000 if rva == TEXT else size - DATA if rva == DATA else 0x1000, rva,
                         0, 0, 0, 0, 0, 0, flags)
    unwind = RDATA + 0x800
    image[unwind:unwind + 4] = bytes([1, 0, 0, 0])                             # 풀기 정보: 뿌리(플래그 없음)
    for i, (begin, end) in enumerate(functions):
        struct.pack_into("<III", image, PDATA + 12 * i, begin, end, unwind)
    return image


def put(image: bytearray, rva: int, data: bytes) -> int:
    image[rva:rva + len(data)] = data
    return rva + len(data)


def rip(image: bytearray, rva: int, opcode: bytes, target: int, tail: bytes = b"") -> int:
    """RIP 상대 변위가 든 명령 하나: opcode + 변위(4) + tail. 변위는 명령의 끝을 기준으로 한다."""
    length = len(opcode) + 4 + len(tail)
    return put(image, rva, opcode + struct.pack("<i", target - (rva + length)) + tail)


def plant(image: bytearray, at: int, text: str, target) -> int:
    """서명 글 하나를 at 에 심는다: 정해진 바이트는 그대로, 구멍은 건드리지 않고, 읽어 낼 자리는 target 이 나오게.
    target 이 튜플이면 읽어 낼 자리마다 차례로 하나씩 쓴다. 끝 자리를 돌려준다."""
    values = iter(target if isinstance(target, tuple) else (target, target))
    pos = at
    for m in TOKEN.finditer(text):
        word = m.group(0)
        if word.startswith("[rip"):
            struct.pack_into("<i", image, pos, next(values) - (pos + 4 + int(m.group(1) or 0)))
            pos += 4
        elif word == "[u32]":
            struct.pack_into("<I", image, pos, next(values))
            pos += 4
        elif word == "[u8]":
            image[pos] = next(values)
            pos += 1
        elif word == "?":
            pos += 1
        else:
            image[pos] = int(word, 16)
            pos += 1
    return pos


def shape(text: str) -> str:
    """읽어 낼 자리를 구멍으로 바꾼 글. 꼴이 같은 서명들은 게임에서 같은 자리의 명령을 읽는다
    (프로그램 상태와 모드 상태가 게임 진입의 두 mov 에서 하나씩 읽는다) — 한 곳에만 심어야 저마다 한 번씩 맞는다."""
    return " ".join("? ? ? ?" if w.startswith("[rip") or w == "[u32]" else "?" if w in ("?", "[u8]") else w.upper()
                    for w in (m.group(0) for m in TOKEN.finditer(text)))


def beside(target):
    """그 값의 옆: 주소는 8바이트 옆, (간격, 첫 칸)은 저마다 4 큰 값."""
    return tuple(value + 4 for value in target) if isinstance(target, tuple) else target + 8


def sig_image(sigs: list[tuple[str, str]], *, broken=(), twice=(), stray=(), targets: dict | None = None,
              into: bytearray | None = None) -> bytes:
    """DLL 의 서명 표(sigs: [(찾을 것, 서명 글)])를 심은 이미지. into 가 없으면 치트 문자열이 하나도 없는 빈 틀에 심는다.

    broken · twice · stray 는 sigs 의 칸 번호들이다: 심지 않는다 / 한 번 더 심는다(두 번 맞는다) / 옆의 값을 가리키게 심는다.
    targets 로 가짜 주소 · 값을 바꾼다(STATE · VALUES · MORE · RESEARCH 의 이름으로).
    """
    image = into if into is not None else shell([(RECOMPUTE, RECOMPUTE + 0x40), (PLANT, TEXT + 0x2000)])
    at = {**STATE, **VALUES, **MORE, **RESEARCH, **(targets or {})}
    places: dict[str, int] = {}
    for i, (name, text) in enumerate(sigs):
        if i in broken:
            continue
        place = places.setdefault(shape(text), PLANT + 0x40 * len(places))
        plant(image, place, text, beside(at[name]) if i in stray else at[name])
        if i in twice:
            plant(image, AGAIN + 0x40 * i, text, at[name])
    return bytes(image)


def build(sigs: list[tuple[str, str]] | None = None, *, extra_anchor: bool = False, second_call: bool = False,
          no_options: bool = False, outside: bool = False) -> bytes:
    """옛 찾기의 닻(치트 문자열, 명령 처리 함수, 그것을 부르는 곳)이 든 이미지. sigs 를 주면 새 찾기의 서명도 심는다.

    나머지 인자는 옛 찾기가 거부해야 하는 흠을 하나씩 낸다.
    """
    image = shell([(HANDLER, HANDLER + 0x200), (CALLER, CALLER + 0x20), (CALLER + 0x20, CALLER + 0x100), (RECOMPUTE, RECOMPUTE + 0x40),
                   (PLANT, TEXT + 0x2000)])
    unwind = RDATA + 0x800
    put(image, unwind + 0x10, bytes([0x21, 0, 0, 0]) + struct.pack("<III", CALLER, CALLER + 0x20, unwind))   # UNW_FLAG_CHAININFO
    struct.pack_into("<I", image, PDATA + 12 * 2 + 8, unwind + 0x10)           # 부르는 함수의 뒤 조각은 앞 조각에 묶인다
    put(image, ANCHOR, b"cheat allowcheats\0")
    if extra_anchor:
        put(image, RDATA + 0x400, b"cheat allowcheats\0")

    # 명령 처리 함수: lea rdx,["cheat allowcheats"] / or dword ptr [옵션],40h
    end = put(image, HANDLER, bytes([0x40, 0x55, 0x53, 0x57]))
    end = rip(image, end, bytes([0x48, 0x8D, 0x15]), ANCHOR)
    if not no_options:
        end = rip(image, end, bytes([0x83, 0x0D]), SIZE + 0x100 if outside else LEGACY["options"], b"\x40")
    put(image, end, b"\xC3")

    # 부르는 함수의 뒤쪽 조각: lea rcx,[this] / call 명령 처리 함수
    end = rip(image, CALLER + 0x30, bytes([0x48, 0x8D, 0x0D]), LEGACY["context"])
    rip(image, end, bytes([0xE8]), HANDLER)
    if second_call:
        rip(image, CALLER + 0x60, bytes([0xE8]), HANDLER)
    return sig_image(sigs, into=image) if sigs is not None else bytes(image)
