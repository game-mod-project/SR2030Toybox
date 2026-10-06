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
