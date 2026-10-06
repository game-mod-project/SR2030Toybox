"""한글화 모드: 원문 추출 → 번역 테이블 → LOCALKO 빌드."""
from __future__ import annotations

import csv
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import hook, sprites
from . import spritefont as sf
from . import srtext, srutf8, tcheck
from .config import Config

TEXT_EXTS = {".csv", ".ini", ".gmt"}
# 문자열이 없거나(색인 파일) 다른 형식이라 번역 대상에서 빼는 파일
SKIP_NAMES = {"localtext.csv", "tipofday.csv"}
GUI_NAME = "LocalText-GUI.csv"
GUI_TABLE = "localtext-gui.csv"
REGIONS_NAME = "LocalText-Regions.csv"
EXTRA_REGIONS_TABLE = "localtext-regions.extra.csv"   # 영어판 현지화 파일에 없는 지역 이름(한국어판에만 행 추가)
SCENARIO_DIRS = ("Scenario", "Sandbox", "Campaign", "Tutorials")
# 지도 위 도시·시설 위치 이름. 현지화 파일이 아니라 지도 데이터(*.OOF)에 있어, 훅 DLL 이 그리는 순간에 바꾼다
MAP_NAMES_TABLE = "map-names.csv"
MAP_NAMES_FILE = "srhook-names.txt"     # 빌드 산출물(Localize/<대상 언어>/): "게임이 그리는 바이트<TAB>SR-UTF8 한글<LF>"
MAP_NAME_MAX = 63                       # 훅이 사전에서 찾아보는 문자열의 최대 길이(바이트). native/srhook 의 SR_NAME_MAX
OOF_ROW = re.compile(r'^\s*\d+,\s*-?\d+,\s*-?\d+,\s*"([^"]+)"')

# 게임이 지도 라벨에 쓰는 바이트 단위 대문자화(빌드 21347933, docs/03). a–z 는 따로 대문자가 된다
GAME_UPPER = {0x9A: 0x8A, 0x9E: 0x8E, 0xE1: 0xC1, 0xE2: 0xC2, 0xE4: 0xC4, 0xE7: 0xC7, 0xE9: 0xC9, 0xEA: 0xCA, 0xEB: 0xCB,
              0xED: 0xCD, 0xEE: 0xD8, 0xF1: 0xD1, 0xF3: 0xD3, 0xF4: 0xD4, 0xF6: 0xD6, 0xFA: 0xDA, 0xFC: 0xDC, 0xFD: 0xDD}
HEADER = ["key", "en", "ko", "status"]
STATUS_MT, STATUS_OK = "mt", "ok"   # 기계 번역 초안 / 사람이 확인함

# 폭 계산 오차를 줄이려고 ASCII 로 바꿔 쓰는 문장부호 (큰따옴표는 파일 형식상 쓸 수 없다)
PUNCT = str.maketrans({"‘": "'", "’": "'", "“": "'", "”": "'", "…": "...", "–": "-", "—": "-", "•": "-", " ": " "})


def decode_cp1252(data: bytes) -> str:
    table = [srutf8.cp1252_char(b) for b in range(256)]
    return "".join(table[b] for b in data)


def table_name(rel: Path) -> str:
    """원본 상대 경로 → 번역 테이블 파일명 (예: CUSTOM/DEFAULT.GMT → custom.default.csv)."""
    return ".".join(p.lower() for p in rel.with_suffix("").parts) + ".csv"


def source_files(cfg: Config) -> list[Path]:
    """번역 원문 파일들의 (언어 폴더 기준) 상대 경로."""
    out = []
    for path in sorted(cfg.source_dir.rglob("*")):
        rel = path.relative_to(cfg.source_dir)
        if path.is_file() and path.suffix.lower() in TEXT_EXTS and path.name.lower() not in SKIP_NAMES \
                and rel.parts[0].lower() != "fonts":
            out.append(rel)
    return out


def official_gui_keys(cfg: Config) -> list[str]:
    """공식 번역들의 GUI 사전 키(영어 원문). 영어 폴더에는 GUI 파일이 없어 다른 언어 파일들의 합집합을 쓴다."""
    keys: dict[str, None] = {}
    for lang in sorted(cfg.localize_dir.glob("LOCAL*")):
        if lang.name == cfg.target_lang:
            continue
        for path in lang.iterdir():
            if path.name.lower() == GUI_NAME.lower():
                for ln in srtext.parse(decode_cp1252(path.read_bytes())).lines:
                    if ln.section == "GUITRANS" and ln.key:
                        keys.setdefault(ln.key)
    return list(keys)


def gui_keys(cfg: Config) -> list[str]:
    """GUI 번역 키: 공식 번역의 키에, 거기에도 없어 게임의 번역 검사 로그에서 모은 키(gui-keys-extra.csv)를 보탠다."""
    keys = dict.fromkeys(official_gui_keys(cfg))
    for key in tcheck.read_extra_keys(cfg.korean_mod_dir / tcheck.EXTRA_KEYS):
        keys.setdefault(key)
    return list(keys)


def tcheck_import(cfg: Config, log_path: Path, skip_screens: tuple[str, ...] = ("BUILDERX", "FONTTEST")) -> dict:
    """번역 검사 로그에서 사전에 없는 GUI 문구(Missing)를 키 목록에 더하고, 대소문자만 다른 키가 있으면 그 번역으로 채운다.

    게임은 화면에 그릴 때 사전을 대소문자까지 똑같은 키로만 찾는다. 대소문자만 다른 키가 있어도 똑같은 키가
    없으면 영어로 나오고, 로그에는 Missing 과 Incorrect Case 가 함께 적힌다.
    skip_screens 는 개발용 화면(화면 편집기, 글꼴 시험)이라 모으지 않는다.
    """
    log = tcheck.parse(log_path.read_bytes())
    table = cfg.translation_dir / GUI_TABLE
    # 번역이 이미 있는데도 게임이 못 찾았다면 설치된 빌드가 오래됐거나 키가 어긋난 것
    had = read_table(table)
    stale = [t for t in log.missing if (row := had.get(f"GUITRANS|{t}")) and row.ko]
    path = cfg.korean_mod_dir / tcheck.EXTRA_KEYS
    extra = tcheck.read_extra_keys(path)
    before = len(extra)
    official = set(official_gui_keys(cfg))
    for text, screen in log.missing.items():
        if screen not in skip_screens and text not in official:
            extra.setdefault(text, screen)
    tcheck.write_extra_keys(path, extra)
    extract(cfg)
    rows = read_table(table)
    filled = 0
    for text, (key, _) in log.case.items():
        row, known = rows.get(f"GUITRANS|{text}"), rows.get(f"GUITRANS|{key}")
        if row and not row.ko and known and known.ko:
            rows[f"GUITRANS|{text}"] = Row(row.en, known.ko, STATUS_MT)
            filled += 1
    write_table(table, rows)
    return {"missing": len(log.missing), "case": len(log.case), "new_keys": len(extra) - before, "filled": filled,
            "untranslated": sum(1 for r in rows.values() if not r.ko), "stale": stale}


@dataclass
class Row:
    en: str
    ko: str = ""
    status: str = ""   # "" 미번역, STATUS_MT, STATUS_OK


def read_table(path: Path) -> dict[str, Row]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {r["key"]: Row(r["en"], r["ko"], (r.get("status") or STATUS_MT) if r["ko"] else "")
                for r in csv.DictReader(f)}


def write_table(path: Path, rows: dict[str, Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows((key, r.en, r.ko, r.status if r.ko else "") for key, r in rows.items())


@dataclass
class TableReport:
    name: str
    total: int
    translated: int
    reviewed: int
    changed: list[str]   # 원문이 바뀐 키 (번역 재검토 필요)
    removed: list[str]   # 원문에서 사라진 키


def _report(name: str, rows: dict[str, Row], changed: list[str] = (), removed: list[str] = ()) -> TableReport:
    return TableReport(name, len(rows), sum(1 for r in rows.values() if r.ko),
                       sum(1 for r in rows.values() if r.ko and r.status == STATUS_OK), list(changed), list(removed))


def _merge(path: Path, units: list[tuple[str, str]]) -> TableReport:
    old = read_table(path)
    rows: dict[str, Row] = {}
    changed = []
    for key, en in units:
        row = old.get(key, Row(en))
        if row.ko and row.en != en:
            changed.append(key)
            row = Row(en, row.ko, STATUS_MT)  # 원문이 바뀌었으니 다시 검수 대상
        rows[key] = Row(en, row.ko, row.status)
    write_table(path, rows)
    return _report(path.name, rows, changed, [k for k in old if k not in rows])


def scenario_files(cfg: Config) -> list[Path]:
    """시나리오 폴더 안의 현지화 파일(게임 루트 기준 상대 경로): <…>/Localize/<원문 언어>/<파일>."""
    out: list[Path] = []
    for top in SCENARIO_DIRS:
        for folder in sorted((cfg.game_dir / top).rglob("Localize")):
            src = folder / cfg.source_lang
            if src.is_dir():
                out += [p.relative_to(cfg.game_dir) for p in sorted(src.rglob("*"))
                        if p.is_file() and p.suffix.lower() in TEXT_EXTS]
    return out


def scenario_table(rel: Path) -> str:
    """Scenario/Arena 6A/Localize/LOCALEN/Arena_localTTRX.csv → scen.arena-6a.arena_localttrx.csv"""
    i = [p.lower() for p in rel.parts].index("localize")
    slug = lambda s: s.lower().replace(" ", "-")  # noqa: E731
    return f"scen.{slug('-'.join(rel.parts[1:i]))}.{slug(rel.stem)}.csv"


def cvp_region_names(path: Path) -> dict[str, str]:
    """지역 데이터(.CVP)의 지역 번호 → regionname."""
    names: dict[str, str] = {}
    current = None
    for line in decode_cp1252(path.read_bytes()).split("\n"):
        if m := re.match(r"\s*&&CVP\s+(\d+)", line):
            current = m.group(1)
        elif line.lstrip().startswith("&&"):
            current = None
        elif current is not None and (m := re.match(r'\s*regionname\s+"([^"]*)"', line)):
            names.setdefault(current, m.group(1))
    return names


def extra_region_names(cfg: Config, known: set[str]) -> list[tuple[str, str]]:
    """LocalText-Regions 를 쓰는 샌드박스의 지역 가운데, 지역 데이터에만 이름이 있고 현지화 파일에는 없는 것.

    게임은 이런 지역에 데이터의 영어 이름을 그대로 쓴다(공식 번역에서도 빠져 있다). 번호에 이름이 하나로 정해질 때만 다룬다.
    """
    seen: dict[str, set[str]] = {}
    for scen in sorted((cfg.game_dir / "Sandbox").glob("*.scenario")):
        text = decode_cp1252(scen.read_bytes())
        if "localtext-regions.csv" not in text.lower():
            continue
        for name in re.findall(r'#include\s+"([^"]+\.cvp)"', text, flags=re.I):
            cvp = cfg.game_dir / "Maps" / name
            if cvp.is_file():
                for rid, region in cvp_region_names(cvp).items():
                    seen.setdefault(rid, set()).add(region)
    return [(f"REGIONTEXT|{rid}|0", next(iter(names))) for rid, names in sorted(seen.items(), key=lambda kv: int(kv[0]))
            if rid not in known and len(names) == 1]


def game_upper(data: bytes) -> bytes:
    """게임이 지도 라벨을 그리기 전에 하는 대문자화를 그대로 흉내 낸다."""
    return bytes(b - 32 if 0x61 <= b <= 0x7A else GAME_UPPER.get(b, b) for b in data)


def map_files(cfg: Config) -> list[Path]:
    """지도 물체 파일(*.OOF, 게임 루트 기준 어디든). 게임·편집기가 남긴 백업 폴더는 뺀다."""
    return [p for p in sorted(cfg.game_dir.rglob("*.OOF"))
            if not any("backup" in part.lower() for part in p.relative_to(cfg.game_dir).parts)]


def map_names(cfg: Config) -> list[str]:
    """지도 물체 파일의 이름 칸(`번호, x, y, "이름", …`)에 나오는 서로 다른 이름들."""
    names: dict[str, None] = {}
    for path in map_files(cfg):
        for line in decode_cp1252(path.read_bytes()).split("\n"):
            if m := OOF_ROW.match(line):
                names.setdefault(m.group(1))
    return sorted(names)


def extract(cfg: Config) -> list[TableReport]:
    """원문을 번역 테이블로 뽑는다. 기존 번역(ko)은 키 기준으로 유지한다."""
    reports = []
    region_ids: set[str] = set()
    for rel in source_files(cfg):
        doc = srtext.parse(decode_cp1252((cfg.source_dir / rel).read_bytes()))
        units = [(u.key, u.text) for u in doc.units()]
        if units:
            reports.append(_merge(cfg.translation_dir / table_name(rel), units))
        if rel.name.lower() == REGIONS_NAME.lower():
            region_ids = {ln.key for ln in doc.lines if ln.section == "REGIONTEXT" and ln.key}
    reports.append(_merge(cfg.translation_dir / GUI_TABLE, [(f"GUITRANS|{k}", k) for k in gui_keys(cfg)]))
    reports.append(_merge(cfg.translation_dir / EXTRA_REGIONS_TABLE, extra_region_names(cfg, region_ids)))
    for rel in scenario_files(cfg):
        doc = srtext.parse(decode_cp1252((cfg.game_dir / rel).read_bytes()))
        units = [(u.key, u.text) for u in doc.units()]
        if units:
            reports.append(_merge(cfg.translation_dir / scenario_table(rel), units))
    reports.append(_merge(cfg.translation_dir / MAP_NAMES_TABLE, [(f"MAPNAME|{n}", n) for n in map_names(cfg)]))
    return reports


def tm_fill(cfg: Config, pattern: str = "scen.*.csv") -> int:
    """pattern 에 맞는 테이블의 빈 행을, 같은 영어 원문이 다른 곳에서 한 가지로만 번역돼 있으면 그 번역으로 채운다."""
    tables = {p: read_table(p) for p in sorted(cfg.translation_dir.glob("*.csv"))}
    memory: dict[str, set[str]] = {}
    for rows in tables.values():
        for row in rows.values():
            if row.ko:
                memory.setdefault(row.en, set()).add(row.ko)
    skip = notranslate(cfg)
    filled = 0
    for path, rows in tables.items():
        if not path.match(pattern):
            continue
        before = filled
        for key, row in rows.items():
            found = memory.get(row.en)
            if not row.ko and found and len(found) == 1 and not (skip and skip.search(key)):
                rows[key] = Row(row.en, next(iter(found)), STATUS_MT)
                filled += 1
        if filled > before:
            write_table(path, rows)
    return filled


def stats(cfg: Config) -> list[TableReport]:
    return [_report(path.name, read_table(path)) for path in sorted(cfg.translation_dir.glob("*.csv"))]


# 게임이 고정 길이로 잘라 쓰는 자리: (키 정규식, 최대 바이트, 설명). 바이트는 게임 파일 인코딩(SR-UTF8) 기준.
# 지역 이름은 게임 화면에서 30바이트(한글 10자)까지 보이고 33바이트는 잘리는 것을 확인했다(2026-10-06).
# 시나리오 전용 파일은 이름 칸을 비워 두므로(`801,,"소개문"`) 같은 키가 소개문을 가리킨다 → 테이블 이름으로 구분한다.
BYTE_LIMITS = [(re.compile(r"^localtext-regions(\.extra)?\.csv\|REGIONTEXT\|[^|]+\|0$"), 30, "지역 이름")]


def problem(en: str, ko: str, key: str = "") -> str | None:
    """번역문이 게임에서 깨질 이유가 있으면 그 설명을 돌려준다. key 는 "테이블파일|섹션|행|순번" (길이 제한 판정용)."""
    if '"' in ko:
        return "큰따옴표 사용 불가"
    if any(c in ko for c in "\n\r\t"):
        return "줄바꿈·탭 문자 사용 불가"
    if srtext.tokens(en) != srtext.tokens(ko):
        return f"토큰 불일치: 원문 {srtext.tokens(en)} / 번역 {srtext.tokens(ko)}"
    if bad := srutf8.unsupported(ko):
        return f"게임에 넣을 수 없는 문자: {' '.join(bad)} (한자 일부는 쓸 수 없습니다 — 한글로 풀어 쓰세요)"
    if key.startswith(MAP_NAMES_TABLE + "|"):
        if len(ko) > len(en):
            # 게임은 그리기 버퍼를 원래 이름의 바이트 수만큼만 잡는다: 그보다 긴 이름은 뒤가 잘린다
            return f"지도 이름이 원래 이름보다 깁니다: {len(ko)}자 (최대 {len(en)}자)"
        if re.search(r"[A-Za-zÀ-ÿ()]", ko):
            return "지도 이름은 한글로만 적습니다(로마자·괄호 불가)"
    for pattern, limit, what in BYTE_LIMITS:
        size = len(srutf8.encode(ko))
        if pattern.search(key) and size > limit:
            return f"{what}이 너무 깁니다: {size}바이트 (최대 {limit}, 한글 한 자 = 3바이트)"
    return None


def notranslate(cfg: Config) -> re.Pattern[str] | None:
    """mods/korean/notranslate.txt 의 정규식들을 하나로 묶는다(번역하면 게임에서 깨지는 키)."""
    path = cfg.korean_mod_dir / "notranslate.txt"
    if not path.is_file():
        return None
    patterns = [line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines()]
    patterns = [p for p in patterns if p]
    return re.compile("|".join(f"(?:{p})" for p in patterns)) if patterns else None


def check(cfg: Config) -> list[str]:
    """번역문 검증: 서식 토큰 보존(순서 포함), 금지 문자, 번역 금지 키."""
    problems = []
    skip = notranslate(cfg)
    for path in sorted(cfg.translation_dir.glob("*.csv")):
        for key, row in read_table(path).items():
            if not row.ko:
                continue
            why = "번역 금지 키(notranslate.txt)" if skip and skip.search(key) \
                else problem(row.en, row.ko, f"{path.name}|{key}")
            if why:
                problems.append(f"{path.name}: {key}: {why}")
    return problems


def inconsistencies(cfg: Config, max_len: int = 60) -> list[tuple[str, dict[str, list[str]]]]:
    """같은 영어 원문(대소문자·앞뒤 공백 무시)이 서로 다르게 번역된 경우: (원문, {번역: [위치…]})."""
    groups: dict[str, dict[str, list[str]]] = {}
    for path in sorted(cfg.translation_dir.glob("*.csv")):
        for key, row in read_table(path).items():
            if row.ko and len(row.en) <= max_len:
                groups.setdefault(row.en.strip().casefold(), {}).setdefault(row.ko.strip(), []).append(
                    f"{path.stem}:{key}")
    return [(en, kos) for en, kos in groups.items() if len(kos) > 1]


def _translations(path: Path, skip: re.Pattern[str] | None = None) -> dict[str, str]:
    return {k: r.ko.translate(PUNCT) for k, r in read_table(path).items()
            if r.ko and not (skip and skip.search(k))}


def _add_extra_regions(doc: srtext.Document, extras: dict[str, str]) -> int:
    """REGIONTEXT 섹션 끝에 영어판에는 없는 지역 이름 행을 더한다."""
    section = [i for i, ln in enumerate(doc.lines) if ln.section == "REGIONTEXT"]
    if not section or not extras:
        return 0
    new = [srtext.Line([f"{key.split('|')[1]}, ", ko, ""], "REGIONTEXT", key.split("|")[1]) for key, ko in extras.items()]
    doc.lines[section[-1] + 1:section[-1] + 1] = new
    return len(new)


def map_name_entries(cfg: Config) -> dict[bytes, str]:
    """훅이 쓸 이름 사전: 게임이 그리는 바이트열(대문자화된 원래 이름) → 한글 이름.

    훅은 그려지는 문자열이 이름과 **똑같을 때** 통째로 바꾼다. 그래서 번역하지 않고 영어로 그려지는 다른 문구와
    철자가 같은 이름은 뺀다(그 문구까지 도시 이름으로 바뀌므로).
    """
    skip = notranslate(cfg)
    shown_in_english: set[bytes] = set()
    for path in sorted(cfg.translation_dir.glob("*.csv")):
        if path.name == MAP_NAMES_TABLE:
            continue
        for key, row in read_table(path).items():
            if (not row.ko or (skip and skip.search(key))) and len(row.en) <= MAP_NAME_MAX:
                shown_in_english.add(game_upper(row.en.encode("cp1252", "replace")))
    entries: dict[bytes, str] = {}
    for key, ko in _translations(cfg.translation_dir / MAP_NAMES_TABLE, skip).items():
        drawn = game_upper(key.split("|", 1)[1].encode("cp1252"))
        if 2 <= len(drawn) <= MAP_NAME_MAX and drawn not in shown_in_english and "\t" not in ko:
            entries.setdefault(drawn, ko)
    return entries


def build_text(cfg: Config, out_root: Path) -> tuple[int, set[str]]:
    """out_root(게임 루트 구조) 아래에 한국어 텍스트 파일을 만든다. (적용된 번역 수, 쓰인 비ASCII 문자 집합)."""
    applied = 0
    used: set[str] = set()
    skip = notranslate(cfg)
    out_lang = out_root / "Localize" / cfg.target_lang

    def emit(dest: Path, text: str) -> None:
        used.update(ch for ch in text if ord(ch) > 0x7F)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(srutf8.encode(text))

    for path in sorted(cfg.source_dir.rglob("*")):
        rel = path.relative_to(cfg.source_dir)
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTS or rel.parts[0].lower() == "fonts" \
                or path.name.lower() == "tipofday.csv":
            continue
        doc = srtext.parse(decode_cp1252(path.read_bytes()).translate(PUNCT))
        applied += doc.apply(_translations(cfg.translation_dir / table_name(rel), skip))
        if path.name.lower() == REGIONS_NAME.lower():
            applied += _add_extra_regions(doc, _translations(cfg.translation_dir / EXTRA_REGIONS_TABLE, skip))
        emit(out_lang / rel, doc.serialize())

    gui = _translations(cfg.translation_dir / GUI_TABLE, skip)
    lines = ["// LocalText-GUI (generated by srkit)", "&&GUITRANS"]
    lines += [f'"{key.split("|", 1)[1]}", "{ko}", ' for key, ko in gui.items()]
    emit(out_lang / GUI_NAME, "\n".join(lines) + "\n\n")

    # 시나리오 폴더 안의 현지화 파일: 같은 자리의 Localize/<대상 언어>/ 로 낸다(번역이 없어도 영어로라도 있어야 한다)
    for rel in scenario_files(cfg):
        doc = srtext.parse(decode_cp1252((cfg.game_dir / rel).read_bytes()).translate(PUNCT))
        applied += doc.apply(_translations(cfg.translation_dir / scenario_table(rel), skip))
        parts = [cfg.target_lang if p.lower() == cfg.source_lang.lower() else p for p in rel.parts]
        emit(out_root.joinpath(*parts), doc.serialize())

    # 지도 이름 사전(훅 DLL 이 읽는다). 키는 원본 데이터의 바이트 그대로라 텍스트로 다루지 않고 바이트로 쓴다
    names = map_name_entries(cfg)
    if names:
        used.update(ch for ko in names.values() for ch in ko if ord(ch) > 0x7F)
        (out_lang / MAP_NAMES_FILE).write_bytes(
            b"".join(drawn + b"\t" + srutf8.encode(ko) + b"\n" for drawn, ko in sorted(names.items())))
    return applied + len(gui) + len(names), used


def font_slots(fontinfo: Path) -> dict[str, int]:
    """fontinfo.font 에서 spritefont 파일 이름 → 스타일(0 보통, 1 굵게, 2 기울임)."""
    slots: dict[str, int] = {}
    for line in fontinfo.read_text(encoding="cp1252").splitlines():
        cols = [c.strip() for c in line.split(",")]
        if cols[0].lower() == "fontimage" and len(cols) > 5 and cols[1]:
            slots[cols[1].upper()] = int(cols[5] or 0)
    return slots


def default_charset() -> str:
    """KS X 1001 한글 2,350자 + 호환 자모 + 자주 쓰는 기호."""
    hangul = "".join(bytes([hi, lo]).decode("euc_kr") for hi in range(0xB0, 0xC9) for lo in range(0xA1, 0xFF))
    jamo = "".join(chr(c) for c in range(0x3131, 0x3164))
    return hangul + jamo + "·※→←↑↓×÷±°℃"


def build_fonts(cfg: Config, out_fonts: Path, extra_chars: set[str], only: set[str] | None = None) -> list[str]:
    src = cfg.source_dir / "Fonts"
    out_fonts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "fontinfo.font", out_fonts / "fontinfo.font")
    slots = font_slots(src / "fontinfo.font")
    built = []
    for path in sorted(src.glob("*.spritefont")):
        name = path.stem.upper()
        if only and name not in only:
            continue
        base = sf.load(path)
        have = {g.char for g in base.glyphs}
        # 원본에 이미 있는 문자는 원본 글리프를 그대로 쓴다
        chars = "".join(sorted(c for c in set(default_charset()) | extra_chars if ord(c) not in have))
        baseline, _ = sf.metrics(base)
        em = sf.hangul_em(base)
        weight = cfg.hangul_weight_bold if slots.get(name) == 1 else cfg.hangul_weight_regular
        new = sf.render_glyphs(cfg.hangul_font, em, chars, baseline, weight, sf.left_pad(base))
        new += [sf.blank_glyph(srutf8.PH_CELL, float(em)), sf.blank_glyph(srutf8.PH_ZERO, 0.0)]
        sf.save(sf.augment(base, new), out_fonts / path.name)
        built.append(path.name)
    return built


def patch_uisettings(text: str, lang_dir: str, display: str, position: int = 1) -> str:
    """INI/UISettings.csv 의 언어 목록(langdirs/langs)에 새 언어를 넣는다. 끝의 빈 항목은 유지.

    옵션 화면의 언어 목록은 앞의 6개만 보여 준다(게임 화면으로 확인). 끝에 붙이면 7번째라 고를 수 없으므로
    영어 다음(position)에 넣는다 — 대신 원래 6번째였던 언어(포르투갈어)가 목록에서 밀려난다.
    이미 들어 있으면 그 자리로 옮긴다.
    """
    out = []
    for line in text.split("\n"):
        head = line.split(",", 1)[0].strip().lower()
        value = {"langdirs": lang_dir, "langs": display}.get(head)
        if value and '"' in line:
            items = re.findall(r'"([^"]*)"', line)
            closed = items[-1] == ""
            names = [item for item in items if item not in ("", value)]
            names.insert(min(position, len(names)), value)
            line = (line[:line.index('"')] + ", ".join(f'"{item}"' for item in names + [""] * closed)
                    + line[len(line.rstrip()):])
        out.append(line)
    return "\n".join(out)


def build(cfg: Config, *, fonts: bool = True, only_fonts: set[str] | None = None) -> dict:
    """build/korean/ 아래에 게임 루트 구조(MODS 형)로 한글화 모드를 만든다."""
    out = cfg.build_dir / "korean"
    out_lang = out / "Localize" / cfg.target_lang
    if out.exists():
        shutil.rmtree(out)
    applied, used = build_text(cfg, out)
    shutil.copy2(cfg.source_dir / "LOCALTEXT.csv", out_lang / "LOCALTEXT.csv")
    sprite_notes: list[str] = []
    if (cfg.source_dir / "Graphics").is_dir():
        shutil.copytree(cfg.source_dir / "Graphics", out_lang / "Graphics")
        spec = cfg.korean_mod_dir / "sprites.toml"
        if spec.is_file():  # 그림으로 들어 있는 문구(메뉴·제목·버튼)를 한글로 다시 그린다
            sprite_notes = sprites.localize(cfg.game_dir, spec, out_lang / "Graphics")
    built = build_fonts(cfg, out_lang / "Fonts", used, only_fonts) if fonts else []
    ui = cfg.game_dir / "INI" / "UISettings.csv"
    (out / "INI").mkdir(parents=True, exist_ok=True)
    (out / "INI" / "UISettings.csv").write_bytes(
        patch_uisettings(ui.read_bytes().decode("latin-1"), cfg.target_lang, cfg.display_name).encode("latin-1"))
    has_hook = hook.output(cfg).is_file()
    if has_hook:
        shutil.copy2(hook.output(cfg), out / hook.PROXY_NAME)
    return {"out": out, "applied": applied, "fonts": built, "nonascii_chars": len(used), "hook": has_hook,
            "sprite_notes": sprite_notes}
