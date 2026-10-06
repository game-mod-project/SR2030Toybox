from pathlib import Path

import numpy as np
import pytest

from srkit import sprites

FONT = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
BITMAPS = (
    "// Id, Page, Frames, FramesPerRow, Speed, x1, y1, x2, y2, Sel…\n&&BITMAPS\n"
    '99,5,15,1,,2,2,304,38,306,2,608,38,610,2,912,38,914,2,1216,38,,,,,"//Lobby","x",302,36,,\n'
    '826,5,5,5,,2,1524,182,1784,,,,,2,1786,182,2046,,,,,912,1524,1092,1784,"//Main menu","x",180,260,,\n'
    '7,0,,,,256,0,512,192,,,,,,,,,,,,,,,,,"//Advisor2","hold",256,192,,\n'
)


@pytest.fixture(scope="module")
def face():
    if not FONT.is_file():
        pytest.skip(f"글꼴 없음: {FONT}")
    return sprites.Face(str(FONT), 900)


def test_entries_and_frame_boxes():
    entries = sprites.read_entries(BITMAPS)
    assert set(entries) == {99, 826}                       # 5번 페이지만
    tabs, cards = entries[99], entries[826]
    assert tabs.box("normal", 0) == (2, 2, 302, 36)
    assert tabs.box("hover_selected", 2) == (914, 2 + 2 * 38, 302, 36)   # 세로로 2px 간격
    assert cards.box("normal", 4) == (2 + 4 * 182, 1524, 180, 260)      # 한 줄에 5개
    assert set(cards.rects) == {"normal", "hover", "greyed"}


def _floating(text_box=(14, 9, 120, 25)) -> np.ndarray:
    frame = np.zeros((36, 302, 4), np.float32)
    x0, y0, x1, y1 = text_box
    frame[y0:y1, x0:x1] = 1.0                              # 흰 글자 본체
    return frame


def test_float_redraws_text_at_same_left_edge(face):
    ref = _floating()
    out = sprites.render_float(ref, ref, "옵션", "normal", face, "left")
    ink = out[..., 3] > 0.9
    xs = np.nonzero(ink.any(axis=0))[0]
    assert 12 <= xs.min() <= 17                            # 원본 글자의 왼쪽 끝에 맞춘다
    assert xs.max() < 110 and not out[:, 200:, 3].any()    # 짧은 한글: 원본 글자가 있던 오른쪽은 비어야 한다


def test_selected_state_adds_underline(face):
    ref = _floating()
    plain = sprites.render_float(ref, ref, "옵션", "normal", face, "left")
    selected = sprites.render_float(ref, ref, "옵션", "selected", face, "left")
    bottom = slice(30, 36)
    assert (selected[bottom, :, 3] > 0.9).sum() > (plain[bottom, :, 3] > 0.9).sum() + 20


def test_plate_erases_old_text_in_alpha_too(face):
    """판이 반투명이고 영어 글자만 불투명한 그림: 색과 알파 모두에서 옛 글자가 사라져야 한다."""
    frame = np.zeros((26, 172, 4), np.float32)
    frame[..., :3], frame[..., 3] = 0.3, 0.7               # 반투명 회색 판
    frame[7:19, 30:140] = 1.0                              # 판의 70% 를 덮는 넓은 흰 글자
    out = sprites.render_plate(frame, "시작", face, (0.0, 1.0))
    left_of_new_text = out[7:19, 32:58]                    # 옛 글자 자리였지만 새 글자는 없는 곳
    assert np.allclose(left_of_new_text[..., :3], 0.3, atol=0.02)
    assert np.allclose(left_of_new_text[..., 3], 0.7, atol=0.02)
    assert (out[..., 3] > 0.95).any()                      # 새 글자는 불투명하게 찍힌다


def test_plate_without_text_is_left_alone(face):
    frame = np.full((26, 172, 4), 0.3, np.float32)
    assert sprites.render_plate(frame, "시작", face, (0.0, 1.0)) is frame


def test_letters_keeps_glyph_sized_blobs_only():
    white = np.zeros((80, 200), bool)
    white[10:30, 10:22] = True                             # 글자 크기
    white[5:75, 100:190] = True                            # 흰 옷 같은 큰 덩어리
    keep, cap = sprites._letters(white)
    assert keep[15, 15] and not keep[40, 150] and cap == 20
