"""그림 글자 한글화: 스프라이트 시트(SRBITS5.png) 안의 영어 문구를 지우고 같은 자리에 한글을 그린다.

어느 영역이 어떤 그림인지는 게임의 INI\\Bitmaps.csv 가 정한다(항목마다 상태별 사각형과 프레임 수).
무엇을 무슨 말로 바꿀지는 mods/korean/sprites.toml 에 적는다.
"""
from __future__ import annotations

import csv
import io
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PAGE = "5"
SHEET = "SRBITS5.png"
STATES = (("normal", 5), ("selected", 9), ("hover", 13), ("hover_selected", 17), ("greyed", 21))
GAP = 2  # 프레임 사이 간격(px)


@dataclass(frozen=True)
class Entry:
    id: int
    frames: int
    per_row: int
    rects: dict[str, tuple[int, int, int, int]]  # 상태 → 첫 프레임의 (x, y, w, h)

    def box(self, state: str, i: int) -> tuple[int, int, int, int]:
        x, y, w, h = self.rects[state]
        return x + (i % self.per_row) * (w + GAP), y + (i // self.per_row) * (h + GAP), w, h


def read_entries(bitmaps_csv: str, page: str = PAGE) -> dict[int, Entry]:
    out = {}
    for r in csv.reader(io.StringIO(bitmaps_csv)):
        if len(r) < 25 or not r[0].strip().isdigit() or r[1].strip() != page:
            continue
        rects = {}
        for state, i in STATES:
            if all(v.strip() for v in r[i:i + 4]):
                x1, y1, x2, y2 = (int(v) for v in r[i:i + 4])
                rects[state] = (x1, y1, x2 - x1, y2 - y1)
        if rects:
            out[int(r[0])] = Entry(int(r[0]), int(r[2] or 1), int(r[3] or 1), rects)
    return out


# ---------------------------------------------------------------- 그리기 도구

def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _blur(mask: np.ndarray, radius: float, shift: tuple[int, int] = (0, 0)) -> np.ndarray:
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius))
    out = np.asarray(img, dtype=np.float32) / 255
    if shift != (0, 0):
        out = np.roll(out, (shift[1], shift[0]), axis=(0, 1))
        if shift[1] > 0:
            out[:shift[1]] = 0
        if shift[0] > 0:
            out[:, :shift[0]] = 0
    return out


def _over(dst: np.ndarray, color, mask: np.ndarray) -> None:
    """dst(H,W,4 float, 곧은 알파) 위에 color 를 mask 만큼 덧칠한다."""
    m = np.clip(mask, 0, 1)[..., None]
    a = dst[..., 3:4]
    out_a = m + a * (1 - m)
    rgb = (np.asarray(color, dtype=np.float32) * m + dst[..., :3] * a * (1 - m)) / np.maximum(out_a, 1e-6)
    dst[..., :3] = rgb
    dst[..., 3:4] = out_a


class Face:
    def __init__(self, path: str, weight: int | None):
        self.path, self.weight = path, weight
        self._ratio: float | None = None

    def at(self, em: int) -> ImageFont.FreeTypeFont:
        font = ImageFont.truetype(self.path, max(6, em))
        if self.weight is not None:
            try:
                axes = font.get_variation_axes()
            except OSError:
                axes = []
            if axes:
                font.set_variation_by_axes([self.weight if len(axes) == 1 or b"eight" in a.get("name", b"")
                                            else a["default"] for a in axes])
        return font

    def ink_ratio(self) -> float:
        """한글 한 글자의 실제 높이 / em."""
        if self._ratio is None:
            x0, y0, x1, y1 = self.at(200).getbbox("한글", anchor="ls")
            self._ratio = (y1 - y0) / 200
        return self._ratio

    def mask(self, text: str, shape: tuple[int, int], ink_h: float, max_w: float, *, cy: float,
             left: float | None = None, cx: float | None = None) -> tuple[np.ndarray, tuple[int, int, int, int]]:
        """text 를 글자 높이 ink_h 로(폭이 넘치면 줄여서) 그린 마스크와 그 사각형(x0, y0, x1, y1)."""
        em = round(ink_h / self.ink_ratio())
        while True:
            font = self.at(em)
            x0, y0, x1, y1 = font.getbbox(text, anchor="ls")
            if x1 - x0 <= max_w or em <= 8:
                break
            em -= 1
        ox = (left if left is not None else cx - (x1 - x0) / 2) - x0
        oy = cy - (y0 + y1) / 2
        img = Image.new("L", (shape[1], shape[0]), 0)
        ImageDraw.Draw(img).text((round(ox), round(oy)), text, font=font, fill=255, anchor="ls")
        box = (round(ox) + x0, round(oy) + y0, round(ox) + x1, round(oy) + y1)
        return np.asarray(img, dtype=np.float32) / 255, box


def _underline(shape: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    """선택 상태의 밑줄(원본과 같은 꼴: 꼬리가 달린 두 줄)."""
    x0, _, x1, y1 = box
    h, w = shape
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    y = min(y1 + 3, h - 6)
    d.line([(x0 - 1, y), (min(x1 + 10, w - 6), y)], fill=255, width=2)
    d.line([(min(x1 + 10, w - 6), y), (min(x1 + 14, w - 2), y - 4)], fill=255, width=2)
    d.line([(x0 + 3, y + 4), (x0 + round((x1 - x0) * 0.6), y + 4)], fill=255, width=2)
    d.line([(x0 + 3, y + 4), (x0 - 1, min(y + 8, h - 1))], fill=255, width=2)
    return np.asarray(img, dtype=np.float32) / 255


# ---------------------------------------------------------------- 종류별 처리

def _core(frame: np.ndarray) -> np.ndarray:
    """투명 바탕 글자의 '글자 본체'(그림자·광채 제외) 마스크."""
    return (frame[..., 3] > 0.5) & (_luma(frame[..., :3]) > 0.45)


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None


def render_float(ref: np.ndarray, orig: np.ndarray, text: str, state: str, face: Face, align: str) -> np.ndarray:
    """ref = 같은 프레임의 보통 상태 원본(글자 위치·높이 기준), orig = 이 상태의 원본(색 표본)."""
    box = _bbox(_core(ref))
    if box is None:
        return orig
    h, w = ref.shape[:2]
    x0, y0, x1, y1 = box
    core = _core(orig)
    color = orig[..., :3][core].mean(axis=0) if core.any() else np.ones(3, np.float32)
    underlined = state in ("selected", "hover_selected")
    ink_h = min((y1 - y0) * 1.15, h - (14 if underlined else 6))
    kwargs = {"cx": w / 2} if align == "center" else {"left": float(x0)}
    mask, tbox = face.mask(text, (h, w), ink_h, w - x0 - 16, cy=(y0 + y1) / 2 - (2 if underlined else 0), **kwargs)
    if underlined:
        mask = np.maximum(mask, _underline((h, w), tbox))
    out = np.zeros_like(ref)
    if state in ("hover", "hover_selected"):
        halo = orig[..., :3][(orig[..., 3] > 0.25) & ~core]
        glow = halo.mean(axis=0) if len(halo) else np.array([0.1, 0.35, 0.9], np.float32)
        _over(out, glow, np.clip(_blur(mask, 3.0) * 2.2, 0, 1))
    else:
        _over(out, (0, 0, 0), _blur(mask, 1.6, (2, 2)) * 0.85)
    _over(out, color, mask)
    return out


def _find_text(frame: np.ndarray, zone: tuple[float, float], margin: int) -> tuple[np.ndarray, tuple[int, int, int, int]] | None:
    """판 위의 밝은 글자를 찾아 (마스크, 사각형) 을 돌려준다."""
    h, w = frame.shape[:2]
    ya, yb = round(h * zone[0]), round(h * zone[1])
    lum = _luma(frame[..., :3])
    area = np.zeros((h, w), bool)
    area[ya:yb, margin:w - margin] = True
    # 줄의 '판 밝기'는 중앙값이 아니라 아래쪽 분위수로 잡는다: 긴 문구는 줄의 절반 이상을 글자가 덮는다
    base = np.quantile(lum[ya:yb, margin:w - margin], 0.25, axis=1, keepdims=True)
    mask = np.zeros((h, w), bool)
    # 글자는 판보다 뚜렷이 밝고, 절대 밝기로도 흰색에 가깝다(판을 두른 금속 테두리는 여기서 걸러진다)
    mask[ya:yb, margin:w - margin] = lum[ya:yb, margin:w - margin] > np.maximum(base + 0.16, 0.62)
    mask &= area
    cols = np.nonzero(mask.sum(axis=0) >= 2)[0]
    rows = np.nonzero(mask.sum(axis=1) >= 2)[0]
    if len(cols) < 4 or len(rows) < 3:
        return None
    return mask, (int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1)


def _erase(frame: np.ndarray, box: tuple[int, int, int, int], margin: int) -> None:
    """글자 영역을 왼쪽(없으면 오른쪽)의 빈 판을 거울처럼 이어 붙여 덮는다.

    판이 반투명이고 글자만 불투명한 그림이 있어, 색뿐 아니라 알파까지 함께 덮는다.
    """
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = box
    ex0, ex1 = max(margin, x0 - 4), min(w - margin, x1 + 6)
    ey0, ey1 = max(0, y0 - 3), min(h, y1 + 5)
    left_room, right_room = ex0 - margin, (w - margin) - ex1
    if max(left_room, right_room) < 3:
        # 글자가 판을 가득 채워 빈 자리가 없다: 줄마다 글자가 아닌 픽셀(어두운 쪽 절반)의 중앙값으로 칠한다
        rows = frame[ey0:ey1, margin:w - margin]
        lum = _luma(rows[..., :3])
        dark = lum <= np.median(lum, axis=1, keepdims=True)
        for r in range(ey1 - ey0):
            frame[ey0 + r, ex0:ex1] = np.median(rows[r][dark[r]], axis=0)
        return
    sw = min(18, max(left_room, right_room))
    strip = (frame[ey0:ey1, ex0 - sw:ex0] if left_room >= right_room else frame[ey0:ey1, ex1:ex1 + sw][:, ::-1]).copy()
    k = np.arange(ex1 - ex0)
    idx = np.where((k // sw) % 2 == 0, sw - 1 - (k % sw), k % sw)  # 경계에서 이어지도록 거울 타일
    frame[ey0:ey1, ex0:ex1] = strip[:, idx]


def _stamp(out: np.ndarray, layer: np.ndarray) -> None:
    """글자 층(layer)을 그림 위에 찍는다. 글자가 놓인 자리는 그만큼 불투명해진다."""
    a = layer[..., 3:4]
    out[..., :3] = layer[..., :3] * a + out[..., :3] * (1 - a)
    out[..., 3:4] = np.maximum(out[..., 3:4], a)


def text_rows(frames: list[np.ndarray], zone: tuple[float, float], margin: int = 7) -> tuple[float, float] | None:
    """같은 묶음의 프레임들에서 글자가 놓인 세로 범위(비율)의 중앙값. 사진의 밝은 부분에 속지 않게 한다."""
    found = [f for f in (_find_text(fr, zone, margin) for fr in frames) if f]
    if not found:
        return None
    h = frames[0].shape[0]
    y0 = float(np.median([b[1] for _, b in found]))
    y1 = float(np.median([b[3] for _, b in found]))
    return max(0.0, (y0 - 2) / h), min(1.0, (y1 + 2) / h)


def render_plate(orig: np.ndarray, text: str, face: Face, zone: tuple[float, float],
                 rows: tuple[float, float] | None = None, margin: int = 7) -> np.ndarray:
    """zone = 글자가 들어갈 수 있는 세로 범위, rows = 묶음에서 실제로 글자가 놓인 범위(있으면 그 안에서만 찾는다)."""
    found = _find_text(orig, rows or zone, margin)
    if found is None:
        return orig
    mask, (x0, y0, x1, y1) = found
    h, w = orig.shape[:2]
    lum = _luma(orig[..., :3])
    bright = mask & (lum >= np.quantile(lum[mask], 0.6))
    color = orig[..., :3][bright].mean(axis=0)
    out = orig.copy()
    _erase(out, (x0, y0, x1, y1), margin)
    ya, yb = round(h * zone[0]), round(h * zone[1])
    ink_h = min((y1 - y0) * 1.3, yb - ya - 6)
    tmask, _ = face.mask(text, (h, w), ink_h, w - 2 * margin - 10, cy=(y0 + y1) / 2, cx=(x0 + x1) / 2)
    layer = np.zeros_like(orig)
    _over(layer, (0, 0, 0), _blur(tmask, 1.3, (1, 2)) * 0.75)
    _over(layer, color, tmask)
    _stamp(out, layer)
    return out


def _letters(white: np.ndarray, min_h: int = 9, max_h: int = 46, max_w: int = 64) -> tuple[np.ndarray, float]:
    """흰 픽셀 덩어리 가운데 글자 크기인 것만 남긴다(흰 옷·하늘 같은 큰 덩어리는 버린다). (마스크, 글자 높이 중앙값)."""
    h, w = white.shape
    seen = np.zeros_like(white)
    keep = np.zeros_like(white)
    heights: list[int] = []
    for sy, sx in zip(*np.nonzero(white)):
        if seen[sy, sx]:
            continue
        stack, pixels = [(sy, sx)], []
        seen[sy, sx] = True
        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        ys, xs = zip(*pixels)
        if min_h <= max(ys) - min(ys) + 1 <= max_h and max(xs) - min(xs) + 1 <= max_w:
            keep[list(ys), list(xs)] = True
            heights.append(max(ys) - min(ys) + 1)
    return keep, float(np.median(heights)) if heights else 0.0


def _inpaint(rgb: np.ndarray, hole: np.ndarray) -> np.ndarray:
    """hole 안을 둘레의 색으로 부드럽게 메운다(가까운 둘레부터 점점 넓은 범위의 평균으로)."""
    out = rgb.copy()
    known = (~hole).astype(np.float32)
    todo = hole.copy()
    for radius in (2, 4, 8, 16, 32):
        weight = _blur(known, radius)
        fill = np.stack([_blur(rgb[..., c] * known, radius) for c in range(3)], axis=-1) / np.maximum(weight, 1e-4)[..., None]
        ready = todo & (weight > 0.12)
        out[ready] = fill[ready]
        todo &= ~ready
    return out


def render_photo(orig: np.ndarray, text: str, face: Face, zone: tuple[float, float], margin: int = 10) -> np.ndarray:
    """사진 위에 얹힌 글자: 글자 덩어리만 찾아 둘레 색으로 메우고, 그 자리 가운데에 한 줄로 쓴다."""
    h, w = orig.shape[:2]
    ya, yb = round(h * zone[0]), round(h * zone[1])
    rgb = orig[..., :3]
    white = np.zeros((h, w), bool)
    white[ya:yb, margin:w - margin] = (rgb[ya:yb, margin:w - margin].min(axis=-1) > 0.8)
    letters, cap_h = _letters(white)
    box = _bbox(letters)
    if box is None:
        return orig
    _, y0, _, y1 = box
    hole = _blur(letters.astype(np.float32), 2.5) > 0.04   # 글자 테두리와 그림자까지
    hole |= np.roll(hole, (3, 3), axis=(0, 1))
    out = orig.copy()
    out[..., :3] = _inpaint(rgb, hole)
    tmask, _ = face.mask(text, (h, w), cap_h * 1.45, w - 2 * margin - 16, cy=(y0 + y1) / 2, cx=w / 2)
    layer = np.zeros_like(orig)
    _over(layer, (0, 0, 0), np.clip(_blur(tmask, 5.0) * 1.8, 0, 0.75))   # 사진 위에서도 읽히게 어두운 번짐
    _over(layer, (0, 0, 0), _blur(tmask, 1.4, (2, 2)) * 0.9)
    _over(layer, (1, 1, 1), tmask)
    _stamp(out, layer)
    return out


# ---------------------------------------------------------------- 시트 처리

def _pick(value, skin: str, default):
    if isinstance(value, dict):
        return value.get(skin, default)
    return default if value is None else value


def localize_sheet(sheet: Image.Image, entries: dict[int, Entry], spec: dict, skin: str) -> tuple[Image.Image, list[str]]:
    """시트 한 장의 그림 글자를 바꾼다. (새 시트, 처리하지 못한 항목 설명) 을 돌려준다."""
    px = np.asarray(sheet.convert("RGBA"), dtype=np.float32) / 255
    src = px.copy()
    faces = {name: Face(f["path"], f.get("weight")) for name, f in spec["fonts"].items()}
    skipped = []
    for group in spec["group"]:
        entry = entries.get(group["id"])
        if entry is None:
            skipped.append(f"{skin}: Bitmaps.csv 에 {group['id']} 항목 없음")
            continue
        kind = _pick(group.get("kind"), skin, "plate")
        zone = tuple(_pick(group.get("zone"), skin, (0.0, 1.0)))
        face = faces[_pick(group.get("font"), skin, "sans")]
        count = min(len(group["texts"]), entry.frames)
        margin = int(_pick(group.get("margin"), skin, 7))
        rows = None
        if kind == "plate":
            boxes = [entry.box("normal", i) for i in range(count)]
            rows = text_rows([src[y:y + h, x:x + w] for x, y, w, h in boxes], zone, margin)
        for i, text in enumerate(group["texts"][:entry.frames]):
            rx, ry, rw, rh = entry.box("normal", i)
            ref = src[ry:ry + rh, rx:rx + rw]
            for state in entry.rects:
                x, y, w, h = entry.box(state, i)
                orig = src[y:y + h, x:x + w]
                if kind == "float":
                    new = render_float(ref, orig, text, state, face, group.get("align", "left"))
                elif kind == "photo":
                    new = render_photo(orig, text, face, zone)
                else:
                    new = render_plate(orig, text, face, zone, rows, margin)
                if new is orig:
                    skipped.append(f"{skin}: {group['id']} '{text}' ({state}) 글자를 찾지 못함")
                px[y:y + h, x:x + w] = new
    return Image.fromarray((np.clip(px, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA"), skipped


def localize(game_dir: Path, spec_path: Path, graphics_dir: Path) -> list[str]:
    """graphics_dir/<스킨>/SRBITS5.png 들을 한글판으로 바꿔 쓴다."""
    spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    raw = (game_dir / "INI" / "Bitmaps.csv").read_bytes().decode("cp1252", errors="replace")
    entries = read_entries(raw)
    notes = []
    for path in sorted(graphics_dir.glob(f"*/{SHEET}")):
        with Image.open(path) as sheet:
            new, skipped = localize_sheet(sheet, entries, spec, path.parent.name)
        new.save(path, optimize=True)
        notes += skipped
    return notes
