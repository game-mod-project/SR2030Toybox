"""기계 번역 작업 단위(청크): 내보내기 → (번역) → 검증 → 번역 테이블에 병합.

청크는 build/mt/ 에 JSONL 로 둔다.
    <테이블>[+태그]~NNN.in.jsonl    {"key": ..., "en": ...}      번역할 행
    <테이블>[+태그]~NNN.out.jsonl   {"key": ..., "ko": ...}      번역 결과 (ko 가 "" 이면 일부러 번역하지 않음)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import korean
from .config import Config

IN, OUT = ".in.jsonl", ".out.jsonl"


def chunk_dir(cfg: Config) -> Path:
    return cfg.build_dir / "mt"


def out_path(in_path: Path) -> Path:
    return in_path.with_name(in_path.name[:-len(IN)] + OUT)


def table_of(in_path: Path) -> str:
    return in_path.name[:-len(IN)].rsplit("~", 1)[0].split("+", 1)[0] + ".csv"


def export(cfg: Config, table: str, *, max_rows: int = 400, max_chars: int = 20000,
           key_filter: str | None = None, tag: str = "") -> list[Path]:
    """아직 번역이 없는 행을 청크 파일로 내보낸다. 같은 이름(테이블+태그)의 기존 청크는 지운다."""
    rows = korean.read_table(cfg.translation_dir / table)
    if not rows:
        raise ValueError(f"번역 테이블이 없습니다: {table}")
    skip = korean.notranslate(cfg)
    todo = [(k, r.en) for k, r in rows.items()
            if not r.ko and (not key_filter or re.search(key_filter, k)) and not (skip and skip.search(k))]
    stem = table[:-len(".csv")] + (f"+{tag}" if tag else "")
    out_dir = chunk_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{stem}~*.jsonl"):
        old.unlink()
    chunks: list[list[tuple[str, str]]] = [[]]
    size = 0
    for key, en in todo:
        if chunks[-1] and (len(chunks[-1]) >= max_rows or size + len(en) > max_chars):
            chunks.append([])
            size = 0
        chunks[-1].append((key, en))
        size += len(en)
    paths = []
    for i, chunk in enumerate(c for c in chunks if c):
        path = out_dir / f"{stem}~{i:03d}{IN}"
        path.write_text("".join(json.dumps({"key": k, "en": en}, ensure_ascii=False) + "\n" for k, en in chunk),
                        encoding="utf-8")
        paths.append(path)
    return paths


@dataclass
class ChunkResult:
    path: Path
    total: int = 0
    valid: dict[str, str] = field(default_factory=dict)   # key → ko (검증 통과)
    skipped: int = 0                                      # 일부러 번역하지 않은 행(ko == "")
    problems: list[str] = field(default_factory=list)


def check(in_path: Path) -> ChunkResult:
    source = {r["key"]: r["en"] for r in map(json.loads, in_path.read_text(encoding="utf-8").splitlines())}
    result = ChunkResult(in_path, total=len(source))
    out = out_path(in_path)
    if not out.is_file():
        result.problems.append(f"출력 파일 없음: {out.name}")
        return result
    seen: set[str] = set()
    for n, line in enumerate(out.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            key, ko = row["key"], row["ko"]
        except (ValueError, KeyError, TypeError):
            result.problems.append(f"{n}행: JSON 형식 오류 (필요: {{\"key\": ..., \"ko\": ...}})")
            continue
        if key not in source:
            result.problems.append(f"{n}행: 입력에 없는 키 {key!r}")
        elif key in seen:
            result.problems.append(f"{n}행: 중복 키 {key!r}")
        elif not isinstance(ko, str):
            result.problems.append(f"{n}행: ko 가 문자열이 아님 ({key})")
        elif ko == "":
            result.skipped += 1
        elif why := korean.problem(source[key], ko, f"{table_of(in_path)}|{key}"):
            result.problems.append(f"{n}행 {key}: {why}")
        else:
            result.valid[key] = ko
        seen.add(key)
    missing = [k for k in source if k not in seen]
    if missing:
        result.problems.append(f"빠진 행 {len(missing)}개: " + ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else ""))
    return result


def import_all(cfg: Config, *, overwrite: bool = False) -> list[tuple[ChunkResult, int]]:
    """검증을 통과한 행만 번역 테이블에 넣는다(status=mt). 이미 번역이 있는 행은 overwrite 일 때만 바꾼다."""
    results = []
    by_table: dict[str, list[ChunkResult]] = {}
    for in_path in sorted(chunk_dir(cfg).glob(f"*{IN}")):
        by_table.setdefault(table_of(in_path), []).append(check(in_path))
    for table, chunks in by_table.items():
        path = cfg.translation_dir / table
        rows = korean.read_table(path)
        for chunk in chunks:
            applied = 0
            for key, ko in chunk.valid.items():
                row = rows.get(key)
                if row and (overwrite or not row.ko) and row.ko != ko:
                    rows[key] = korean.Row(row.en, ko, korean.STATUS_MT)
                    applied += 1
            results.append((chunk, applied))
        korean.write_table(path, rows)
    return results
