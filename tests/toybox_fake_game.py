"""가짜 게임 메모리: ToyBox 가 읽고 쓰는 전역과 지역 객체를 Python 버퍼로 흉내 낸다.

tests/test_toybox_game.py · test_toybox_values.py 와 tests/toybox_overlay_probe.py 가 쓴다(pytest 가 직접 모으는 테스트 파일이 아니다).
전역은 mem 의 앞쪽에, 지역 표는 0x1000 부터 있다. 지역 객체와 세계 자료 객체는 게임처럼 따로 잡은 버퍼이고 표와 포인터가 그 주소를 가리킨다.
값의 자리(LAYOUT)는 진짜 게임의 것보다 작게 잡았다 — ToyBox 는 자리를 찾은 것(ValueLayout)에서만 읽는다.
연구(Lab)는 따로 붙인다: 기술 표 · 부대 설계 표 · 보유 비트 묶음 · 지역별 연구 목록.
"""
import ctypes
import struct
from ctypes import wintypes

from srkit.toybox import GameAddresses, MoreLayout, ResearchLayout, ValueLayout

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, WORLD_POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x30, 0x1000
LAYOUT = dict(world_pointer=WORLD_POINTER, treasury=0x40, stock_first=0x60, stock_step=0x10, used_first=0x18, used_step=0x84)
# 더 쓰는 값의 자리: 기술 수준, 여론의 세 칸, 지역 인덱스로 찾는 표 셋(가짜 게임의 표는 256칸 — 인덱스 255 까지 쓴다)
MORE = dict(tech=0x130, opinion0=0x134, opinion1=0x138, opinion2=0x150, relation0=0x200, relation1=0x600, casus=0xA00,
            people0=0x160, people1=0x170, approval=0x158)
RELATION_TABLES = ("relation0", "relation1", "casus")
OBJECT_SIZE = 0x1000
# 연구의 자리: 전역 넷은 mem 의 앞쪽, 세계 객체는 mem 의 0x800 부터(지역 표가 그 +0x800), 연구 목록은 그 +0x1800(지역마다 24바이트 × 256칸).
# "다시 셈" 함수는 자리가 아니라 함수로 준다(srtoybox_research_write · srtoybox_test_research 의 인자)
RESEARCH = dict(tech_table=0x50, tech_count=0x58, design_table=0x60, design_count=0x5C, world=0x800, lists=0x1800, recompute=0)
TECH_SIZE, DESIGN_SIZE, OWNERS_BYTES, LIST_STEP, NODE_SIZE = 0x88, 0x168, 128, 24, 0x60   # native/srtoybox/locate.h 의 꼴
TECH, DESIGN = 1, 2                                                                        # 연구 목록 노드의 종류
GONE, ENDED = 0x80000000, 0x08000000                                                       # 노드의 깃발: 그 쪽에서 뺐다 / 치트의 "끝냄"

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetProcessHeap.restype = ctypes.c_void_p
kernel32.HeapAlloc.restype = ctypes.c_void_p
kernel32.HeapAlloc.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t]
kernel32.HeapSize.restype = ctypes.c_size_t
kernel32.HeapSize.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
kernel32.HeapValidate.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]


class FakeGame:
    def __init__(self):
        self.mem = (ctypes.c_ubyte * 0x4000)()
        self.base = ctypes.addressof(self.mem)
        self.at = GameAddresses(handler=0, context=0x40, multiplayer=MULTIPLAYER, options=OPTIONS, program_state=PROGRAM,
                                mode_state=MODE, player_index=INDEX, player_pointer=POINTER, region_table=TABLE, region_count=COUNT)
        self.layout = ValueLayout(**LAYOUT)
        self.more = MoreLayout(**MORE)
        self.objects: dict[int, ctypes.Array] = {}
        self.where: dict[int, int] = {}                           # 지역 객체가 지금 있는 주소(lock 으로 옮기면 바뀐다)
        self.world = (ctypes.c_ubyte * 0x800)()                   # 세계 자료 객체: "이 물자를 쓰는가"의 표가 있다
        self.poke(WORLD_POINTER, "<Q", ctypes.addressof(self.world))
        self.menu()

    def poke(self, offset: int, fmt: str, value: int) -> None:
        struct.pack_into(fmt, self.mem, offset, value)

    def peek(self, offset: int, fmt: str) -> int:
        return struct.unpack_from(fmt, self.mem, offset)[0]

    def region(self, index: int, number: int, alive: int = 2) -> None:
        """지역 객체 하나: +0 살아 있는가(dword), +4 자기 인덱스(word), +8 지역 번호(word). 값의 칸은 0 으로 차 있다."""
        obj = (ctypes.c_ubyte * OBJECT_SIZE)()
        struct.pack_into("<IHHH", obj, 0, alive, index, 0, number)
        self.objects[index] = obj
        self.where[index] = ctypes.addressof(obj)
        self.poke(TABLE + 8 * index, "<Q", self.where[index])
        self.poke(COUNT, "<i", max(self.peek(COUNT, "<i"), index))

    def menu(self) -> None:
        """메인 메뉴 · 로비: 상태 3 / 1, 플레이어 포인터는 비어 있다(인덱스는 낡은 값이 남는다)."""
        self.poke(PROGRAM, "<i", 3)
        self.poke(MODE, "<i", 1)
        self.poke(POINTER, "<Q", 0)

    def play(self, index: int) -> None:
        """그 인덱스의 지역으로 게임을 진행 중이다."""
        self.poke(PROGRAM, "<i", 1)
        self.poke(MODE, "<i", 2)
        self.poke(INDEX, "<i", index)
        self.poke(POINTER, "<Q", self.where[index])

    def use(self, slot: int, on: bool = True) -> None:
        """이번 판에서 그 물자를 쓴다(세계 자료 객체의 float 가 0 보다 크다) / 안 쓴다."""
        struct.pack_into("<f", self.world, LAYOUT["used_first"] + LAYOUT["used_step"] * slot, 1.0 if on else 0.0)

    def _read(self, index: int, offset: int, fmt: str):
        return struct.unpack(fmt, ctypes.string_at(self.where[index] + offset, struct.calcsize(fmt)))[0]

    def _write(self, index: int, offset: int, fmt: str, value) -> None:
        ctypes.memmove(self.where[index] + offset, struct.pack(fmt, value), struct.calcsize(fmt))

    def treasury(self, index: int) -> float:
        return self._read(index, LAYOUT["treasury"], "<d")

    def set_treasury(self, index: int, value: float) -> None:
        self._write(index, LAYOUT["treasury"], "<d", value)

    def stock(self, index: int, slot: int) -> float:
        return self._read(index, LAYOUT["stock_first"] + LAYOUT["stock_step"] * slot, "<f")

    def set_stock(self, index: int, slot: int, value: float) -> None:
        self._write(index, LAYOUT["stock_first"] + LAYOUT["stock_step"] * slot, "<f", value)

    def tech(self, index: int) -> float:
        return self._read(index, MORE["tech"], "<f")

    def set_tech(self, index: int, value: float) -> None:
        self._write(index, MORE["tech"], "<f", value)

    def opinion(self, index: int) -> list[float]:
        return [self._read(index, MORE[name], "<f") for name in ("opinion0", "opinion1", "opinion2")]

    def people(self, index: int) -> list[float]:
        """그 지역의 [인구, 인구의 풀, 국내 지지율]."""
        return [self._read(index, MORE[name], "<f") for name in ("people0", "people1", "approval")]

    def set_people(self, index: int, values: tuple[float, float], approval: float) -> None:
        """그 지역의 인구 칸 · 인구의 풀 칸과 국내 지지율."""
        for name, value in zip(("people0", "people1", "approval"), (*values, approval)):
            self._write(index, MORE[name], "<f", value)

    def set_opinion(self, index: int, values: tuple[float, float, float]) -> None:
        for name, value in zip(("opinion0", "opinion1", "opinion2"), values):
            self._write(index, MORE[name], "<f", value)

    def relation(self, index: int, other: int) -> list[float]:
        """index 의 지역 객체가 other(인덱스)에 대해 가진 값: [관계 표 1, 관계 표 2, 전쟁 명분]."""
        return [self._read(index, MORE[name] + 4 * other, "<f") for name in RELATION_TABLES]

    def set_relation(self, index: int, other: int, values: tuple[float, float, float]) -> None:
        for name, value in zip(RELATION_TABLES, values):
            self._write(index, MORE[name] + 4 * other, "<f", value)

    def snapshot(self, index: int) -> bytes:
        """그 지역 객체의 지금 바이트 전부."""
        return ctypes.string_at(self.where[index], OBJECT_SIZE)

    def lock(self, index: int, protection: int = 0x02) -> int:
        """그 지역 객체를 따로 잡은 쪽으로 옮기고 그 쪽을 쓸 수 없게 한다(0x02 읽기 전용, 0x20 실행 · 읽기). 새 주소를 돌려준다.

        읽을 수는 있으므로 게임 상태는 그대로 읽힌다 — 쓰기만 안 된다. 그 지역으로 play 하고 있었으면 다시 play 해야 한다.
        (쪽은 돌려주지 않는다. 테스트 프로세스가 끝나면 없어진다.)
        """
        page = kernel32.VirtualAlloc(None, 0x1000, 0x3000, 0x04)
        ctypes.memmove(page, self.where[index], OBJECT_SIZE)
        old = wintypes.DWORD()
        assert kernel32.VirtualProtect(page, 0x1000, protection, ctypes.byref(old))
        self.where[index] = page
        self.poke(TABLE + 8 * index, "<Q", page)
        return page


def locked_page(protection: int = 0x02) -> int:
    """0 으로 찬 한 쪽을 잡아 쓸 수 없게 한다(0x02 읽기 전용, 0x20 실행 · 읽기). 그 주소를 돌려준다(돌려주지 않는다 — 프로세스가 끝나면 없어진다)."""
    page = kernel32.VirtualAlloc(None, 0x1000, 0x3000, 0x04)
    old = wintypes.DWORD()
    assert kernel32.VirtualProtect(page, 0x1000, protection, ctypes.byref(old))
    return page


class Lab:
    """가짜 게임의 연구: 기술 표 · 부대 설계 표 · 보유 비트 묶음 · 지역별 연구 목록.

    표는 따로 잡은 버퍼이고 mem 의 전역이 그 주소와 자리 수를 가리킨다. 보유 묶음은 게임처럼 프로세스 힙에서 128바이트를 받는다 —
    ToyBox 는 새 묶음을 만들기 전에 게임의 묶음이 그 힙의 것인지 본다. block 을 주면 그 주소를 묶음으로 건다(그 힙의 블록이 아닌 것,
    쓸 수 없는 쪽에 있는 것을 흉내 낼 때).
    """

    def __init__(self, fake: FakeGame, techs: int = 64, designs: int = 64):
        self.fake = fake
        self.layout = ResearchLayout(**RESEARCH)
        self.techs = (ctypes.c_ubyte * (techs * TECH_SIZE))()
        self.designs = (ctypes.c_ubyte * (designs * DESIGN_SIZE))()
        self.kept: list = []                                      # 이름 글과 노드의 버퍼(살려 둔다)
        self.nodes: list[int] = []                                # 노드의 주소(건 순서)
        fake.poke(RESEARCH["tech_table"], "<Q", ctypes.addressof(self.techs))
        fake.poke(RESEARCH["tech_count"], "<i", techs)
        fake.poke(RESEARCH["design_table"], "<Q", ctypes.addressof(self.designs))
        fake.poke(RESEARCH["design_count"], "<i", designs)

    @property
    def world(self) -> int:
        """세계 객체의 주소("다시 셈" 함수의 첫 인자)."""
        return self.fake.base + RESEARCH["world"]

    def tech(self, number: int, *needs: int, level: int = 10, kind: int = 1, days: float = 100.0, owners=()) -> None:
        """기술 레코드: +0 분류, +1 수준, +4 · +6 선행, +0x30 연구 기간(ToyBox 는 건드리지 않는다), +0x50 보유 묶음."""
        at = number * TECH_SIZE
        struct.pack_into("<BB", self.techs, at, kind, level)
        struct.pack_into("<HH", self.techs, at + 4, *(list(needs) + [0, 0])[:2])
        struct.pack_into("<f", self.techs, at + 0x30, days)
        for index in owners:
            self.own(TECH, number, index)

    def design(self, number: int, *needs: int, cls: int = 0, year: int = 50, is_open: bool = True, hold: tuple[int, int] = (0, 0),
               name: bytes = b"Unit", owners=()) -> None:
        """부대 설계 레코드: +0 이름 글, +8 병과, +0xA 연도, +0x20 연구 대상, +0x34 선행 넷, +0xEC · +0xF0 깃발, +0xF8 보유 묶음."""
        at = number * DESIGN_SIZE
        text = ctypes.create_string_buffer(name)
        self.kept.append(text)
        struct.pack_into("<Q", self.designs, at, ctypes.addressof(text))
        struct.pack_into("<BxB", self.designs, at + 8, cls, year)
        struct.pack_into("<H", self.designs, at + 0x20, int(is_open))
        struct.pack_into("<4H", self.designs, at + 0x34, *(list(needs) + [0] * 4)[:4])
        struct.pack_into("<II", self.designs, at + 0xEC, *hold)
        for index in owners:
            self.own(DESIGN, number, index)

    def _cell(self, kind: int, number: int) -> tuple[ctypes.Array, int]:
        """그 항목의 보유 묶음 포인터가 든 칸: (표, 표 안의 자리)."""
        return (self.techs, number * TECH_SIZE + 0x50) if kind == TECH else (self.designs, number * DESIGN_SIZE + 0xF8)

    def block(self, kind: int, number: int) -> int:
        """그 항목의 보유 묶음의 주소. 없으면 0."""
        table, at = self._cell(kind, number)
        return struct.unpack_from("<Q", table, at)[0]

    def house(self, kind: int, number: int, block: int | None = None) -> int:
        """보유 묶음을 건다. block 을 주지 않으면 프로세스 힙에서 0 으로 찬 128바이트를 받는다(게임이 하는 그대로)."""
        table, at = self._cell(kind, number)
        if block is None:
            block = kernel32.HeapAlloc(kernel32.GetProcessHeap(), 8, OWNERS_BYTES)      # HEAP_ZERO_MEMORY
        struct.pack_into("<Q", table, at, block)
        return block

    def own(self, kind: int, number: int, index: int, on: bool = True) -> None:
        """그 지역(인덱스)이 그 항목을 보유한다 / 하지 않는다. 묶음이 없으면 만든다."""
        block = self.block(kind, number) or self.house(kind, number)
        byte = ctypes.string_at(block + index // 8, 1)[0]
        byte = byte | (1 << index % 8) if on else byte & ~(1 << index % 8)
        ctypes.memmove(block + index // 8, bytes([byte]), 1)

    def owners(self, kind: int, number: int) -> set[int]:
        """그 항목을 보유한 지역의 인덱스들. 묶음이 없으면 빈 집합."""
        block = self.block(kind, number)
        bits = int.from_bytes(ctypes.string_at(block, OWNERS_BYTES), "little") if block else 0
        return {index for index in range(OWNERS_BYTES * 8) if bits >> index & 1}

    def held(self, kind: int, count: int, index: int) -> list[int]:
        """그 지역이 보유한 항목의 번호들(1 … count - 1 에서)."""
        return [number for number in range(1, count) if index in self.owners(kind, number)]

    def queue(self, index: int, kind: int, number: int, flags: tuple[int, int] = (1, 0), at: int | None = None) -> int:
        """그 지역의 연구 목록의 머리에 노드를 건다(게임처럼 새 노드가 머리가 된다). 노드의 주소를 돌려준다.
        노드: +0x08 앞, +0x10 다음, +0x18 번호, +0x1C 종류, +0x20 · +0x24 깃발, +0x28 남은 기간. at 을 주면 그 주소에 짓는다."""
        if at is None:
            buffer = (ctypes.c_ubyte * NODE_SIZE)()
            self.kept.append(buffer)
            at = ctypes.addressof(buffer)
        head = RESEARCH["world"] + RESEARCH["lists"] + LIST_STEP * index
        after = self.fake.peek(head, "<Q")
        ctypes.memmove(at, struct.pack("<QQQIIIIf", 0x1234, 0, after, number, kind, flags[0], flags[1], 115.0), 0x2C)
        if after:
            ctypes.memmove(after + 8, struct.pack("<Q", at), 8)
        self.fake.poke(head, "<Q", at)
        self.fake.poke(head + 8, "<Q", self.fake.peek(head + 8, "<Q") + 1)
        self.nodes.append(at)
        return at

    def flags(self, node: int) -> tuple[int, int]:
        return struct.unpack("<II", ctypes.string_at(node + 0x20, 8))

    def everything(self) -> dict[str, bytes]:
        """연구에 딸린 메모리 전부: 표 둘, 묶음마다(t<번호> · d<번호>), 노드마다(n<건 순서>), 그리고 가짜 게임의 전역(mem).
        쓰기가 다른 곳을 건드리지 않았는지 볼 때 앞뒤를 견준다."""
        out = {"mem": bytes(self.fake.mem), "techs": bytes(self.techs), "designs": bytes(self.designs)}
        for kind, letter, count in ((TECH, "t", len(self.techs) // TECH_SIZE), (DESIGN, "d", len(self.designs) // DESIGN_SIZE)):
            for number in range(1, count):
                if self.block(kind, number):
                    try:
                        out[f"{letter}{number}"] = ctypes.string_at(self.block(kind, number), OWNERS_BYTES)
                    except OSError:                   # 읽을 수 없는 주소를 묶음으로 걸어 둔 테스트
                        out[f"{letter}{number}"] = b""
        for i, node in enumerate(self.nodes):
            out[f"n{i}"] = ctypes.string_at(node, NODE_SIZE)
        return out


def standard_lab(fake: FakeGame, germany: int = 176, poland: int = 141, denmark: int = 150) -> Lab:
    """테스트들이 함께 쓰는 연구의 판. 지역은 인덱스로 준다(독일이 플레이어다).

    기술      1(수준 10. 독일 · 폴란드 보유) ← 2(수준 20. 폴란드만) ← 3(수준 30. 아무도 — 묶음이 없다) / 4(수준 40. 독일 · 덴마크) ← 6(수준 60. 독일)
              / 7(수준 70. 덴마크만). 5 는 빈 자리다.
    부대 설계 10(선행 1. 독일) / 11(선행 3. 폴란드. 병과 2, 1995년) / 12(선행 4. 아무도 — 묶음이 없다) / 13(선행 6. 독일 · 폴란드)
              / 14(선행 6. 독일. 게임이 "기술을 뺄 때" 건너뛰는 설계다 — 깃발)
    독일의 대기열: 기술 2 를 걸고(막 건 것) 그 뒤에 부대 설계 11 을 걸었다(연구 중). 게임처럼 나중에 건 것이 목록의 앞이다.
    """
    lab = Lab(fake)
    lab.tech(1, level=10, owners=(germany, poland))
    lab.tech(2, 1, level=20, owners=(poland,))
    lab.tech(3, 2, level=30)
    lab.tech(4, level=40, owners=(germany, denmark))
    lab.tech(6, 4, level=60, owners=(germany,))
    lab.tech(7, level=70, owners=(denmark,))
    lab.design(10, 1, owners=(germany,))
    lab.design(11, 3, cls=2, year=95, owners=(poland,))
    lab.design(12, 4)
    lab.design(13, 6, owners=(germany, poland))
    lab.design(14, 6, hold=(1, 0), owners=(germany,))
    lab.queue(germany, TECH, 2)
    lab.queue(germany, DESIGN, 11, flags=(1, 0x60000001))
    return lab
