#!/usr/bin/env python3
"""
국가별 관세표 → 앱이 읽는 JSON 생성

    구글 시트(실무자 편집)  또는  로컬 CSV
              │  이 스크립트 (관세표가 바뀔 때만 실행)
              ▼
        data/<국가>.json   ← 앱은 선택한 국가 것만 내려받음

시트를 원본으로 두면 담당자가 직접 검수·수정할 수 있고, 앱은 정적 파일만
읽으므로 조회가 빠르고 API 할당량 걱정이 없다.

사용법
    python3 tools/build_country_data.py vn            # tools/countries/vn.json 설정으로 생성
    python3 tools/build_country_data.py vn --check    # 파일을 쓰지 않고 통계만
    python3 tools/build_country_data.py --all         # 설정된 모든 국가

구글 시트를 원본으로 쓰려면
    1) 시트를 '링크가 있는 모든 사용자 · 뷰어' 로 공유
    2) 국가 설정의 source_csv 를 아래 형식 URL 로 교체
       https://docs.google.com/spreadsheets/d/<시트ID>/export?format=csv&gid=<탭ID>
"""

import csv
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONF_DIR = os.path.join(HERE, "countries")
OUT_DIR = os.path.join(ROOT, "data")
SEP = " > "


def load_rows(source):
    """로컬 CSV 경로 또는 구글시트 CSV export URL 에서 행을 읽는다."""
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=120) as r:
            text = r.read().decode("utf-8-sig")
        if text.lstrip().startswith("<"):
            raise SystemExit(
                "시트를 CSV 로 받지 못했습니다(HTML 응답).\n"
                "  · 시트 공유 설정을 '링크가 있는 모든 사용자 · 뷰어' 로 바꾸세요\n"
                "  · URL 이 .../export?format=csv&gid=... 형식인지 확인하세요")
        return list(csv.DictReader(io.StringIO(text)))
    path = source if os.path.isabs(source) else os.path.join(ROOT, source)
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def join_path(path, leaf):
    """경로 끝에 세부 품목명이 없으면 붙인다.
    관세표 원본은 상위 경로만 담고 leaf 를 별도 컬럼에 두는 경우가 많은데,
    그대로 두면 형제 코드가 모두 같은 설명이 되어 세부 호를 구분할 수 없다."""
    path = (path or "").strip()
    leaf = (leaf or "").strip()
    if not leaf:
        return path
    if not path:
        return leaf
    if path.split(SEP)[-1].strip() == leaf or path.endswith(leaf):
        return path
    return path + SEP + leaf


def pick(row, colmap, key):
    col = colmap.get(key)
    return (row.get(col) or "").strip() if col else ""


def build(conf, rows):
    cols = conf["columns"]
    rates = conf.get("rates", [])
    items, appended, missing_code = [], 0, 0

    for row in rows:
        code = pick(row, cols, "code")
        if not code:
            missing_code += 1
            continue
        e = join_path(pick(row, cols, "path_en"), pick(row, cols, "desc_en"))
        v = join_path(pick(row, cols, "path_local"), pick(row, cols, "desc_local"))
        if e != pick(row, cols, "path_en"):
            appended += 1

        r = {}
        for spec in rates:
            val = (row.get(spec["col"]) or "").strip()
            if val:
                r[spec["key"]] = val

        items.append({"c": code, "e": e, "v": v,
                      "u": pick(row, cols, "unit"), "r": r})

    meta = {k: conf[k] for k in
            ("country", "name_ko", "name_en", "flag", "version", "source", "digits", "valid_from")
            if k in conf}
    meta["count"] = len(items)
    meta["rates"] = [{k: s[k] for k in ("key", "label", "tip", "hero", "highlight", "badge") if k in s}
                     for s in rates]
    return {"meta": meta, "items": items}, appended, missing_code


def dup_ratio(items):
    seen = {}
    for it in items:
        seen[it["e"]] = seen.get(it["e"], 0) + 1
    dup = sum(n for n in seen.values() if n > 1)
    return dup, len(items)


def run(name, check_only):
    conf_path = os.path.join(CONF_DIR, f"{name}.json")
    if not os.path.exists(conf_path):
        raise SystemExit(f"설정 파일이 없습니다: {conf_path}")
    with open(conf_path, encoding="utf-8") as f:
        conf = json.load(f)

    print(f"\n[{conf['country']}] {conf.get('name_ko','')} · {conf.get('version','')}")
    rows = load_rows(conf["source_csv"])
    print(f"  원본 행: {len(rows)}")

    out, appended, missing = build(conf, rows)
    dup, total = dup_ratio(out["items"])
    print(f"  생성 항목: {total}"
          + (f" (코드 없는 행 {missing}건 건너뜀)" if missing else ""))
    print(f"  세부 품목명 보강: {appended}건")
    print(f"  설명 중복(세부 호 구분 불가): {dup}건 ({dup/total*100:.1f}%)" if total else "")
    print(f"  세율 항목: {', '.join(s['key'] for s in conf.get('rates', []))}")

    if check_only:
        print("  --check: 파일을 쓰지 않았습니다.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    dest = os.path.join(OUT_DIR, f"{conf['country']}.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  생성 완료: data/{conf['country']}.json ({os.path.getsize(dest)/1024/1024:.1f} MB)")


def write_index():
    """앱이 국가 목록을 읽을 수 있게 data/index.json 생성"""
    entries = []
    for fn in sorted(os.listdir(CONF_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(CONF_DIR, fn), encoding="utf-8") as f:
            c = json.load(f)
        if os.path.exists(os.path.join(OUT_DIR, f"{c['country']}.json")):
            entries.append({k: c[k] for k in
                            ("country", "name_ko", "name_en", "flag", "version") if k in c})
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"countries": entries}, f, ensure_ascii=False, indent=1)
    print(f"\ndata/index.json: {', '.join(e['country'] for e in entries) or '(없음)'}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    names = ([f[:-5] for f in sorted(os.listdir(CONF_DIR)) if f.endswith(".json")]
             if "--all" in sys.argv else args)
    if not names:
        raise SystemExit(__doc__)
    for n in names:
        run(n, check_only)
    if not check_only:
        write_index()


if __name__ == "__main__":
    main()
