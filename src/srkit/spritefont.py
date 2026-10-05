"""DirectXTK ``.spritefont`` (DXTKfont) 읽기·쓰기와 글리프 추가.

파일 구조: "DXTKfont" | u32 글리프 수 | 글리프[32바이트] | f32 줄 간격 | u32 기본 문자
          | u32 폭 | u32 높이 | u32 DXGI 형식 | u32 stride | u32 rows | 텍스처 데이터
게임 글꼴은 모두 BC2(74) "CompressedMono" — 4x4 블록마다 4비트 알파 16개 + 고정 색 팔레트.
"""
from __future__ import annotations

import statistics
import struct
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

MAGIC = b"DXTKfont"
DXGI_R8G8B8A8_UNORM = 28
DXGI_BC2_UNORM = 74
GLYPH = struct.Struct("<I4i3f")
PAD = 2  # 글리프 사이 여백(px). 게임이 축소 렌더링하므로 번짐 방지용.


@dataclass(frozen=True)
class Glyph:
    char: int
    left: int
    top: int
    right: int
    bottom: int
    xoff: float
    yoff: float
    xadv: float

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass
class SpriteFont:
    glyphs: list[Glyph]
    line_spacing: float
    default_char: int
    alpha: np.ndarray           # (높이, 폭) uint8
    premultiplied: bool = True  # BC2 모노 양자화 방식 (원본 도구의 /NoPremultiply 여부)

    def find(self, char: int) -> Glyph | None:
        return self._index().get(char)

    def _index(self) -> dict[int, Glyph]:
        return {g.char: g for g in self.glyphs}

    def bitmap(self, g: Glyph) -> np.ndarray:
        return self.alpha[g.top:g.bottom, g.left:g.right]


def _bc2_decode(data: bytes, width: int, height: int) -> tuple[np.ndarray, bool]:
    blocks = np.frombuffer(data, dtype=np.uint8).reshape(height // 4, width // 4, 16)
    a = blocks[:, :, :8]
    nib = np.empty((height // 4, width // 4, 16), dtype=np.uint8)
    nib[:, :, 0::2] = a & 0x0F
    nib[:, :, 1::2] = a >> 4
    alpha = nib.reshape(height // 4, width // 4, 4, 4).transpose(0, 2, 1, 3).reshape(height, width) * 17
    premultiplied = bool(blocks[:, :, 12:].any())
    return alpha.astype(np.uint8), premultiplied


def _bc2_encode(alpha: np.ndarray, premultiplied: bool) -> bytes:
    h, w = alpha.shape
    v = alpha.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3).reshape(h // 4, w // 4, 16)
    if premultiplied:
        # MakeSpriteFont 와 같은 2비트 양자화: (알파 니블, 색 인덱스)
        level = np.digitize(v, [256 // 6, 256 // 2, 256 * 5 // 6])
        nib = np.array([0, 5, 10, 15], dtype=np.uint8)[level]
        rgb = np.array([1, 3, 2, 0], dtype=np.uint32)[level]
    else:
        nib = (v >> 4).astype(np.uint8)
        rgb = np.zeros(v.shape, dtype=np.uint32)
    blocks = np.zeros((h // 4, w // 4, 16), dtype=np.uint8)
    blocks[:, :, :8] = nib[:, :, 0::2] | (nib[:, :, 1::2] << 4)
    blocks[:, :, 8:10] = 0xFF
    bits = (rgb << (np.arange(16, dtype=np.uint32) * 2)).sum(axis=2, dtype=np.uint32)
    blocks[:, :, 12:] = bits[:, :, None].view(np.uint8).reshape(h // 4, w // 4, 4)
    return blocks.tobytes()


def load(path: Path | str) -> SpriteFont:
    data = Path(path).read_bytes()
    if data[:8] != MAGIC:
        raise ValueError(f"spritefont 가 아닙니다: {path}")
    (count,) = struct.unpack_from("<I", data, 8)
    glyphs = [Glyph(*GLYPH.unpack_from(data, 12 + i * GLYPH.size)) for i in range(count)]
    o = 12 + count * GLYPH.size
    line_spacing, default_char, width, height, fmt, stride, rows = struct.unpack_from("<fI5I", data, o)
    tex = data[o + 28:o + 28 + stride * rows]
    if fmt == DXGI_BC2_UNORM:
        alpha, premultiplied = _bc2_decode(tex, width, height)
    elif fmt == DXGI_R8G8B8A8_UNORM:
        alpha = np.frombuffer(tex, dtype=np.uint8).reshape(height, width, 4)[:, :, 3].copy()
        premultiplied = True
    else:
        raise ValueError(f"지원하지 않는 텍스처 형식 {fmt}: {path}")
    return SpriteFont(glyphs, line_spacing, default_char, alpha, premultiplied)


def dumps(font: SpriteFont) -> bytes:
    h, w = font.alpha.shape
    if w % 4 or h % 4:
        raise ValueError("BC2 텍스처 크기는 4의 배수여야 합니다")
    glyphs = sorted(font.glyphs, key=lambda g: g.char)  # DirectXTK 는 이진 탐색을 쓴다
    out = bytearray(MAGIC)
    out += struct.pack("<I", len(glyphs))
    for g in glyphs:
        out += GLYPH.pack(g.char, g.left, g.top, g.right, g.bottom, g.xoff, g.yoff, g.xadv)
    out += struct.pack("<fI5I", font.line_spacing, font.default_char, w, h, DXGI_BC2_UNORM, w * 4, h // 4)
    out += _bc2_encode(font.alpha, font.premultiplied)
    return bytes(out)


def save(font: SpriteFont, path: Path | str) -> None:
    Path(path).write_bytes(dumps(font))


@dataclass(frozen=True)
class NewGlyph:
    char: int
    bitmap: np.ndarray  # (h, w) uint8, 비어 있으면 1x1 투명
    xoff: float
    yoff: float
    xadv: float


def metrics(font: SpriteFont) -> tuple[int, int]:
    """원본 라틴 글리프에서 (기준선 y, 대문자 높이) 를 추정한다."""
    caps = [g for g in (font.find(ord(c)) for c in "HEFTILBDZ") if g and g.height > 1]
    if not caps:
        return round(font.line_spacing * 0.8), round(font.line_spacing * 0.55)
    baseline = round(statistics.median(g.yoff + g.height for g in caps))
    return baseline, round(statistics.median(g.height for g in caps))


def left_pad(font: SpriteFont) -> int:
    """원본 글리프에 공통으로 들어 있는 왼쪽 여백(px).

    원본은 GDI+ 로 그려져 모든 글리프의 XOffset 에 약 em/6 이 더해져 있다(XAdvance 가 그만큼 작다).
    새 글리프도 같은 만큼 밀어야 라틴 문자와 간격이 맞는다. 왼쪽 베어링이 거의 0 인 글자로 추정한다.
    """
    flat = [g.xoff for g in (font.find(ord(c)) for c in "AVWXYTvwxy") if g and g.width > 1]
    return round(statistics.median(flat)) if flat else 0


def hangul_em(font: SpriteFont, cap_ratio: float = 0.733) -> int:
    """라틴 대문자 높이에 맞춘 한글 글꼴 크기(px). cap_ratio 는 한글 글꼴의 대문자 높이/em."""
    _, cap = metrics(font)
    return max(8, int(min(cap / cap_ratio, font.line_spacing * 0.80)))


def render_glyphs(ttf: Path | str, em_px: int, chars: str, baseline: int, weight: int | None = None,
                  pad: int = 0) -> list[NewGlyph]:
    face = ImageFont.truetype(str(ttf), em_px)
    if weight is not None:
        try:
            axes = face.get_variation_axes()
        except OSError:
            axes = []
        if axes:
            face.set_variation_by_axes([weight if b"wght" in a.get("name", b"").lower() or len(axes) == 1
                                        else a["default"] for a in axes])
    out: list[NewGlyph] = []
    for ch in chars:
        x0, y0, x1, y1 = face.getbbox(ch, anchor="ls")
        adv = face.getlength(ch)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            out.append(NewGlyph(ord(ch), np.zeros((1, 1), np.uint8), 0.0, float(baseline), adv - 1))
            continue
        img = Image.new("L", (w, h), 0)
        ImageDraw.Draw(img).text((-x0, -y0), ch, font=face, fill=255, anchor="ls")
        out.append(NewGlyph(ord(ch), np.asarray(img, dtype=np.uint8),
                            float(pad + x0), float(baseline + y0), adv - x0 - w - pad))
    return out


def blank_glyph(char: int, advance: float) -> NewGlyph:
    """그려지는 픽셀 없이 폭만 차지하는 글리프(폭 측정용 자리표시)."""
    return NewGlyph(char, np.zeros((1, 1), np.uint8), 0.0, 0.0, advance - 1)


def augment(base: SpriteFont, extra: list[NewGlyph]) -> SpriteFont:
    """원본 글리프 픽셀은 그대로 두고 새 글리프를 더해 텍스처를 다시 채운다(같은 문자는 새 것으로 대체)."""
    items: dict[int, NewGlyph] = {
        g.char: NewGlyph(g.char, base.bitmap(g), g.xoff, g.yoff, g.xadv) for g in base.glyphs
    }
    items.update({n.char: n for n in extra})
    order = sorted(items.values(), key=lambda n: (-n.bitmap.shape[0], n.char))
    area = sum((n.bitmap.shape[0] + PAD) * (n.bitmap.shape[1] + PAD) for n in order)
    width = next(w for w in (256, 512, 1024, 2048, 4096, 8192) if w * w >= area * 1.15 or w == 8192)

    placed: list[tuple[NewGlyph, int, int]] = []
    x = y = PAD
    row_h = 0
    for n in order:
        h, w = n.bitmap.shape
        if x + w + PAD > width:
            x, y, row_h = PAD, y + row_h + PAD, 0
        placed.append((n, x, y))
        x += w + PAD
        row_h = max(row_h, h)
    height = -(-(y + row_h + PAD) // 4) * 4

    alpha = np.zeros((height, width), dtype=np.uint8)
    glyphs: list[Glyph] = []
    for n, gx, gy in placed:
        h, w = n.bitmap.shape
        alpha[gy:gy + h, gx:gx + w] = n.bitmap
        glyphs.append(Glyph(n.char, gx, gy, gx + w, gy + h, n.xoff, n.yoff, n.xadv))
    return replace(base, glyphs=sorted(glyphs, key=lambda g: g.char), alpha=alpha)


def render_text(font: SpriteFont, text: str, *, bg: int = 24, fg: int = 235) -> Image.Image:
    """DirectXTK SpriteFont 의 배치 규칙으로 문자열을 그린 미리보기(검증용)."""
    index = font._index()
    default = index.get(font.default_char)
    pen: list[tuple[Glyph, int, int]] = []
    x = y = 0.0
    max_x = 1.0
    for ch in text:
        if ch == "\r":
            continue
        if ch in ("\n", "¶"):
            x, y = 0.0, y + font.line_spacing
            continue
        g = index.get(ord(ch), default)
        if g is None:
            continue
        x = max(x + g.xoff, 0.0)
        pen.append((g, round(x), round(y + g.yoff)))
        x += g.width + g.xadv
        max_x = max(max_x, x)
    canvas = np.zeros((int(y + font.line_spacing) + 4, int(max_x) + 4), dtype=np.uint8)
    for g, gx, gy in pen:
        bmp = font.bitmap(g)
        gy0, gx0 = max(gy, 0), max(gx, 0)
        region = canvas[gy0:gy + g.height, gx0:gx + g.width]
        src = bmp[gy0 - gy:gy0 - gy + region.shape[0], gx0 - gx:gx0 - gx + region.shape[1]]
        np.maximum(region, src, out=region)
    out = (bg + (fg - bg) * (canvas.astype(np.float32) / 255.0)).astype(np.uint8)
    return Image.fromarray(out, "L")
