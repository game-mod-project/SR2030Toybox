import csv
from dataclasses import replace

import pytest

from srkit import inventory

# 지역 블록(키 값), 시나리오 설정(키: 값), 이름 붙은 행(키, 값, …) — 셋 다 키 섹션이다
KEYED = (
    "// CVP data\n"
    "&&CVP 599\n"
    'regionname\t"Palestine"\n'
    "gdpc 3660\n"
    "influence 1,2,3,6\n"
    "techlevel 70   // note\n"
    "\n"
    "&&GROUPING 599\n"
    "502,\n"
    "504,\n"
    "\n"
    "&&CVP 1499\n"
    'regionname "Germany"\n'
    "gdpc 51203\n"
    "treasury 100\n"
    "techlevel 110\n"
    "&&GMC\n"
    "startymd:       2023, 8, 7\n"
    "scenarioid:     \n"
    "initialfunds:   2\n"
    "&&END\n"
    "&&WMDATA, 0\n"
    "aiplayrich, 75000000.000\n"
    "socadj, 1.000, 2.000\n"
)

TABLES = (
    "// Equipment data\n"
    "// Created by the Asset Manager on 12/18/2025 08:05:47\n"
    "// SR5ID, ModelCode+EquipName, ClassNum, DaysToBuild, Cost, // Notes\n"
    "&&UNITS\n"
    '21535, "City, capital", 21, , 586, // not a column\n'
    '10091, "Mk V Tempest", 10, 4.5, 2.3,\n'
    "&&END\n"
    "// OUTPUT - 7\n"
    "// 660 Rows\n"
    "&&CABPRIORITIES, 0\n"
    "0, 1.000, 1.000 //Resource Minister, Military Materials\n"
    "&&NAMESET 0\n"
    "Malisheve\n"
    "Zubin Potok\n"
    "al-Hasakah\n"
    "&&BUILDSEQUENCE\n"
)


def test_strip_comment_keeps_slashes_inside_strings():
    assert inventory.strip_comment('1, "see http://x//y" // tail') == '1, "see http://x//y" '
    assert inventory.strip_comment('1,0,"//Grid","x"') == '1,0,"//Grid","x"'
    assert inventory.strip_comment("0, 1.000 //Resource, Minister") == "0, 1.000 "


def test_fields_split_on_commas_outside_strings():
    assert inventory.fields_of('21535, "City, capital", 21, , 586,') == ["21535", "City, capital", "21", "", "586", ""]
    assert inventory.fields_of("0, 1.000 //Resource, Minister") == ["0", "1.000"]
    assert inventory.fields_of("502,") == ["502", ""]
    assert inventory.fields_of('1, "unterminated, 2') == ["1", "unterminated, 2"]     # 따옴표가 안 맞아도 죽지 않는다


def test_key_value_accepts_space_colon_and_comma():
    assert inventory.key_value('regionname\t"Great Britain"') == ("regionname", '"Great Britain"')
    assert inventory.key_value("influence 1,2,3,6") == ("influence", "1,2,3,6")
    assert inventory.key_value("startymd:       2023, 8, 7") == ("startymd", "2023, 8, 7")
    assert inventory.key_value("scenarioid:     ") == ("scenarioid", "")
    assert inventory.key_value("aiforcesize, 2, 4, 8") == ("aiforcesize", "2, 4, 8")
    assert inventory.key_value("techlevel 70   // note") == ("techlevel", "70")
    assert inventory.key_value('21535, "City", 21') is None
    assert inventory.key_value("0x0D,0,0,1950") is None
    assert inventory.key_value(', , "text"') is None


def test_header_is_the_comment_with_the_most_names():
    comments = ["// Equipment data", "// Created by the Asset Manager on 12/18/2025 08:05:47",
                "// SR5ID, ModelCode+EquipName, ClassNum, // Notes"]
    assert inventory.header_names(comments) == ["SR5ID", "ModelCode+EquipName", "ClassNum", "Notes"]
    assert inventory.header_names(["// OUTPUT - 7", "// 660 Rows"]) == []
    assert inventory.header_names(["// Training Items Export,,,,", "// These are Espionage missions,,,,"]) == []
    assert inventory.header_names([]) == []


def scan(text: str, rel: str = "Maps/X.CVP") -> dict[str, inventory.Section]:
    sections: dict[str, inventory.Section] = {}
    inventory.scan_text(rel, text, sections)
    return sections


def test_keyed_sections_yield_keys():
    s = scan(KEYED)
    assert s["CVP"].keyed and s["GMC"].keyed and s["WMDATA"].keyed
    assert not s["GROUPING"].keyed
    assert list(s["CVP"].keys) == ["regionname", "gdpc", "influence", "techlevel", "treasury"]
    assert s["CVP"].keys["gdpc"] == 2 and s["CVP"].keys["treasury"] == 1
    assert s["CVP"].key_example["regionname"] == '"Palestine"'      # 처음 나온 값이 예시
    assert s["CVP"].blocks["Maps/X.CVP"] == 2 and s["CVP"].rows["Maps/X.CVP"] == 8
    assert list(s["GMC"].keys) == ["startymd", "scenarioid", "initialfunds"]
    assert "scenarioid" not in s["GMC"].key_example                # 값이 빈 키는 예시가 없다
    assert s["WMDATA"].key_example["socadj"] == "1.000, 2.000"


def test_mostly_lowercase_names_still_make_a_keyed_section():
    text = "&&CVP 1\n" + "".join(f"key{i} {i}\n" for i in range(9)) + "RacePrimary 4\n"
    assert scan(text)["CVP"].keyed                                  # 9/10: 대문자로 시작하는 키가 섞여도 된다
    assert "RacePrimary" in scan(text)["CVP"].keys
    half = "&&MIX\n" + "alpha 1\n" * 5 + "1, 2, 3\n" * 5
    assert not scan(half)["MIX"].keyed                              # 절반만 이름이면 표로 남아 열이 나온다
    assert scan(half)["MIX"].tables["Maps/X.CVP"].width == 3


def test_tables_yield_columns_with_names_from_the_header_comment():
    s = scan(TABLES, "Maps/DATA/DEFAULT.UNIT")
    units = s["UNITS"].tables["Maps/DATA/DEFAULT.UNIT"]
    assert not s["UNITS"].keyed
    assert units.names == ["SR5ID", "ModelCode+EquipName", "ClassNum", "DaysToBuild", "Cost", "Notes"]
    assert units.width == 6
    assert units.filled == {0: 2, 1: 2, 2: 2, 3: 1, 4: 2}           # 빈 칸은 세지 않는다
    assert units.example[1] == "City, capital" and units.example[3] == "4.5"
    cab = s["CABPRIORITIES"].tables["Maps/DATA/DEFAULT.UNIT"]
    assert cab.names == [] and cab.width == 3                       # 열 이름 주석이 없으면 번호만


def test_place_names_do_not_become_keys():
    s = scan(TABLES)
    assert not s["NAMESET"].keyed
    assert s["NAMESET"].rows["Maps/X.CVP"] == 3


def test_empty_section_is_listed_with_zero_rows():
    s = scan(TABLES)
    assert s["BUILDSEQUENCE"].blocks["Maps/X.CVP"] == 1
    assert s["BUILDSEQUENCE"].rows["Maps/X.CVP"] == 0 and not s["BUILDSEQUENCE"].keyed


def test_directives_and_lines_outside_sections_are_not_rows():
    text = ('#ifset 0x02\n#include "DEFAULT.UNIT", "MAPS\\DATA\\"\n#endifset\nstray, 1\n'
            '&&MAP\n#include "x.csv", "MAPS\\"\nmapfile "World2030"\n&&END\nafter, end\n')
    s = scan(text, "Sandbox/W.scenario")
    assert list(s) == ["MAP"]
    assert s["MAP"].rows["Sandbox/W.scenario"] == 1 and list(s["MAP"].keys) == ["mapfile"]


def test_each_file_keeps_its_own_column_names():
    sections: dict[str, inventory.Section] = {}
    inventory.scan_text("a.UNIT", "// Id, Name\n&&UNITS\n1, x\n", sections)
    inventory.scan_text("b.UNIT", "// Id, Name, Extra\n&&UNITS\n1, x, y\n", sections)
    assert sections["UNITS"].tables["a.UNIT"].names == ["Id", "Name"]
    assert sections["UNITS"].tables["b.UNIT"].names == ["Id", "Name", "Extra"]


def fake_game(root, exe: bytes = b""):
    (root / "INI").mkdir(parents=True)
    (root / "Maps" / "DATA").mkdir(parents=True)
    (root / "Localize").mkdir()
    (root / "INI" / "scen.scenario").write_bytes(KEYED.replace("\n", "\r\n").encode("cp1252"))
    (root / "Maps" / "DATA" / "DEFAULT.UNIT").write_bytes(TABLES.encode("cp1252"))
    (root / "Maps" / "World.OOF").write_bytes(b'&&OOF\t0, \r\n21003, 958, 107, "Caf\xe9"\r\n\0')   # 끝에 NUL 하나
    (root / "Maps" / "World.MAPX").write_bytes(b"`\x01\0\0\x08\x03\0\0binary")
    (root / "Localize" / "skip.csv").write_bytes(b"&&GUITRANS\n")                              # 훑는 폴더가 아니다
    (root / "SupremeRuler2030.exe").write_bytes(exe)
    return root


def test_scan_walks_game_folders_and_skips_binary_files(tmp_path):
    inv = inventory.scan(fake_game(tmp_path))
    assert inv.skipped == [("Maps/World.MAPX", "이진")]
    assert "OOF" in inv.sections and "GUITRANS" not in inv.sections     # 끝의 NUL 하나는 이진이 아니다
    assert inv.sections["OOF"].tables["Maps/World.OOF"].example[3] == "Café"
    assert inv.sections["CVP"].rows["INI/scen.scenario"] == 8           # CRLF 파일도 같게 읽는다


def test_exe_candidates_come_from_tables_that_hold_known_names():
    table = b"\0".join([b"startymd:", b"hiddenkey:", b"initialfunds:", b"otherkey"])
    lonely = b"\0" * 64 + b"lonely\0"
    sentence = b"Some sentence here.\0"
    unrelated = b"\0" * 64 + b"\0".join([b"alpha", b"beta", b"gamma"])
    found = inventory.exe_candidates(lonely + sentence + table + unrelated, {"startymd", "initialfunds"})
    assert found == [inventory.Candidate("hiddenkey", "startymd", 1, True),
                     inventory.Candidate("otherkey", "initialfunds", 1, False)]


def test_exe_candidates_need_two_known_names_and_a_tight_table():
    one_known = b"\0".join([b"startymd:", b"hiddenkey:"])
    spread = b"startymd:" + b"\0" * 40 + b"hiddenkey:" + b"\0" * 40 + b"initialfunds:"
    assert inventory.exe_candidates(one_known, {"startymd", "initialfunds"}) == []
    assert inventory.exe_candidates(spread, {"startymd", "initialfunds"}) == []
    assert inventory.exe_candidates(b"", {"startymd"}) == []


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_run_writes_five_tables(cfg, tmp_path):
    exe = b"\0".join([b"startymd:", b"hiddenkey:", b"initialfunds:"])
    fake = replace(cfg, root=tmp_path / "proj", game_dir=fake_game(tmp_path / "game", exe))
    result = inventory.run(fake)
    out = fake.build_dir / "inventory"
    assert result["out"] == out and result["skipped"] == 1 and result["candidates"] == 1
    assert sorted(p.name for p in out.iterdir()) == ["columns.csv", "exe-candidates.csv", "keys.csv", "sections.csv",
                                                     "skipped.csv"]
    kinds = {r["section"]: r["kind"] for r in read(out / "sections.csv")}
    assert kinds["CVP"] == "keyed" and kinds["UNITS"] == "table" and kinds["BUILDSEQUENCE"] == "table"
    assert {"section": "CVP", "key": "gdpc", "files": "1", "count": "2", "example": "3660"} in read(out / "keys.csv")
    cost = [r for r in read(out / "columns.csv") if r["section"] == "UNITS" and r["name"] == "Cost"]
    assert cost == [{"file": "Maps/DATA/DEFAULT.UNIT", "section": "UNITS", "index": "4", "name": "Cost", "filled": "2",
                     "example": "586"}]
    assert read(out / "exe-candidates.csv") == [{"string": "hiddenkey", "near": "startymd", "distance": "1", "colon": "1"}]
    assert read(out / "skipped.csv") == [{"file": "Maps/World.MAPX", "reason": "이진"}]
    assert b"\r\n" not in (out / "keys.csv").read_bytes()               # 번역 테이블과 같은 형식: BOM + LF
    inventory.run(fake)                                                 # 다시 돌려도 같은 다섯 파일
    assert len(list(out.iterdir())) == 5


def test_run_refuses_a_folder_without_the_game(cfg, tmp_path):
    fake = replace(cfg, root=tmp_path, game_dir=tmp_path / "nowhere")
    with pytest.raises(RuntimeError, match="게임 폴더가 아닙니다"):
        inventory.run(fake)
    assert not (fake.build_dir / "inventory").exists()


def test_real_game_inventory(game_dir, cfg, tmp_path):
    """설치본에서: 키 섹션과 표가 맞게 갈리고, 치트 조사에 쓸 키·열이 실제로 나온다."""
    fake = replace(cfg, root=tmp_path)
    result = inventory.run(fake)
    out = fake.build_dir / "inventory"
    kinds = {r["section"]: r["kind"] for r in read(out / "sections.csv")}
    assert {name for name, kind in kinds.items() if kind == "keyed"} >= {"CVP", "GMC", "WMDATA", "WMPRODDATA", "AIPARAMS"}
    for name in ("UNITS", "TTR", "TERRAIN", "NAMESET", "OOB", "OOF", "SEVENTS"):
        assert kinds[name] == "table", name
    keys = {(r["section"], r["key"]) for r in read(out / "keys.csv")}
    assert {("CVP", "treasury"), ("CVP", "gdpc"), ("GMC", "initialfunds"), ("GMC", "fastbuild")} <= keys
    unit_columns = {r["name"] for r in read(out / "columns.csv") if r["file"] == "Maps/DATA/DEFAULT.UNIT"}
    assert {"DaysToBuild", "Cost", "SoftAttack", "GroundDefense"} <= unit_columns
    assert result["sections"] >= 50 and result["candidates"] > 0
