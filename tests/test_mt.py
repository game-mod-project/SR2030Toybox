import json
from dataclasses import replace

import pytest

from srkit import korean, mt

Row = korean.Row


@pytest.fixture
def proj(cfg, tmp_path):
    fake = replace(cfg, root=tmp_path)
    korean.write_table(fake.translation_dir / "custom.default.csv", {
        "A|1|0": Row("Hello %s"),
        "A|2|0": Row("Already", "이미 번역됨", "ok"),
        "A|3|0": Row("mm/dd/yy"),
        "A|4|0": Row("Line one¶Line two"),
        "B|1|0": Row("Other section"),
    })
    return fake


def _write_out(in_path, rows):
    mt.out_path(in_path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_export_only_untranslated_and_chunks_by_rows(proj):
    paths = mt.export(proj, "custom.default.csv", max_rows=2)
    assert [p.name for p in paths] == ["custom.default~000.in.jsonl", "custom.default~001.in.jsonl"]
    keys = [json.loads(line)["key"] for p in paths for line in p.read_text(encoding="utf-8").splitlines()]
    assert keys == ["A|1|0", "A|3|0", "A|4|0", "B|1|0"]           # 이미 번역된 A|2|0 제외
    assert mt.table_of(paths[0]) == "custom.default.csv"


def test_export_filter_and_tag(proj):
    paths = mt.export(proj, "custom.default.csv", key_filter=r"^B\|", tag="b")
    assert [p.name for p in paths] == ["custom.default+b~000.in.jsonl"]
    assert mt.table_of(paths[0]) == "custom.default.csv"


def test_check_and_import_accept_only_valid_rows(proj):
    (path,) = mt.export(proj, "custom.default.csv")
    assert mt.check(path).problems == ["출력 파일 없음: custom.default~000.out.jsonl"]
    _write_out(path, [
        {"key": "A|1|0", "ko": "%s 님 안녕하세요"},
        {"key": "A|3|0", "ko": ""},                      # 일부러 번역하지 않음
        {"key": "A|4|0", "ko": "한 줄로 합침"},           # 줄바꿈 기호 누락 → 거부
        {"key": "Z|9|0", "ko": "없는 키"},
    ])
    result = mt.check(path)
    assert result.valid == {"A|1|0": "%s 님 안녕하세요"} and result.skipped == 1
    assert len(result.problems) == 3                      # 토큰 불일치, 없는 키, 빠진 행(B|1|0)

    ((_, applied),) = mt.import_all(proj)
    assert applied == 1
    rows = korean.read_table(proj.translation_dir / "custom.default.csv")
    assert rows["A|1|0"] == Row("Hello %s", "%s 님 안녕하세요", "mt")
    assert rows["A|2|0"] == Row("Already", "이미 번역됨", "ok")    # 검수된 행은 그대로
    assert rows["A|4|0"].ko == "" and rows["A|3|0"].ko == ""
