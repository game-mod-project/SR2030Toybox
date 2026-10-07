"""가짜 게임 메모리: ToyBox 가 읽는 전역과 지역 객체를 Python 버퍼로 흉내 낸다.

tests/test_toybox_game.py 와 tests/toybox_overlay_probe.py 가 쓴다(pytest 가 직접 모으는 테스트 파일이 아니다).
전역은 mem 의 앞쪽에, 지역 표는 0x1000 부터 있다. 지역 객체는 게임처럼 따로 잡은 버퍼이고 표가 그 주소를 가리킨다.
"""
import ctypes
import struct

from srkit.toybox import GameAddresses

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x1000


class FakeGame:
    def __init__(self):
        self.mem = (ctypes.c_ubyte * 0x4000)()
        self.base = ctypes.addressof(self.mem)
        self.at = GameAddresses(handler=0, context=0x40, multiplayer=MULTIPLAYER, options=OPTIONS, program_state=PROGRAM,
                                mode_state=MODE, player_index=INDEX, player_pointer=POINTER, region_table=TABLE, region_count=COUNT)
        self.objects: dict[int, ctypes.Array] = {}
        self.menu()

    def poke(self, offset: int, fmt: str, value: int) -> None:
        struct.pack_into(fmt, self.mem, offset, value)

    def peek(self, offset: int, fmt: str) -> int:
        return struct.unpack_from(fmt, self.mem, offset)[0]

    def region(self, index: int, number: int, alive: int = 2) -> None:
        """지역 객체 하나: +0 살아 있는가(dword), +4 자기 인덱스(word), +8 지역 번호(word)."""
        obj = (ctypes.c_ubyte * 16)()
        struct.pack_into("<IHHH", obj, 0, alive, index, 0, number)
        self.objects[index] = obj
        self.poke(TABLE + 8 * index, "<Q", ctypes.addressof(obj))
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
        self.poke(POINTER, "<Q", ctypes.addressof(self.objects[index]))
