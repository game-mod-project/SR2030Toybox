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


def test_mining_skips_the_excluded_ranges(image):
    """치트 코드에서는 서명을 뽑지 않는다. 뺄 범위는 여럿일 수 있다."""
    assert [c.at for c in sigmine.mine_address(image, G, exclude=[(0x1000, 0x1040)])] == [0x1040, 0x1100]
    assert [c.at for c in sigmine.mine_address(image, G, exclude=[(0x1000, 0x1040), (0x1100, 0x1140)])] == [0x1040]


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


def cheat_image(anchor_in_function: bool = True) -> bytes:
    """명령 처리 함수(0x1040) · 거기서만 불리는 A(0x1100) · 밖에서도 불리는 B(0x1140) · A 에서만 불리는 C(0x1180)."""
    image = fake.shell([(0x1000, 0x1040), (0x1040, 0x1100), (0x1100, 0x1140), (0x1140, 0x1180), (0x1180, 0x11C0)])
    fake.put(image, fake.RDATA + 0x10, b"\0cheat allowcheats\0")
    fake.rip(image, 0x1050 if anchor_in_function else 0x2F00, bytes([0x48, 0x8D, 0x15]), fake.RDATA + 0x11)
    fake.rip(image, 0x1060, bytes([0xE8]), 0x1100)      # 명령 처리 함수 → A
    fake.rip(image, 0x1070, bytes([0xE8]), 0x1140)      # 명령 처리 함수 → B
    fake.rip(image, 0x1010, bytes([0xE8]), 0x1140)      # 치트와 무관한 함수 → B
    fake.rip(image, 0x1110, bytes([0xE8]), 0x1180)      # A → C
    return bytes(image)


def test_cheat_ranges_cover_the_handler_and_what_only_cheat_code_calls(image):
    assert sigmine.cheat_ranges(sigmine.Image(cheat_image())) == [(0x1040, 0x1100), (0x1100, 0x1140), (0x1180, 0x11C0)]
    assert sigmine.cheat_ranges(image) == []                               # 치트가 없는 빌드


def test_cheat_ranges_refuse_an_anchor_they_cannot_place():
    """치트 문자열은 있는데 그것을 쓰는 함수를 못 찾으면, 치트 코드를 가리지 못한 채 뽑게 두지 않는다."""
    with pytest.raises(LookupError):
        sigmine.cheat_ranges(sigmine.Image(cheat_image(anchor_in_function=False)))


NOPS = bytes([0x90]) * 48
P, Q, T, U = 0x1000 + 48, 0x1080 + 48, 0x1180 + 48, 0x1200 + 48


def constants_image() -> bytes:
    """상수를 든 자리들. 저마다 nop 48개(명령의 경계가 분명하다) 뒤에 놓고 ret 로 끝낸다."""
    image = fake.shell([(0x1000 + 0x80 * i, 0x1080 + 0x80 * i) for i in range(6)])
    for at, code in [
            (0x1000, "48 69 C0 50 01 00 00  48 05 A4 4D 01 00  48 03 C6"),             # P: imul rax,rax,150h / add rax,14DA4h / add rax,rsi
            (0x1080, "48 69 C8 50 01 00 00  42 0F 2F 84 21 A4 4D 01 00  76 40"),       # Q: imul rcx,rax,150h / comiss xmm0,[rcx+r12+14DA4h] / jbe
            (0x1100, "48 69 C0 50 01 00 00" + "  48 03 C6" * 5 + "  48 05 A4 4D 01 00"),   # 둘째 상수가 멀다(명령 다섯 뒤)
            (0x1180, "F2 0F 10 87 88 4B 01 00  66 0F 2F C1  76 5B"),                   # T: movsd xmm0,[rdi+14B88h] / comisd / jbe
            (0x1200, "49 69 CE 84 00 00 00  F3 0F 10 44 01 18  0F 2F C6"),             # U: imul rcx,r14,84h / movss xmm0,[rcx+rax+18h] / comiss
            (0x1280, "48 8B 05 50 01 00 00  48 85 C0 48 85 C0")]:                      # rip 상대 거리가 우연히 150h — 상수가 아니다
        fake.put(image, at, NOPS + bytes.fromhex(code) + b"\xC3")
    return bytes(image)


def test_constants_are_mined_as_values_to_read():
    """구조체 안의 자리와 간격은 서명이 읽어 낼 자리가 된다 — 4바이트는 [u32], 1바이트는 [u8]."""
    image = sigmine.Image(constants_image())
    assert {c.at: c.text for c in sigmine.mine_constants(image, [0x150, 0x14DA4])} == {
        P: "48 69 C0 [u32] 48 05 [u32] 48 03 C6", Q: "48 69 C8 [u32] 42 0F 2F 84 21 [u32] 76 40"}   # 둘째 상수가 먼 자리는 뺀다
    assert {c.at: (c.text, c.function, c.length) for c in sigmine.mine_constants(image, [0x14B88])} == {
        T: ("F2 0F 10 87 [u32] 66 0F 2F C1 76 5B", 0x1180, 14)}
    assert {c.at: c.text for c in sigmine.mine_constants(image, [0x84, 0x18])} == {U: "49 69 CE [u32] F3 0F 10 44 01 [u8] 0F 2F C6"}
    assert all(c.at != 0x1280 + 48 for c in sigmine.mine_constants(image, [0x150]))            # rip 상대 거리는 상수로 치지 않는다
    assert [c.at for c in sigmine.mine_constants(image, [0x150, 0x14DA4], exclude=[(0x1000, 0x1080)])] == [Q]


def test_a_candidate_can_be_shown_as_instructions():
    image = sigmine.Image(constants_image())
    found = sigmine.mine_constants(image, [0x84, 0x18])[0]
    assert sigmine.listing(image, found) == "imul rcx, r14, 0x84; movss xmm0, dword ptr [rcx + rax + 0x18]; comiss xmm0, xmm6"


F = 0x1300                                    # 가짜 함수(부르는 자리들이 가리킨다)
A, B, C = 0x1000 + 48, 0x1080 + 48, 0x1100 + 48


def calls_image() -> bytes:
    """함수 F 를 부르는 자리: A · B 는 뒤따르는 명령이 서로 다르고, C 는 앞에 인자를 싣는 명령 둘이 있고 바로 ret 다.
    넷째 자리는 call 이 아니다 — 다른 명령(movabs)의 상수 안에 E8 과 F 까지의 거리가 우연히 들어 있다."""
    image = fake.shell([(0x1000 + 0x80 * i, 0x1080 + 0x80 * i) for i in range(4)] + [(F, F + 0x40)])
    end = fake.rip(image, fake.put(image, 0x1000, NOPS), bytes([0xE8]), F)     # A: call F / mov r9b,1 / xor r8d,r8d / xor edx,edx / ret
    fake.put(image, end, bytes.fromhex("41 B1 01 45 33 C0 33 D2 C3"))
    end = fake.rip(image, fake.put(image, 0x1080, NOPS), bytes([0xE8]), F)     # B: call F / mov r15,[rbp-48h] / mov r14,[rbp-50h] / ret
    fake.put(image, end, bytes.fromhex("4C 8B 7D B8 4C 8B 75 B0 C3"))
    end = fake.put(image, 0x1100, NOPS + bytes.fromhex("BA FF FF FF FF 49 8B CC"))   # C: mov edx,-1 / mov rcx,r12 / call F / ret
    fake.put(image, fake.rip(image, end, bytes([0xE8]), F), b"\xC3")
    end = fake.put(image, 0x1180, NOPS + bytes([0x48, 0xB8, 0x11]))            # movabs rax,<11 E8 거리 22 33> / ret
    fake.put(image, fake.rip(image, end, bytes([0xE8]), F), bytes([0x22, 0x33, 0xC3]))
    fake.put(image, F, b"\xC3")
    return bytes(image)


def test_a_function_is_mined_from_the_calls_that_reach_it():
    """call rel32 의 목표는 rip 상대 거리와 같은 셈이다 — 함수의 주소를 읽어 낼 서명이 된다."""
    image = sigmine.Image(calls_image())
    assert {A + 1, B + 1, C + 9, 0x1180 + 48 + 4} <= set(image.refs(F))    # 거리만 보면 넷째 자리도 F 를 가리킨다
    assert {c.at: c.text for c in sigmine.mine_address(image, F)} == {
        A: "E8 [rip] 41 B1 01 45 33 C0 33 D2", B: "E8 [rip] 4C 8B 7D B8 4C 8B 75 B0"}   # C 는 call 뒤가 바로 ret 다. 넷째는 call 이 아니다
    assert all(sigmine.count(image, c.text) == 1 for c in sigmine.mine_address(image, F))


def test_a_signature_can_start_before_the_instruction_that_points():
    """back: 가리키는 명령보다 앞선 명령부터 — 함수를 부르기 전에 인자를 싣는 명령을 서명에 넣는다."""
    image = sigmine.Image(calls_image())
    found = {c.at: c.text for c in sigmine.mine_address(image, F, back=2)}
    assert found[C - 0] == "BA FF FF FF FF 49 8B CC E8 [rip]"              # 서명의 자리는 그 앞선 명령이다
    assert found[A - 2].startswith("90 90 E8 [rip]") and len(found) == 3
    assert sigmine.mine_address(image, F, back=60) == []                   # 앞에 명령이 그만큼 없다


def shapes_image() -> bytes:
    """전역 G 를 읽는 자리 셋(mov rdx,[G]). X · Y 는 꼴의 상수 88h · 50h 를 든 명령이 뒤따르고, Z 는 50h 가 분기의 거리로만 나온다."""
    image = fake.shell([(0x1000 + 0x80 * i, 0x1080 + 0x80 * i) for i in range(3)])
    for at, code in [
            (0x1000, "48 69 F0 88 00 00 00  4C 89 74 24 48  48 8D 7A 50  C3"),      # X: imul rsi,rax,88h / mov [rsp+48h],r14 / lea rdi,[rdx+50h]
            (0x1080, "48 63 C7  48 83 C3 50  48 69 C8 88 00 00 00  C3"),             # Y: movsxd rax,edi / add rbx,50h / imul rcx,rax,88h
            (0x1100, "48 69 C8 88 00 00 00  48 85 C0  74 50  48 8B C8  C3")]:        # Z: imul rcx,rax,88h / test rax,rax / je +50h / mov rcx,rax
        end = fake.rip(image, fake.put(image, at, NOPS), bytes([0x48, 0x8B, 0x15]), G)
        fake.put(image, end, bytes.fromhex(code))
    return bytes(image)


def test_holding_grows_the_signature_over_the_shape_constants():
    """holding: 서명 안의 명령이 그 상수들을 정해진 바이트로 들 때까지 늘린다 — 꼴이 바뀐 빌드에서는 서명이 맞지 않는다."""
    image = sigmine.Image(shapes_image())
    plain = {c.at: c.text for c in sigmine.mine_address(image, G)}
    assert plain[A] == "48 8B 15 [rip] 48 69 F0 88 00 00 00 4C 89 74 24 48" and len(plain) == 3     # 한 번만 맞으면 거기서 멈춘다
    assert {c.at: c.text for c in sigmine.mine_address(image, G, holding=[0x88, 0x50])} == {
        A: "48 8B 15 [rip] 48 69 F0 88 00 00 00 4C 89 74 24 48 48 8D 7A 50",
        B: "48 8B 15 [rip] 48 63 C7 48 83 C3 50 48 69 C8 88 00 00 00"}     # Z 의 50h 는 je 의 거리다 — 든 것이 아니다
    assert sigmine.mine_address(image, G, holding=[0x99]) == []


def walk_image() -> bytes:
    """목록을 훑는 코드의 꼴: lea rcx,[rax+rax*2] / mov rdx,[rdi+rcx*8+3568C0h] / test rdx,rdx / je / cmp byte ptr [rdx+1Ch],1 /
    jmp(다음 명령으로) / mov rax,[rdx+10h] / ret"""
    image = fake.shell([(0x1000, 0x1080)])
    fake.put(image, 0x1000, NOPS + bytes.fromhex("48 8D 0C 40  48 8B 94 CF C0 68 35 00  48 85 D2  74 0B  80 7A 1C 01  EB 00  48 8B 42 10  C3"))
    return bytes(image)


def test_constants_can_hold_shape_constants_pass_jumps_and_start_earlier():
    image = sigmine.Image(walk_image())
    assert sigmine.mine_constants(image, [0x3568C0], holding=[0x1C, 0x10]) == []            # jmp 에서 멈춘다 — 10h 에 닿지 못한다
    found = sigmine.mine_constants(image, [0x3568C0], holding=[0x1C, 0x10], through_jumps=True)
    assert [(c.at, c.text) for c in found] == [(A + 4, "48 8B 94 CF [u32] 48 85 D2 74 0B 80 7A 1C 01 EB 00 48 8B 42 10")]
    found = sigmine.mine_constants(image, [0x3568C0], holding=[0x1C], back=1)
    assert [(c.at, c.text, c.length) for c in found] == [(A, "48 8D 0C 40 48 8B 94 CF [u32] 48 85 D2 74 0B 80 7A 1C 01", 21)]
    assert sigmine.mine_constants(image, [0x3568C0], holding=[0x0B]) == []                  # je 의 거리 0Bh 는 든 것이 아니다


def installed(game_dir) -> bytes:
    exe = (game_dir / toybox.EXE_NAME).read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    if stamp != 0x695377B6:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x})")
    return toybox.image_of(exe)


def test_mining_the_installed_game_stays_out_of_the_cheat_code(cfg, game_dir):
    """build 21347933: 플레이어 포인터를 쓰는 코드에서, 치트 코드 밖의 서로 다른 함수 셋 이상에서 후보가 나온다."""
    image = sigmine.Image(installed(game_dir))
    cheats = sigmine.cheat_ranges(image)
    assert cheats[0] == (0x522330, 0x5284FD)                              # 명령 처리 함수가 맨 앞이다
    assert (0x528510, 0x52853E) in cheats and len(cheats) == 12           # 치트 코드에서만 불리는 함수 11개
    picks = sigmine.best_per_function(sigmine.mine_address(image, 0x18295F8, exclude=cheats, sites=40))
    assert len(picks) >= 3
    assert all(sigmine.count(image, c.text) == 1 and not any(a <= c.at < z for a, z in cheats) for c in picks)


def test_mining_constants_on_the_installed_game(cfg, game_dir):
    """build 21347933: 재고 칸의 간격과 첫 자리를 함께 읽어 내는 서명이 치트 코드 밖의 서로 다른 함수 셋 이상에서 나온다."""
    image = sigmine.Image(installed(game_dir))
    cheats = sigmine.cheat_ranges(image)
    picks = sigmine.best_per_function(sigmine.mine_constants(image, [0x150, 0x14DA4], exclude=cheats, sites=40))
    assert len(picks) >= 3
    assert all(c.text.count("[u32]") == 2 and sigmine.count(image, c.text) == 1 for c in picks)
    assert not any(a <= c.at < z for c in picks for a, z in cheats)


def test_srkit_sig_mine_prints_candidates(cfg, game_dir, capsys):
    installed(game_dir)
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["18295f8"], offset=False, limit=3, sites=40)) == 0
    out = capsys.readouterr().out
    assert sum(out.count(word) for word in ("[rip]", "[rip+1]", "[rip+4]")) == 3     # 후보 셋(명령 줄의 "[rip + …]" 는 세지 않는다)
    assert "0x522330" in out                                               # 뺀 치트 코드
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["150", "14da4"], offset=True, limit=3, sites=40)) == 0
    out = capsys.readouterr().out
    assert out.count("[u32]") == 6 and "imul" in out                       # 후보 셋(상수 둘씩)과 그 명령
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1", "2", "3"], offset=True, limit=3, sites=40)) == 1


def test_srkit_sig_mine_finds_functions_and_shape_constants(cfg, game_dir, capsys):
    """build 21347933: 함수의 목표(앞의 명령부터), 꼴의 상수를 든 서명, 서명의 길이 한도."""
    installed(game_dir)
    base = dict(offset=False, limit=3, sites=400, holding=None, back=0, most=None, longest=None, through_jumps=False)
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["bdd380"], **{**base, "back": 2})) == 0
    out = capsys.readouterr().out
    assert out.count("E8 [rip]") == 3 and out.count("call 0xbdd380") == 3  # 지역의 효과를 다시 셈하는 함수를 부르는 자리 셋
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1829620"], **{**base, "holding": ["88", "50"], "most": 14})) == 0
    out = capsys.readouterr().out
    assert "상수 0x88 · 0x50 을 든 것만" in out and out.count("88 00 00 00") == 3     # 기술 표: 레코드의 크기와 보유 묶음의 자리가 박힌 것
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1829620"], **{**base, "longest": 65})) == 1
    assert "64바이트" in capsys.readouterr().out
