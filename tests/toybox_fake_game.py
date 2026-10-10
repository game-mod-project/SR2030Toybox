"""가짜 게임 메모리: ToyBox 가 읽고 쓰는 전역과 지역 객체를 Python 버퍼로 흉내 낸다.

tests/test_toybox_game.py · test_toybox_values.py 와 tests/toybox_overlay_probe.py 가 쓴다(pytest 가 직접 모으는 테스트 파일이 아니다).
전역은 mem 의 앞쪽에, 지역 표는 0x1000 부터 있다. 지역 객체와 세계 자료 객체는 게임처럼 따로 잡은 버퍼이고 표와 포인터가 그 주소를 가리킨다.
값의 자리(LAYOUT)는 진짜 게임의 것보다 작게 잡았다 — ToyBox 는 자리를 찾은 것(ValueLayout)에서만 읽는다.
"""
import ctypes
import struct
from ctypes import wintypes

from srkit.toybox import GameAddresses, MoreLayout, ValueLayout

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, WORLD_POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x30, 0x1000
LAYOUT = dict(world_pointer=WORLD_POINTER, treasury=0x40, stock_first=0x60, stock_step=0x10, used_first=0x18, used_step=0x84)
# 더 쓰는 값의 자리: 기술 수준, 여론의 세 칸, 지역 인덱스로 찾는 표 셋(가짜 게임의 표는 256칸 — 인덱스 255 까지 쓴다)
MORE = dict(tech=0x130, opinion0=0x134, opinion1=0x138, opinion2=0x150, relation0=0x200, relation1=0x600, casus=0xA00)
RELATION_TABLES = ("relation0", "relation1", "casus")
OBJECT_SIZE = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]


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
