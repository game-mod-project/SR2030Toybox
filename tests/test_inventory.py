from srkit import inventory


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
