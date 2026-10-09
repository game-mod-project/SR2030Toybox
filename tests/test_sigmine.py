"""서명 뽑기(src/srkit/sigmine.py, 개발용): 주소를 가리키는 코드에서 한 번만 맞는 서명 후보를 찾는다."""
import argparse
import struct

import pytest

import toybox_fake_exe as fake
from srkit import cli, toybox

sigmine = pytest.importorskip("srkit.sigmine", reason="capstone 이 없다 (uv sync)")

G = fake.DATA + 0x40     # 가짜 전역


def code() -> bytes:
    """전역 G 를 쓰는 자리 다섯: A · B 는 뒤따르는 명령이 서로 다르고, C · D 는 똑같고, E 는 거리 뒤에 상수가 붙는 명령이다."""
    image = fake.shell([(0x1000, 0x1040), (0x1040, 0x1080), (0x1080, 0x10C0), (0x10C0, 0x1100), (0x1100, 0x1140)])
    end = fake.rip(image, 0x1000, bytes([0x48, 0x8B, 0x05]), G)             # A: mov rax,[G] / test rax,rax / je / mov ecx,[rax+10h] / ret
    fake.put(image, end, bytes([0x48, 0x85, 0xC0, 0x74, 0x10, 0x8B, 0x48, 0x10, 0xC3]))
    end = fake.rip(image, 0x1040, bytes([0x48, 0x8B, 0x05]), G)             # B: mov rax,[G] / mov eax,[rax+6Ch] / test eax,eax / jne / ret
    fake.put(image, end, bytes([0x8B, 0x40, 0x6C, 0x85, 0xC0, 0x75, 0x08, 0xC3]))
    for at in (0x1080, 0x10C0):                                             # C · D: mov rax,[G] / mov rcx,[rax] / test rcx,rcx / je / ret
        end = fake.rip(image, at, bytes([0x48, 0x8B, 0x05]), G)
        fake.put(image, end, bytes([0x48, 0x8B, 0x08, 0x48, 0x85, 0xC9, 0x74, 0x05, 0xC3]))
    end = fake.rip(image, 0x1100, bytes([0x83, 0x3D]), G, b"\x06")          # E: cmp dword ptr [G],6 / mov r15,rdx / mov r14,rcx / ret
    fake.put(image, end, bytes([0x4C, 0x8B, 0xFA, 0x4C, 0x8B, 0xF1, 0xC3]))
    return bytes(image)


@pytest.fixture(scope="module")
def image():
    return sigmine.Image(code())


def test_refs_find_every_instruction_that_points_at_the_address(image):
    assert image.refs(G) == [0x1003, 0x1043, 0x1083, 0x10C3, 0x1102]      # 4바이트 거리의 자리


def test_root_is_the_function_that_holds_the_place(image):
    assert image.root(0x1045) == 0x1040
    assert image.root(0x2F00) is None                                      # 함수 표에 없는 자리


def test_mining_gives_one_unique_signature_per_place_and_skips_ambiguous_places(image):
    found = {c.at: c for c in sigmine.mine_address(image, G)}
    assert {at: c.text for at, c in found.items()} == {
        0x1000: "48 8B 05 [rip] 48 85 C0 74 10",
        0x1040: "48 8B 05 [rip] 8B 40 6C 85 C0",
        0x1100: "83 3D [rip+1] 06 4C 8B FA 4C 8B F1"}       # C · D 는 똑같아서 어느 길이로도 한 번만 맞지 않는다
    assert {at: c.function for at, c in found.items()} == {0x1000: 0x1000, 0x1040: 0x1040, 0x1100: 0x1100}
    assert all(sigmine.count(image, c.text) == 1 for c in found.values())


def test_mining_skips_the_excluded_range(image):
    """치트 명령 처리 함수의 코드에서는 서명을 뽑지 않는다."""
    assert [c.at for c in sigmine.mine_address(image, G, exclude=(0x1000, 0x1040))] == [0x1040, 0x1100]


def test_count_agrees_with_the_dll_about_overlapping_matches():
    overlap = fake.shell([(0x1000, 0x1040)])
    fake.put(overlap, 0x1000, bytes([0xAA, 0xAA, 0xAA, 0x01]))
    image = sigmine.Image(bytes(overlap))
    assert sigmine.count(image, "AA AA [u8]") == 2                         # DLL 처럼 겹친 것까지 센다
    assert sigmine.count(image, "AA AA [u8]", exact=False) == 1            # 빠른 어림(뽑는 동안 먼저 거르는 데 쓴다)


def test_best_per_function_keeps_the_shortest_of_each_function():
    Candidate = sigmine.Candidate
    picks = sigmine.best_per_function([Candidate(0x1000, 0x1010, 30, "long"), Candidate(0x1000, 0x1000, 12, "short"),
                                       Candidate(0x1040, 0x1040, 12, "other"), Candidate(None, 0x2000, 5, "loose"),
                                       Candidate(None, 0x2100, 5, "loose too")])
    assert [(c.function, c.at) for c in picks] == [(None, 0x2000), (None, 0x2100), (0x1000, 0x1000), (0x1040, 0x1040)]


def test_handler_range_comes_from_the_cheat_anchor(image):
    assert sigmine.handler_range(image) is None                            # 치트가 없는 빌드
    anchored = fake.shell([(0x1000, 0x1040), (0x1040, 0x1100)])
    fake.put(anchored, fake.RDATA + 0x10, b"\0cheat allowcheats\0")
    fake.rip(anchored, 0x1050, bytes([0x48, 0x8D, 0x15]), fake.RDATA + 0x11)     # lea rdx,["cheat allowcheats"]
    assert sigmine.handler_range(sigmine.Image(bytes(anchored))) == (0x1040, 0x1100)


def installed(game_dir) -> bytes:
    exe = (game_dir / toybox.EXE_NAME).read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    if stamp != 0x695377B6:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x})")
    return toybox.image_of(exe)


def test_mining_the_installed_game_stays_out_of_the_cheat_handler(cfg, game_dir):
    """build 21347933: 플레이어 포인터를 쓰는 코드에서, 치트 명령 처리 함수 밖의 서로 다른 함수 셋 이상에서 후보가 나온다."""
    image = sigmine.Image(installed(game_dir))
    handler = sigmine.handler_range(image)
    assert handler == (0x522330, 0x5284FD)
    picks = sigmine.best_per_function(sigmine.mine_address(image, 0x18295F8, exclude=handler, sites=40))
    assert len(picks) >= 3
    assert all(sigmine.count(image, c.text) == 1 and not handler[0] <= c.at < handler[1] for c in picks)


def test_srkit_sig_mine_prints_candidates(cfg, game_dir, capsys):
    installed(game_dir)
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(address="18295f8", limit=3, sites=40)) == 0
    out = capsys.readouterr().out
    assert out.count("[rip") == 3 and "0x522330" in out                    # 후보 셋, 그리고 뺀 치트 함수의 범위
