"""srtext: &&REGIONTEXT 의 따옴표 없는 이름(DLC 의 1940 ~ 1942 시나리오)도 번역 단위다."""
from srkit import srtext

CODE = chr(92) + "42 "        # 줄머리 코드: 역슬래시 + "42 "
SOURCE = "\n".join([
    "&&REGIONTEXT, 0",
    "",
    f"0,League of Nations,{CODE}",
    f'101,Egypt,"{CODE}Egypt, with its ancient civilization"',
    f"102, Libya ,{CODE}",
    '801,,"only a description"',
    f'1007, "Albania", "{CODE}Albania struggles"',
    f"103, 12 ,{CODE}",
    "// 104,Comment,",
    "&&END",
    "105,Outside,",
    "&&LOCALIZE",
    "106,Not a region,",
    "",
])


def test_bare_region_names_are_units_and_the_file_is_unchanged_until_translated():
    doc = srtext.parse(SOURCE)
    assert doc.serialize() == SOURCE                                   # 읽고 그대로 쓰면 한 글자도 바뀌지 않는다
    assert [(u.key, u.text) for u in doc.units()] == [
        ("REGIONTEXT|0|0", "League of Nations"),                       # 따옴표가 하나도 없는 줄
        ("REGIONTEXT|101|0", "Egypt"),                                 # 이름이 순번 0,
        ("REGIONTEXT|101|1", CODE + "Egypt, with its ancient civilization"),   # 따옴표 안의 소개문이 1
        ("REGIONTEXT|102|0", "Libya"),                                 # 둘레의 빈칸은 이름이 아니다
        ("REGIONTEXT|801|0", "only a description"),                    # 이름 칸이 빈 줄은 앞과 같다(소개문이 0)
        ("REGIONTEXT|1007|0", "Albania"),                              # 따옴표가 있는 이름도 앞과 같다
        ("REGIONTEXT|1007|1", CODE + "Albania struggles"),
    ]                                                                  # 숫자뿐인 칸 · 주석 · 다른 섹션은 이름이 아니다


def test_translated_bare_names_are_written_in_quotes():
    doc = srtext.parse(SOURCE)
    changed = doc.apply({"REGIONTEXT|0|0": "국제 연맹", "REGIONTEXT|101|0": "이집트", "REGIONTEXT|101|1": CODE + "이집트는",
                         "REGIONTEXT|1007|0": "알바니아"})
    assert changed == 4
    lines = doc.serialize().split("\n")
    assert lines[2] == f'0,"국제 연맹",{CODE}'
    assert lines[3] == f'101,"이집트","{CODE}이집트는"'
    assert lines[4] == f"102, Libya ,{CODE}"                           # 번역하지 않은 이름은 그대로(따옴표 없이)
    assert lines[6] == f'1007, "알바니아", "{CODE}Albania struggles"'
    again = srtext.parse(doc.serialize())                              # 다시 읽으면 이름은 따옴표 안의 글이다 — 키는 같다
    assert ("REGIONTEXT|101|0", "이집트") in [(u.key, u.text) for u in again.units()]
    assert ("REGIONTEXT|101|1", CODE + "이집트는") in [(u.key, u.text) for u in again.units()]


def test_missing_region_names_fill_empty_name_cells_or_add_rows():
    """지역 자료에만 이름이 있는 지역(korean.missing_region_names): 이름 칸이 빈 행은 그 칸을 채우고, 행이 없으면 섹션 끝에 더한다."""
    from srkit import korean
    lines = ["&&REGIONTEXT", '0, "United Nations", "", "", ', '101, "", "desc of 101"', '102,,"desc of 102"', '103, "Named", "desc"',
             "&&END", ""]
    doc = srtext.parse(chr(10).join(lines))
    added = korean._add_extra_regions(doc, {"REGIONTEXT|101|0": "이집트", "REGIONTEXT|102|0": "리비아", "REGIONTEXT|103|0": "쓰이지 않는다",
                                            "REGIONTEXT|999|0": "새 지역"})
    assert added == 3
    assert doc.serialize().split(chr(10)) == ["&&REGIONTEXT", '0, "United Nations", "", "", ', '101, "이집트", "desc of 101"',
                                              '102,"리비아","desc of 102"', '103, "Named", "desc"', '999, "새 지역"', "&&END", ""]


def test_missing_titles_are_added_to_the_title_section():
    """영어판에 제목 행이 없는 시나리오: 한국어판의 FILETEXT 끝에 `<파일 이름>, "<제목>"` 을 더한다."""
    from srkit import korean
    lines = ["&&FILETEXT, 0", 'SR1936, "1936 - The Road to War"', "&&END", "&&THEATRESTEXT, 0", '1, "A", "NEA"', ""]
    doc = srtext.parse(chr(10).join(lines))
    assert korean._add_extra_titles(doc, {"FILETEXT|1914 - The Great War|0": "1914 - 대전쟁"}) == 1
    assert doc.serialize().split(chr(10))[:3] == ["&&FILETEXT, 0", 'SR1936, "1936 - The Road to War"',
                                                  '1914 - The Great War, "1914 - 대전쟁"']
