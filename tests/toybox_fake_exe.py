"""주소 찾기(native/srtoybox/locate.cpp) 테스트용: 작은 가짜 실행 파일 이미지(RVA 대로 펼친 것).

게임의 코드를 옮긴 것이 아니다. locate 가 찾는 닻(문자열)과 서명(명령의 바이트 꼴)만 같은 자리 관계로 놓았다.
pytest 가 직접 모으는 테스트 파일이 아니다(tests/test_toybox_game.py 가 쓴다).
"""
import struct

SIZE = 0x8000                                 # 지역 표(8바이트 × 1024칸)가 DATA + 0x200 부터 들어갈 만큼
TEXT, RDATA, PDATA, DATA = 0x1000, 0x3000, 0x4000, 0x5000
HANDLER, CALLER, ENTER = 0x1000, 0x1800, 0x1A00
WORLD = DATA + 0x180                          # 지역 표 = WORLD + 0x80
EXPECTED = {"handler": HANDLER, "context": DATA + 0x100, "multiplayer": DATA, "options": DATA + 4, "program_state": DATA + 8,
            "mode_state": DATA + 12, "player_index": DATA + 16, "player_pointer": DATA + 24, "region_table": WORLD + 0x80,
            "region_count": DATA + 20}
STRINGS = {"cheat allowcheats": RDATA, "cheat georgew": RDATA + 0x20, "cheat georgeww": RDATA + 0x40,
           "cheat populate": RDATA + 0x60, "cheat becomeregion": RDATA + 0x80}


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
        struct.pack_into("<8sIIIIIIHHI", image, optional + 0xF0 + 40 * i, name, 0x2000 if rva == TEXT else 0x1000, rva,
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


def build(extra_anchor: bool = False, second_call: bool = False, no_head_check: bool = False, other_pointer: bool = False,
          outside: bool = False, other_table: bool = False) -> bytes:
    """가짜 이미지. 인자는 주소 찾기가 거부해야 하는 흠을 하나씩 낸다."""
    image = bytearray(SIZE)
    at = dict(EXPECTED)
    if outside:
        at["program_state"] = SIZE + 0x100     # 이미지 밖을 가리키는 주소

    def put(rva: int, data: bytes) -> int:
        image[rva:rva + len(data)] = data
        return rva + len(data)

    def rip(rva: int, opcode: bytes, target: int, tail: bytes = b"") -> int:
        """RIP 상대 변위가 든 명령 하나: opcode + 변위(4) + tail. 변위는 명령의 끝을 기준으로 한다."""
        length = len(opcode) + 4 + len(tail)
        return put(rva, opcode + struct.pack("<i", target - (rva + length)) + tail)

    # 머리말: DOS · NT · 구역 표
    put(0, b"MZ")
    struct.pack_into("<I", image, 0x3C, 0x80)
    put(0x80, b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664, 4, 0, 0, 0, 0xF0, 0x22))
    optional = 0x98
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<II", image, optional + 56, SIZE, 0x400)                 # SizeOfImage, SizeOfHeaders
    struct.pack_into("<I", image, optional + 108, 16)                          # NumberOfRvaAndSizes
    struct.pack_into("<II", image, optional + 112 + 3 * 8, PDATA, 4 * 12)      # 예외 디렉터리(.pdata)
    for i, (name, rva, flags) in enumerate([(b".text", TEXT, 0x60000020), (b".rdata", RDATA, 0x40000040),
                                            (b".pdata", PDATA, 0x40000040), (b".data", DATA, 0xC0000040)]):
        struct.pack_into("<8sIIIIIIHHI", image, optional + 0xF0 + 40 * i, name, 0x2000 if rva == TEXT else 0x1000, rva,
                         0, 0, 0, 0, 0, 0, flags)

    for text, rva in STRINGS.items():
        put(rva, text.encode() + b"\0")
    if extra_anchor:
        put(RDATA + 0x400, b"cheat allowcheats\0")

    # 명령 처리 함수
    end = put(HANDLER, bytes([0x40, 0x55, 0x53, 0x57]))
    if not no_head_check:
        end = rip(end, bytes([0x80, 0x3D]), at["multiplayer"], b"\0")          # cmp byte ptr [멀티플레이],0
    end = rip(end, bytes([0x48, 0x8D, 0x15]), STRINGS["cheat allowcheats"])    # lea rdx,["cheat allowcheats"]
    end = rip(end, bytes([0x83, 0x0D]), at["options"], b"\x40")                # or dword ptr [옵션],40h
    put(end, b"\xC3")

    def player_read(rva: int, text: str, pointer: int) -> None:                # lea rdx,[문자열] / mov rax,[포인터] / movsd xmm0,[rax+14B88h]
        end = rip(rva, bytes([0x48, 0x8D, 0x15]), STRINGS[text])
        end = rip(end, bytes([0x48, 0x8B, 0x05]), pointer)
        put(end, bytes([0xF2, 0x0F, 0x10, 0x80, 0x88, 0x4B, 0x01, 0x00]))

    player_read(0x1040, "cheat georgew", at["player_pointer"])
    player_read(0x1080, "cheat georgeww", at["player_pointer"] + (8 if other_pointer else 0))

    end = rip(0x10C0, bytes([0x48, 0x8D, 0x15]), STRINGS["cheat populate"])
    end = rip(end, bytes([0x48, 0x63, 0x05]), at["player_index"])              # movsxd rax,dword ptr [인덱스]
    end = rip(end, bytes([0x4C, 0x8D, 0x3D]), WORLD)                           # lea r15,[월드]
    put(end, bytes([0x49, 0x8B, 0x8C, 0xC7]) + struct.pack("<I", 0x80))        # mov rcx,[r15+rax*8+80h]

    end = rip(0x1100, bytes([0x48, 0x8D, 0x15]), STRINGS["cheat becomeregion"])
    end = put(end, bytes([0x0F, 0xB7, 0x4A, 0x04, 0x33, 0xD2]))                # movzx ecx,word ptr [rdx+4] / xor edx,edx
    end = rip(end, bytes([0x89, 0x0D]), at["player_index"])                    # mov [인덱스],ecx
    end = rip(end, bytes([0x89, 0x0D]), DATA + 0x1C)                           # mov [인덱스의 사본],ecx
    end = put(end, bytes([0x48, 0x63, 0xC1]))                                  # movsxd rax,ecx
    end = rip(0x1120, bytes([0x44, 0x8B, 0x0D]), at["region_count"])           # mov r9d,[지역 수]
    end = put(end, bytes([0x45, 0x33, 0xF6, 0x45, 0x85, 0xC9, 0x0F, 0x88, 0, 0, 0, 0]))
    rip(end, bytes([0x48, 0x8D, 0x0D]), at["region_table"] + (8 if other_table else 0))   # lea rcx,[지역 표]

    # 부르는 함수: 머리에 프로그램 상태 검사, 뒤쪽 조각에 호출
    end = put(CALLER, bytes([0x48, 0x81, 0xEC, 0xC0, 0x0D, 0x00, 0x00]))
    rip(end, bytes([0x83, 0x3D]), at["program_state"], b"\x06")                # cmp dword ptr [프로그램 상태],6
    end = rip(CALLER + 0x30, bytes([0x48, 0x8D, 0x0D]), at["context"])         # lea rcx,[this]
    rip(end, bytes([0xE8]), HANDLER)                                           # call 명령 처리 함수
    if second_call:
        rip(CALLER + 0x60, bytes([0xE8]), HANDLER)

    # 게임 진입: mov [모드 상태],2 / mov [프로그램 상태],1
    end = rip(ENTER, bytes([0xC7, 0x05]), at["mode_state"], struct.pack("<I", 2))
    rip(end, bytes([0xC7, 0x05]), at["program_state"], struct.pack("<I", 1))

    # .pdata: 부르는 함수는 조각 둘(뒤 조각이 앞 조각에 chained unwind 로 묶인다)
    unwind = RDATA + 0x800
    put(unwind, bytes([1, 0, 0, 0]))                                                         # 뿌리(플래그 없음)
    put(unwind + 0x10, bytes([0x21, 0, 0, 0]) + struct.pack("<III", CALLER, CALLER + 0x20, unwind))   # UNW_FLAG_CHAININFO
    put(PDATA, struct.pack("<III", HANDLER, HANDLER + 0x200, unwind)
        + struct.pack("<III", CALLER, CALLER + 0x20, unwind)
        + struct.pack("<III", CALLER + 0x20, CALLER + 0x100, unwind + 0x10)
        + struct.pack("<III", ENTER, ENTER + 0x20, unwind))
    return bytes(image)
