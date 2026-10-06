from dataclasses import replace

from srkit import korean, srutf8, tcheck

# 똑같은 키가 없으면 Missing 이 적히고, 대소문자만 다른 키가 있으면 Incorrect Case 도 함께 적힌다.
# 똑같은 키가 있어도 대소문자만 다른 키가 사전 앞쪽에 있으면 Incorrect Case 만 적힌다(Hold, Then Go).
LOG = (
    "SRLOG: Translation Check Started...\r\n"
    "SRLOG: Missing GUI Translation, in DEF_S3, Show for \r\n"
    "SRLOG: Missing GUI Translation, in DEF_F5, Allow Movement in Panama Canal\r\n"
    "SRLOG: Missing GUI Translation, in BUILDERX, HAPNAME:\r\n"
    "SRLOG: Missing GUI Translation, in POP_X, Yes, really\r\n"
    "SRLOG: Missing GUI Translation, in LOB_SETC, Force Recache for Modding\r\n"
    "SRLOG: Incorrect Case Translation, in LOB_SETC, Force Recache for Modding, (Force Recache For Modding, 모드용 캐시 재생성)\r\n"
    "SRLOG: Incorrect Case Translation, in POP_Y, Hold, Then Go, (HOLD, THEN GO, 대기 후 이동)\r\n"
)


def test_parse_log():
    log = tcheck.parse(srutf8.encode(LOG))
    assert log.missing == {"Show for ": "DEF_S3", "Allow Movement in Panama Canal": "DEF_F5", "HAPNAME:": "BUILDERX",
                           "Yes, really": "POP_X", "Force Recache for Modding": "LOB_SETC"}   # 끝 공백·쉼표 보존
    assert log.case == {"Force Recache for Modding": ("Force Recache For Modding", "LOB_SETC"),
                        "Hold, Then Go": ("HOLD, THEN GO", "POP_Y")}


def test_import_adds_keys_and_reuses_case_variants(cfg, game_dir, tmp_path):
    fake = replace(cfg, root=tmp_path)
    fake.korean_mod_dir.mkdir(parents=True)
    korean.extract(fake)
    table = fake.translation_dir / korean.GUI_TABLE
    rows = korean.read_table(table)
    assert "GUITRANS|Show for " not in rows and "GUITRANS|Force Recache for Modding" not in rows
    rows["GUITRANS|Force Recache For Modding"] = korean.Row("Force Recache For Modding", "모드용 캐시 재생성", "ok")
    korean.write_table(table, rows)
    log = tmp_path / "LOG-TRANS-CHECK.log"
    log.write_bytes(srutf8.encode(LOG))

    result = korean.tcheck_import(fake, log)
    rows = korean.read_table(table)
    assert rows["GUITRANS|Show for "] == korean.Row("Show for ")               # 새 키: 번역 대기
    assert rows["GUITRANS|Force Recache for Modding"] == korean.Row(           # 대소문자 변형: 기존 번역 재사용
        "Force Recache for Modding", "모드용 캐시 재생성", "mt")
    assert rows["GUITRANS|Force Recache For Modding"].status == "ok"
    assert "GUITRANS|HAPNAME:" not in rows                                      # 개발용 화면은 모으지 않는다
    assert "GUITRANS|Hold, Then Go" not in rows                                 # 똑같은 키가 이미 있다는 뜻이라 모으지 않는다
    assert result["new_keys"] == 4 and result["filled"] == 1 and result["stale"] == []
    extra = tcheck.read_extra_keys(fake.korean_mod_dir / tcheck.EXTRA_KEYS)
    assert extra["Show for "] == "DEF_S3" and not set(extra) & set(korean.official_gui_keys(fake))

    again = korean.tcheck_import(fake, log)                                     # 번역한 뒤에도 같은 로그가 나오면
    assert again["new_keys"] == 0 and again["stale"] == ["Force Recache for Modding"]   # 못 찾은 문구로 알린다
