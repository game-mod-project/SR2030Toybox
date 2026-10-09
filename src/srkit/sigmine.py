"""서명 뽑기(개발용): 게임의 코드에서 주소를 읽어 낼 서명 후보를 찾는다. 설치된 실행 파일을 읽기만 한다.

ToyBox 는 게임이 뜰 때 서명(native/srtoybox/sigs.h)으로 주소를 찾는다. 서명은 내장 치트와 무관한 코드에서 뽑아야 하고
(docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md 의 요구 3), 실행 구역 전체에서 정확히 한 번 맞아야 한다.
이 모듈은 그런 후보를 찾아 줄 뿐이다 — 서명 표(native/srtoybox/locate.cpp)에는 사람이 골라 옮긴다.

디스어셈블러 capstone 을 쓴다(개발 의존성). 게임 안에서 도는 DLL 과 srkit 의 다른 명령은 쓰지 않는다.
"""
from __future__ import annotations

import bisect
import re
import struct
from dataclasses import dataclass

import capstone
import numpy as np
from capstone import x86_const as X

# 서명 글의 낱말(native/srtoybox/sigs.h 와 같다)
TOKEN = re.compile(r"\[rip(?:\+([14]))?\]|\[u(?:8|32)\]|\?|[0-9A-Fa-f]{2}")
ANCHOR = b"cheat allowcheats\0"      # 치트 명령 처리 함수를 가려내는 데만 쓴다(그 함수의 코드에서는 서명을 뽑지 않는다)


class Image:
    """RVA 대로 펼친 실행 파일(srkit.toybox.image_of 의 결과): 실행 구역과 함수 표."""

    def __init__(self, image: bytes):
        self.data = image
        pe = struct.unpack_from("<I", image, 0x3C)[0]
        count, optional_size = struct.unpack_from("<H", image, pe + 6)[0], struct.unpack_from("<H", image, pe + 20)[0]
        optional = pe + 24
        self.code: list[tuple[int, int]] = []          # 실행 구역 [시작, 끝)
        for i in range(count):
            _name, size, rva, _rs, _raw, _a, _b, _c, _d, flags = struct.unpack_from(
                "<8sIIIIIIHHI", image, optional + optional_size + 40 * i)
            if flags & 0x20000000 and size:            # IMAGE_SCN_MEM_EXECUTE
                self.code.append((rva, rva + size))
        pdata, pdata_size = struct.unpack_from("<II", image, optional + 112 + 3 * 8)
        self.funcs = [struct.unpack_from("<III", image, pdata + 12 * i) for i in range(pdata_size // 12)]
        self._starts = [f[0] for f in self.funcs]

    def _root_of(self, begin: int, unwind: int) -> int | None:
        for _ in range(32):                            # chained unwind 를 뿌리까지
            if not (self.data[unwind] >> 3) & 4:
                return begin
            parent = unwind + 4 + 2 * ((self.data[unwind + 2] + 1) & ~1)
            begin, _end, unwind = struct.unpack_from("<III", self.data, parent)
        return None

    def root(self, rva: int) -> int | None:
        """rva 가 든 함수의 시작. 함수 표에 없으면 None."""
        i = bisect.bisect_right(self._starts, rva) - 1
        if i < 0 or not (self.funcs[i][0] <= rva < self.funcs[i][1]):
            return None
        return self._root_of(self.funcs[i][0], self.funcs[i][2])

    def extent(self, root: int) -> tuple[int, int]:
        """그 함수의 모든 조각을 덮는 [시작, 끝)."""
        parts = [(begin, end) for begin, end, unwind in self.funcs if self._root_of(begin, unwind) == root]
        return min(b for b, _ in parts), max(e for _, e in parts)

    def refs(self, target: int) -> list[int]:
        """target 을 rip 상대로 가리키는 4바이트 거리의 자리들(그 뒤에 상수 0 · 1 · 4바이트가 붙는 명령)."""
        out: set[int] = set()
        for lo, hi in self.code:
            b = np.frombuffer(self.data, dtype=np.uint8)[lo:hi].astype(np.uint32)
            if len(b) < 4:
                continue
            disp = (b[:-3] | (b[1:-2] << 8) | (b[2:-1] << 16) | (b[3:] << 24)).astype(np.int32).astype(np.int64)
            after = lo + np.arange(len(disp), dtype=np.int64) + 4 + disp
            for tail in (0, 1, 4):
                out.update(int(lo + i) for i in np.nonzero(after + tail == target)[0])
        return sorted(out)


def regex(text: str, overlapping: bool = True) -> re.Pattern[bytes]:
    """서명 글 → 정규식. overlapping 이면 겹쳐 맞는 것까지 센다(DLL 의 세는 법과 같다. 느리다)."""
    out = b""
    for m in TOKEN.finditer(text):
        token = m.group(0)
        if token == "?" or token == "[u8]":
            out += b"."
        elif token.startswith("["):
            out += b"...."
        else:
            out += re.escape(bytes([int(token, 16)]))
    return re.compile(b"(?=" + out + b")" if overlapping else out, re.S)


def count(image: Image, text: str, exact: bool = True) -> int:
    """실행 구역에서 서명이 맞는 횟수."""
    pattern = regex(text, overlapping=exact)
    return sum(1 for lo, hi in image.code for _ in pattern.finditer(image.data, lo, hi))


def handler_range(image: Image) -> tuple[int, int] | None:
    """치트 명령 처리 함수의 [시작, 끝). 치트가 없는 빌드면 None.

    치트 코드를 "보는" 곳이지만 DLL 밖이다: 여기서 뽑는 서명이 그 함수의 코드가 아님을 가리는 데만 쓴다.
    """
    at = image.data.find(b"\0" + ANCHOR)
    if at < 0:
        return None
    string = at + 1
    for lo, hi in image.code:
        for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", image.data[lo:hi]):
            use = lo + m.start()
            if use + 7 + struct.unpack_from("<i", image.data, use + 3)[0] == string:
                root = image.root(use)
                return image.extent(root) if root is not None else None
    return None


@dataclass
class Candidate:
    function: int | None     # 서명이 든 함수의 시작(함수 표에 없으면 None)
    at: int                  # 서명이 맞는 자리
    length: int              # 바이트 수
    text: str                # 서명 글


_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
_md.detail = True


def _first_instruction(image: Image, pos: int, target: int):
    """4바이트 rip 상대 거리가 pos 에 있고 target 을 가리키는 명령."""
    for back in (3, 4, 5, 2, 6, 7, 1):                 # 흔한 꼴부터: REX + 연산 + ModRM, 0F 가 낀 것, 접두 없는 것
        start = pos - back
        ins = next(_md.disasm(image.data[start:start + 16], start), None)
        if ins is None or ins.disp_size != 4 or start + ins.disp_offset != pos:
            continue
        if any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP and ins.address + ins.size + op.mem.disp == target
               for op in ins.operands):
            return ins
    return None


def _words(ins, first: bool) -> list[str] | None:
    """명령 하나의 서명 글. 첫 명령의 rip 상대 거리는 읽어 낼 자리, 그 밖의 rip 상대 거리와 call · jmp 의 4바이트 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    rip = ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    if first:
        tail = ins.size - (ins.disp_offset + 4)
        if tail not in (0, 1, 4):
            return None
        out[ins.disp_offset:ins.disp_offset + 4] = ["[rip]" if tail == 0 else f"[rip+{tail}]"]
    elif rip:
        out[ins.disp_offset:ins.disp_offset + 4] = ["?"] * 4
    elif (ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands \
            and ins.operands[0].type == X.X86_OP_IMM:
        out[ins.size - 4:] = ["?"] * 4
    return out


def mine_address(image: Image, target: int, *, exclude: tuple[int, int] | None = None, fewest: int = 3, most: int = 8,
                 fixed: int = 8, longest: int = 60, sites: int = 400) -> list[Candidate]:
    """target 을 가리키는 명령에서 시작해 실행 구역 전체에서 한 번만 맞는 가장 짧은 서명을, 쓰는 자리마다 하나씩.

    exclude 안의 자리는 보지 않는다(치트 명령 처리 함수). 명령 fewest 개 · 정해진 바이트 fixed 개 이상이어야 서명으로 친다.
    쓰는 자리가 sites 보다 많으면 고르게 골라 그만큼만 본다.
    """
    found: list[Candidate] = []
    places = [p for p in image.refs(target) if not (exclude and exclude[0] <= p < exclude[1])]
    for pos in places[::max(1, len(places) // sites)]:
        first = _first_instruction(image, pos, target)
        if first is None:
            continue
        words: list[str] = []
        length = 0
        for n, ins in enumerate(_md.disasm(image.data[first.address:first.address + 160], first.address), start=1):
            more = _words(ins, first=n == 1)
            if more is None or length + ins.size > longest:
                break
            words += more
            length += ins.size
            text = " ".join(words)
            if n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                found.append(Candidate(image.root(first.address), first.address, length, text))
                break
            if n >= most or ins.id in (X.X86_INS_RET, X.X86_INS_INT3, X.X86_INS_JMP):
                break
    return found


def best_per_function(candidates: list[Candidate]) -> list[Candidate]:
    """함수마다 가장 짧은 것 하나. 짧은 것부터(같으면 앞의 것부터)."""
    best: dict[int, Candidate] = {}
    for c in candidates:
        key = c.function if c.function is not None else -c.at      # 함수 표에 없는 자리는 저마다 다른 함수로 친다
        if key not in best or (c.length, c.at) < (best[key].length, best[key].at):
            best[key] = c
    return sorted(best.values(), key=lambda c: (c.length, c.at))
