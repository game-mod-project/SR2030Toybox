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
from typing import Sequence

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


def _branch(ins) -> bool:
    """4바이트 목표를 가진 call · jmp 다(목표는 명령의 마지막 4바이트)."""
    return bool((ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands
                and ins.operands[0].type == X.X86_OP_IMM)


def _first_instruction(image: Image, pos: int, target: int):
    """4바이트 rip 상대 거리가 pos 에 있고 target 을 가리키는 명령. call · jmp rel32 의 목표도 같은 셈이다(함수를 찾을 때)."""
    for back in (3, 4, 5, 2, 6, 7, 1):                 # 흔한 꼴부터: REX + 연산 + ModRM, 0F 가 낀 것, 접두 없는 것
        start = pos - back
        ins = next(_md.disasm(image.data[start:start + 16], start), None)
        if ins is None or ins.disp_size != 4 or start + ins.disp_offset != pos:
            continue
        if any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP and ins.address + ins.size + op.mem.disp == target
               for op in ins.operands):
            return ins
    if image.data[pos - 1] in (0xE8, 0xE9) and _boundary(image, pos) == pos - 1:     # 앞의 바이트가 우연히 E8 인 자리는 거른다
        ins = next(_md.disasm(image.data[pos - 1:pos + 15], pos - 1), None)
        if ins is not None and ins.size == 5 and _branch(ins) and ins.operands[0].imm == target:
            return ins
    return None


def _words(ins, first: bool) -> list[str] | None:
    """명령 하나의 서명 글. 첫 명령의 rip 상대 거리(call · jmp 면 목표)는 읽어 낼 자리, 그 밖의 rip 상대 거리와 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    rip = ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    if first and _branch(ins):
        out[ins.size - 4:] = ["[rip]"]
    elif first:
        tail = ins.size - (ins.disp_offset + 4)
        if tail not in (0, 1, 4):
            return None
        out[ins.disp_offset:ins.disp_offset + 4] = ["[rip]" if tail == 0 else f"[rip+{tail}]"]
    elif rip:
        out[ins.disp_offset:ins.disp_offset + 4] = ["?"] * 4
    elif _branch(ins):
        out[ins.size - 4:] = ["?"] * 4
    return out


def _back(image: Image, address: int, n: int) -> int | None:
    """address 의 명령보다 n 개 앞선 명령의 시작. 그 함수 조각을 처음부터 풀어 내려와 찾는다 — 조각이 함수 표에 없거나,
    풀이가 address 에 닿지 않거나, 앞에 명령이 n 개가 안 되면 None."""
    i = bisect.bisect_right(image._starts, address) - 1
    if i < 0 or not (image.funcs[i][0] <= address < image.funcs[i][1]):
        return None
    begin = image.funcs[i][0]
    starts: list[int] = []
    for at, _size, _mnemonic, _operands in _lite.disasm_lite(image.data[begin:address + 16], begin):
        if at >= address:
            return starts[-n] if at == address and len(starts) >= n else None
        starts.append(at)
    return None


def _stops(ins, through_jumps: bool) -> bool:
    """이 명령 뒤로는 서명을 늘리지 않는다: 함수의 끝. 무조건 jmp 는 through_jumps 가 아니면 끝으로 친다."""
    return ins.id in (X.X86_INS_RET, X.X86_INS_INT3) or (ins.id == X.X86_INS_JMP and not through_jumps)


def mine_address(image: Image, target: int, *, exclude: Sequence[tuple[int, int]] = (), fewest: int = 3, most: int = 8,
                 fixed: int = 8, longest: int = 60, sites: int = 400, holding: Sequence[int] = (), back: int = 0,
                 through_jumps: bool = False) -> list[Candidate]:
    """target 을 가리키는 명령에서 시작해 실행 구역 전체에서 한 번만 맞는 가장 짧은 서명을, 쓰는 자리마다 하나씩.

    exclude 의 범위들 안의 자리는 보지 않는다(치트 코드 — cheat_ranges). 명령 fewest 개 · 정해진 바이트 fixed 개 이상이어야
    서명으로 친다. 쓰는 자리가 sites 보다 많으면 고르게 골라 그만큼만 본다.
    holding: 서명 안의 명령이 정해진 바이트로 들고 있어야 하는 상수들(구조체의 크기 · 칸의 자리 — 꼴이 바뀐 빌드에서 서명이
    맞지 않게 한다). back: 가리키는 명령보다 그만큼 앞선 명령부터 시작한다. through_jumps: 무조건 jmp 를 지나서도 늘린다.
    """
    found: list[Candidate] = []
    places = [p for p in image.refs(target) if not any(a <= p < z for a, z in exclude)]
    for pos in places[::max(1, len(places) // sites)]:
        first = _first_instruction(image, pos, target)
        if first is None:
            continue
        start = _back(image, first.address, back) if back else first.address
        if start is None:
            continue
        words: list[str] = []
        length = 0
        missing = list(holding)
        for n, ins in enumerate(_md.disasm(image.data[start:start + 200], start), start=1):
            more = _words(ins, first=ins.address == first.address)
            if more is None or length + ins.size > longest:
                break
            words += more
            length += ins.size
            missing = [value for value in missing if _holds(ins, value) is None]
            text = " ".join(words)
            if ins.address >= first.address and not missing and n >= fewest and sum(len(w) == 2 for w in words) >= fixed \
                    and count(image, text, exact=False) == 1 and count(image, text) == 1:
                found.append(Candidate(image.root(start), start, length, text))
                break
            if n >= most or _stops(ins, through_jumps):
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


_lite = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)     # 명령의 경계만 본다(자세히 풀지 않는다 — 빠르다)


def cheat_ranges(image: Image) -> list[tuple[int, int]]:
    """치트 코드의 [시작, 끝) 들: 명령 처리 함수(맨 앞)와, 치트 코드에서만 불리는 함수들. 치트가 없는 빌드면 빈 목록.

    서명은 이 범위 밖의 코드에서만 뽑는다. 치트 문자열은 있는데 그것을 쓰는 함수를 못 찾으면 LookupError —
    치트 코드를 가리지 못한 채 서명을 뽑게 두지 않는다.
    """
    if image.data.find(b"\0" + ANCHOR) < 0:
        return []
    handler = handler_range(image)
    if handler is None:
        raise LookupError("치트 문자열은 있는데 그것을 쓰는 함수를 찾지 못했습니다 — 치트 코드를 가리지 못한 채 서명을 뽑지 않습니다")
    starts = set(image._starts)
    callers: dict[int, list[int]] = {}                 # 함수의 시작 → 그것을 부르는 call rel32 의 자리들
    for lo, hi in image.code:
        b = np.frombuffer(image.data, dtype=np.uint8)[lo:hi]
        calls = np.nonzero(b[:-4] == 0xE8)[0]
        disp = (b[calls + 1].astype(np.uint32) | (b[calls + 2].astype(np.uint32) << 8) | (b[calls + 3].astype(np.uint32) << 16)
                | (b[calls + 4].astype(np.uint32) << 24)).astype(np.int32).astype(np.int64)
        for site, target in zip((lo + calls).tolist(), (lo + calls + 5 + disp).tolist()):
            if target in starts:
                callers.setdefault(target, []).append(site)
    ranges = [handler]
    grew = True
    while grew:                                        # 치트에서만 불리는 함수가 부르는 함수까지
        grew = False
        for target, sites in callers.items():
            if all(any(a <= s < z for a, z in ranges) for s in sites) and not any(a <= target < z for a, z in ranges) \
                    and image.root(target) == target:
                ranges.append(image.extent(target))
                grew = True
    return [handler] + sorted(ranges[1:])


def _boundary(image: Image, pos: int) -> int | None:
    """pos 를 품은 명령의 시작. 앞쪽 여러 자리에서 풀어 내려와 가장 많이 닿는 경계다(x86 의 풀이는 몇 명령 안에 제 경계로 모인다)."""
    votes: dict[int, int] = {}
    for start in range(max(0, pos - 40), pos - 15):
        for address, size, _mnemonic, _operands in _lite.disasm_lite(image.data[start:pos + 16], start):
            if address + size > pos:
                if address <= pos:
                    votes[address] = votes.get(address, 0) + 1
                break
    return max(votes, key=lambda a: (votes[a], -a)) if votes else None


def _holds(ins, value: int) -> tuple[int, int] | None:
    """명령이 value 를 상수(imm)나 메모리 자리(disp. rip 상대는 아니다)로 들고 있으면 (명령 안의 자리, 크기 1 또는 4).

    call · jmp · 조건 분기의 거리는 상수가 아니다(`je +0x24` 는 0x24 를 "들고" 있지 않다).
    """
    if ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP):
        return None
    rip = any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    for offset, size in ((ins.imm_offset, ins.imm_size), (ins.disp_offset, 0 if rip else ins.disp_size)):
        if size in (1, 4) and offset and (size == 4 or value < 0x80) \
                and int.from_bytes(bytes(ins.bytes[offset:offset + size]), "little") == value:
            return offset, size
    return None


def _constant_words(ins, held: tuple[int, int] | None) -> list[str]:
    """명령 하나의 서명 글. 든 상수는 읽어 낼 자리, rip 상대 거리와 call · jmp 의 4바이트 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    spans: list[tuple[int, int, list[str]]] = []
    if held:
        spans.append((held[0], held[1], ["[u32]" if held[1] == 4 else "[u8]"]))
    if ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands):
        spans.append((ins.disp_offset, 4, ["?"] * 4))
    elif (ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands \
            and ins.operands[0].type == X.X86_OP_IMM:
        spans.append((ins.size - 4, 4, ["?"] * 4))
    for offset, size, words in sorted(spans, reverse=True):      # 뒤에서부터 바꿔야 앞의 자리가 밀리지 않는다
        out[offset:offset + size] = words
    return out


def _grow(image: Image, first: int, constants: list[int], *, fewest: int, most: int, fixed: int, longest: int, within: int,
          unique: bool, holding: Sequence[int] = (), back: int = 0, through_jumps: bool = False) -> tuple[int, str] | None:
    """first 의 명령부터 constants 를 차례로 든 명령들을 지나, (unique 면) holding 의 상수를 든 명령들도 지나고 실행 구역에서
    한 번만 맞을 때까지 늘린 서명의 (시작, 글). back 이면 first 보다 그만큼 앞선 명령부터 시작한다."""
    start = _back(image, first, back) if back else first
    if start is None:
        return None
    words: list[str] = []
    length, wanted, since = 0, 0, 0
    missing = list(holding)
    for n, ins in enumerate(_md.disasm(image.data[start:start + 200], start), start=1):
        reached = ins.address >= first
        held = _holds(ins, constants[wanted]) if reached and wanted < len(constants) else None
        if ins.address == first and (held is None or held[1] != 4):
            return None                        # 첫 명령이 첫 상수를 4바이트로 들고 있어야 한다
        if reached and wanted < len(constants) and held is None:
            since += 1
            if since > within:
                return None                    # 다음 상수가 가까이에 없다
        if length + ins.size > longest:
            return None
        words += _constant_words(ins, held)
        length += ins.size
        if held:
            wanted, since = wanted + 1, 0
        else:
            missing = [value for value in missing if _holds(ins, value) is None]
        if wanted == len(constants):
            text = " ".join(words)
            if not unique:
                return start, text
            if not missing and n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                return start, text
        if n >= most or _stops(ins, through_jumps):
            return None
    return None


def mine_constants(image: Image, constants: list[int], *, exclude: Sequence[tuple[int, int]] = (), fewest: int = 3, most: int = 9,
                   fixed: int = 8, longest: int = 60, within: int = 4, sites: int = 400, holding: Sequence[int] = (),
                   back: int = 0, through_jumps: bool = False) -> list[Candidate]:
    """constants(하나 또는 둘 — 구조체 안의 자리 · 간격)를 차례로 든 명령들에서 시작해, 한 번만 맞는 가장 짧은 서명을 자리마다.

    첫 상수는 4바이트로 든 것만 찾는다(imul r,r,간격 · [r+자리]). 다음 상수는 그 뒤 명령 within 개 안에 있어야 한다.
    상수의 자리는 읽어 낼 자리([u32] · [u8])가 된다. 뜻이 같은 코드인지는 사람이 본다(srkit sig-mine 이 명령을 함께 보인다) —
    값만 우연히 같은 코드도 후보로 나온다. holding · back · through_jumps 는 mine_address 의 것과 같다.
    """
    options = dict(fewest=fewest, most=most, fixed=fixed, longest=longest, within=within)
    needle = struct.pack("<I", constants[0])
    starts: list[int] = []
    seen: set[int] = set()
    for lo, hi in image.code:
        for m in re.finditer(re.escape(needle), image.data[lo:hi]):
            pos = lo + m.start()
            if any(a <= pos < z for a, z in exclude):
                continue
            start = _boundary(image, pos)
            if start is None or start in seen:
                continue
            seen.add(start)
            first = next(_md.disasm(image.data[start:start + 16], start), None)
            held = _holds(first, constants[0]) if first is not None else None
            if held == (pos - start, 4) and _grow(image, start, constants, unique=False, **options):
                starts.append(start)                   # 상수를 모두 든 자리만 남긴다 — 고르게 고르는 것은 그 뒤다
    found: list[Candidate] = []
    for first in starts[::max(1, len(starts) // sites)]:
        grown = _grow(image, first, constants, unique=True, holding=holding, back=back, through_jumps=through_jumps, **options)
        if grown:
            start, text = grown
            length = sum(4 if w.startswith("[rip") or w == "[u32]" else 1 for w in text.split())
            found.append(Candidate(image.root(start), start, length, text))
    return found


def listing(image: Image, candidate: Candidate) -> str:
    """후보가 덮는 명령들을 한 줄로(사람이 뜻을 보고 고른다). 저장소에는 넣지 않는다."""
    return "; ".join(f"{ins.mnemonic} {ins.op_str}".strip()
                     for ins in _md.disasm(image.data[candidate.at:candidate.at + candidate.length], candidate.at))
