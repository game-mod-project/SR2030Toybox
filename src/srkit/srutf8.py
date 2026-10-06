"""SR-UTF8: 게임 엔진의 바이트 단위 처리와 충돌하지 않도록 조정한 UTF-8 변형.

엔진은 줄바꿈 기호 ``¶`` 를 **바이트 0xB6** 으로 직접 비교한다(줄바꿈 계산 루틴).
표준 UTF-8 은 '부·북·분·불·추·출·충·권' 등 흔한 음절의 연속 바이트에 0xB6 이 나오므로 그대로 쓰면 글자가 쪼개진다.

엔진은 또 지도 라벨(나라·도시 이름)을 **바이트 단위로 대문자화**한다(빌드 21347933 의 RVA 0x697c25, 0x6984c9 두 곳,
같은 표): 9A→8A 9E→8E E1→C1 E2→C2 E4→C4 E7→C7 E9→C9 EA→CA EB→CB ED→CD EE→D8 F1→D1 F3→D3 F4→D4 F6→D6 FA→DA FC→DC FD→DD.
표준 UTF-8 의 한글 선두 바이트 EA·EB·ED 와 연속 바이트 9A·9E 가 여기에 걸려, 지도를 축소하면 나라 이름이 깨졌다.

규칙
- ``¶`` (U+00B6) 는 단일 바이트 0xB6 으로 쓴다.
- 그 외 비ASCII 문자는 UTF-8 로 쓰되
  - 3바이트 문자의 선두 바이트는 대문자화에 걸리지 않는 값으로 바꿔 쓴다: EA→E5, EB→E6, ED→E8, E2→E0 (EC 는 그대로).
  - 연속 바이트 0xB6 은 0xFF, 0x9A 는 0xF7, 0x9E 는 0xFE 로 바꿔 쓴다(셋 다 게임 데이터에 나오지 않고 대문자화에도 안 걸린다).
- 바꿔 쓴 선두 바이트 자리를 원래 쓰던 문자(U+0800–0FFF, U+5000–6FFF, U+8000–8FFF: 한자 일부)는 쓸 수 없다 → ``unsupported``.

디코더는 native/srhook/srdecode.c 와 같은 규칙을 구현한다(게임 안에서는 DLL 이 수행).
유효한 시퀀스가 아니면 해당 바이트를 CP1252 문자로 취급하므로 원본 게임 데이터(CP1252)도 그대로 읽힌다.
바꿔 쓰기 전의 바이트(선두 EA·EB·ED·E2, 연속 9A·9E)도 그대로 읽는다 — 이전 빌드가 남긴 문자열(저장 파일 등)을 위해서다.
"""
from __future__ import annotations

PARA = 0xB6
# 폭 측정 전용 자리표시 문자 (한 바이트만 넘어온 경우)
PH_CELL = 0xE000  # 한글 한 칸 폭
PH_ZERO = 0xE001  # 폭 0

LEAD_IN = {0xE5: 0xEA, 0xE6: 0xEB, 0xE8: 0xED, 0xE0: 0xE2}     # 파일의 선두 바이트 → 실제 UTF-8 선두 바이트
LEAD_OUT = {real: written for written, real in LEAD_IN.items()}
CONT_IN = {0xFF: 0xB6, 0xF7: 0x9A, 0xFE: 0x9E}                  # 파일의 연속 바이트 → 실제 UTF-8 연속 바이트
CONT_OUT = {real: written for written, real in CONT_IN.items()}


def unsupported(text: str) -> list[str]:
    """SR-UTF8 로 쓸 수 없는 문자들(바꿔 쓴 선두 바이트 자리의 원래 주인)."""
    return sorted({ch for ch in text if 0x800 <= ord(ch) <= 0xFFFF and ch.encode("utf-8")[0] in LEAD_IN})


def encode(text: str) -> bytes:
    out = bytearray()
    for ch in text:
        cp = ord(ch)
        if cp < 0x80 or cp == PARA:
            out.append(cp)
            continue
        raw = ch.encode("utf-8")
        lead = raw[0]
        if len(raw) == 3:
            if lead in LEAD_IN:
                raise ValueError(f"SR-UTF8 로 쓸 수 없는 문자입니다: {ch!r} (U+{cp:04X})")
            lead = LEAD_OUT.get(lead, lead)
        out.append(lead)
        out.extend(CONT_OUT.get(b, b) for b in raw[1:])
    return bytes(out)


def _is_cont(b: int) -> bool:
    return (0x80 <= b <= 0xBF and b != PARA) or b in CONT_IN


def _cont(b: int) -> int:
    return CONT_IN.get(b, b) & 0x3F


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
                cp = ((LEAD_IN.get(b, b) & 0x0F) << 12) | (_cont(data[i + 1]) << 6) | _cont(data[i + 2])
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
