"""SR-UTF8: 게임 엔진의 바이트 단위 처리와 충돌하지 않도록 조정한 UTF-8 변형.

엔진은 줄바꿈 기호 ``¶`` 를 **바이트 0xB6** 으로 직접 비교한다(줄바꿈 계산 루틴).
표준 UTF-8 은 '부·북·분·불·추·출·충·권' 등 흔한 음절의 연속 바이트에 0xB6 이 나오므로 그대로 쓰면 글자가 쪼개진다.

규칙
- ``¶`` (U+00B6) 는 단일 바이트 0xB6 으로 쓴다.
- 그 외 비ASCII 문자는 UTF-8 로 쓰되, 연속 바이트 0xB6 은 0xFF 로 바꿔 쓴다.

디코더는 native/srhook/srdecode.c 와 같은 규칙을 구현한다(게임 안에서는 DLL 이 수행).
유효한 시퀀스가 아니면 해당 바이트를 CP1252 문자로 취급하므로 원본 게임 데이터(CP1252)도 그대로 읽힌다.
"""
from __future__ import annotations

PARA = 0xB6
ESC_CONT = 0xFF
# 폭 측정 전용 자리표시 문자 (한 바이트만 넘어온 경우)
PH_CELL = 0xE000  # 한글 한 칸 폭
PH_ZERO = 0xE001  # 폭 0


def encode(text: str) -> bytes:
    out = bytearray()
    for ch in text:
        cp = ord(ch)
        if cp < 0x80 or cp == PARA:
            out.append(cp)
            continue
        raw = ch.encode("utf-8")
        out.append(raw[0])
        out.extend(ESC_CONT if b == PARA else b for b in raw[1:])
    return bytes(out)


def _is_cont(b: int) -> bool:
    return (0x80 <= b <= 0xBF and b != PARA) or b == ESC_CONT


def _cont(b: int) -> int:
    return (PARA if b == ESC_CONT else b) & 0x3F


def cp1252_char(b: int) -> str:
    try:
        return bytes([b]).decode("cp1252")
    except UnicodeDecodeError:  # 0x81 0x8D 0x8F 0x90 0x9D: Windows 는 C1 제어문자로 매핑
        return chr(b)


def decode(data: bytes, *, measure: bool = False) -> str:
    """SR-UTF8 바이트열을 문자열로. measure=True 는 폭 측정 경로(CP_UTF8 호출)의 동작."""
    n = len(data)
    if measure and n == 1 and data[0] >= 0x80 and data[0] != PARA:
        b = data[0]
        if 0xE0 <= b <= 0xEF:
            return chr(PH_CELL)
        if _is_cont(b):
            return chr(PH_ZERO)
        return cp1252_char(b)

    out: list[str] = []
    i = 0
    multibyte = False  # 앞에서 멀티바이트 문자가 나왔는가 (= 한글이 섞인 문자열인가)
    while i < n:
        b = data[i]
        if b < 0x80 or b == PARA:
            out.append(chr(b))
            i += 1
            continue
        if 0xC2 <= b <= 0xDF and i + 1 < n and _is_cont(data[i + 1]):
            out.append(chr(((b & 0x1F) << 6) | _cont(data[i + 1])))
            i += 2
            multibyte = True
            continue
        if 0xE0 <= b <= 0xEF:
            if i + 2 < n and _is_cont(data[i + 1]) and _is_cont(data[i + 2]):
                cp = ((b & 0x0F) << 12) | (_cont(data[i + 1]) << 6) | _cont(data[i + 2])
                if cp >= 0x800 and not 0xD800 <= cp <= 0xDFFF:
                    out.append(chr(cp))
                    i += 3
                    multibyte = True
                    continue
            elif i + 2 == n and _is_cont(data[i + 1]):
                # 문자열이 음절 중간에서 잘린 경우: 깨진 꼬리는 버린다
                i += 2
                continue
            elif i + 1 == n and multibyte:
                # 한글 문자열의 맨 끝에 리드 바이트만 남음(게임이 칸에 맞춰 자른 것) → 버린다.
                # 한글이 없는 문자열이면 'Bogotá' 같은 원본 이름의 끝 글자이므로 아래에서 CP1252 로 살린다.
                i += 1
                continue
        if 0xF0 <= b <= 0xF4 and i + 3 < n and all(_is_cont(x) for x in data[i + 1:i + 4]):
            cp = ((b & 0x07) << 18) | (_cont(data[i + 1]) << 12) | (_cont(data[i + 2]) << 6) | _cont(data[i + 3])
            if 0x10000 <= cp <= 0x10FFFF:
                out.append(chr(cp))
                i += 4
                multibyte = True
                continue
        out.append(cp1252_char(b))
        i += 1
    return "".join(out)
