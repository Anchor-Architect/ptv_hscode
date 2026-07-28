#!/usr/bin/env python3
"""
hs2026_clean.csv → hs_data.json 재생성

기존 hs_data.json 은 `e`(영문 경로)에 CSV 의 path_en 만 그대로 담아,
세부 품목명(en 컬럼)이 통째로 빠져 있었다. 그 결과 3,047건(26.7%)의 코드가
형제 코드와 완전히 같은 설명을 갖게 되어 8자리 세부 호를 구분할 수 없었다.
(예: 0306 의 71개 코드가 모두 "Crustaceans, whether in shell or not..." 하나)

이 스크립트는 path 끝에 leaf 가 없으면 붙여서 각 코드가 고유한 설명을 갖게 한다.

사용법:
    python3 tools/build_hs_data.py                # hs_data.json 갱신(기존은 .bak 로 백업)
    python3 tools/build_hs_data.py --check        # 변경 없이 통계만 출력
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(ROOT, "hs2026_clean.csv")
JSON_PATH = os.path.join(ROOT, "hs_data.json")

# JSON 필드 ← CSV 컬럼 (전량 일치 검증됨)
RATE_FIELDS = [("u", "unit"), ("tt", "tt"), ("ud", "uudai"), ("vt", "vat"),
               ("ak", "akfta"), ("vj", "vjepa"), ("at", "atiga"), ("cp", "cptpp")]
SEP = " > "


def join_path(path, leaf):
    """경로 끝에 leaf 가 없으면 붙인다. 이미 있으면 그대로."""
    path = (path or "").strip()
    leaf = (leaf or "").strip()
    if not leaf:
        return path
    if not path:
        return leaf
    # 마지막 구간이 leaf 와 같으면 중복 없음
    if path.split(SEP)[-1].strip() == leaf:
        return path
    if path.endswith(leaf):
        return path
    return path + SEP + leaf


def build(rows):
    out, appended = [], 0
    for r in rows:
        e = join_path(r.get("path_en"), r.get("en"))
        v = join_path(r.get("path_vn"), r.get("vn"))
        if e != (r.get("path_en") or "").strip():
            appended += 1
        rec = {"c": r["code"], "e": e, "v": v}
        for jk, ck in RATE_FIELDS:
            rec[jk] = (r.get(ck) or "").strip()
        out.append(rec)
    return out, appended


def dup_stats(records):
    """설명이 형제와 완전히 동일해 구분 불가한 항목 수"""
    by_text = {}
    for r in records:
        by_text.setdefault(r["e"], []).append(r["c"])
    dup = sum(len(v) for v in by_text.values() if len(v) > 1)
    return dup, len(records)


def main():
    check_only = "--check" in sys.argv
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    records, appended = build(rows)

    before = None
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, encoding="utf-8") as f:
            before = dup_stats(json.load(f))
    after = dup_stats(records)

    print(f"CSV 행: {len(rows)} → 생성 항목: {len(records)}")
    print(f"leaf 를 새로 붙인 항목: {appended}")
    if before:
        print(f"설명 중복(구분 불가): {before[0]} ({before[0]/before[1]*100:.1f}%) "
              f"→ {after[0]} ({after[0]/after[1]*100:.1f}%)")
    else:
        print(f"설명 중복: {after[0]} ({after[0]/after[1]*100:.1f}%)")

    if check_only:
        print("\n--check 모드: 파일을 쓰지 않았습니다.")
        return

    if os.path.exists(JSON_PATH):
        os.replace(JSON_PATH, JSON_PATH + ".bak")
        print(f"기존 파일 백업: {os.path.basename(JSON_PATH)}.bak")
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
    print(f"생성 완료: {os.path.basename(JSON_PATH)} "
          f"({os.path.getsize(JSON_PATH)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
