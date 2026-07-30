#!/usr/bin/env python3
"""
미국 HTS(공식 JSON) → data/US.json  [1단계: 기본세율]

미국은 다른 나라와 관세표 구조가 완전히 달라 전용 파서가 필요하다.
  · 세율이 8자리(예: 6110.11.00)에만 있고 10자리 통계코드는 상속받는다
  · special(FTA)이 "Free (A+,...,KR,...)" 형식 — KR 포함 여부로 한·미 FTA 적용 판단
  · general 세율이 "Free"·"2.5%"·"1¢/kg" 처럼 문장/종량세 → 숫자 변환 금지, 원문 유지
  · 품목 절반 이상에 9903 추가관세 각주 → 이 파일은 '기본 층'일 뿐. add 플래그만 세우고
    실제 232/301 금액은 2단계(오버레이)에서 채운다.

사용법
    python3 tools/build_us.py                 # /tmp/us_hts.json 사용(있으면)
    python3 tools/build_us.py <경로_또는_URL>  # 원본 지정
    python3 tools/build_us.py --check         # 파일 안 쓰고 통계만

원본: USITC HTS export JSON — https://hts.usitc.gov  (Export 기능)
"""

import datetime as _dt
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "US.json")
DEFAULT_SRC = "/tmp/us_hts.json"
SEP = " > "


def load(src):
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=180) as r:
            return json.loads(r.read())
    with open(src, encoding="utf-8") as f:
        return json.load(f)


def indent_of(r):
    try:
        return int(str(r.get("indent") or "0"))
    except ValueError:
        return 0


def korus_rate(special):
    """special 문자열에서 한국(KR) 에 적용되는 FTA 세율만 추출. KR 미포함이면 '' """
    if not special:
        return ""
    m = re.match(r"\s*(.+?)\s*\(([^)]*)\)\s*$", special)
    if not m:
        return special.strip()          # 괄호 없는 드문 케이스 — 그대로
    rate, countries = m.group(1).strip(), m.group(2)
    codes = [c.strip() for c in countries.split(",")]
    return rate if "KR" in codes else ""


def has_addduty(r):
    """9903(232/301 등) 추가관세 대상인가 — 각주/additionalDuties 에서 감지"""
    blob = json.dumps(r.get("footnotes") or "") + str(r.get("additionalDuties") or "")
    return "9903" in blob


def build(rows):
    stack = []           # 조상 노드(경로·세율 상속용)
    emitted = []         # {code, path[], general, special, other, units, add}
    for r in rows:
        ind = indent_of(r)
        while stack and stack[-1]["indent"] >= ind:
            stack.pop()
        node = {"indent": ind, "desc": (r.get("description") or "").strip(),
                "htsno": r.get("htsno") or "",
                "general": (r.get("general") or "").strip(),
                "special": (r.get("special") or "").strip(),
                "other": (r.get("other") or "").strip(),
                "units": r.get("units") or [],
                "add": has_addduty(r)}
        stack.append(node)
        h = node["htsno"]
        if not h or len(h.replace(".", "")) < 8:
            continue                     # 상위 그룹행은 경로로만 쓰고 코드로는 안 냄
        if h[:2] in ("98", "99"):
            continue                     # 98·99류는 특수·임시 규정(추가관세/일시감면) — 품목 분류가 아니라 제외
                                         # (9903 추가관세는 원본에서 2단계 오버레이로 따로 뽑는다)

        # 조상에서 세율 상속(자기 값이 비면 가까운 조상 값)
        def inherit(field):
            for n in reversed(stack):
                if n[field]:
                    return n[field]
            return ""
        path = [n["desc"] for n in stack if n["desc"]]
        emitted.append({
            "code": h.replace(".", ""),
            "path": path,
            "general": inherit("general"),
            "special": inherit("special"),
            "other": inherit("other"),
            "units": next((n["units"] for n in reversed(stack) if n["units"]), []),
            "add": any(n["add"] for n in stack),
        })

    # 리프만 남긴다(다른 코드의 접두가 되는 상위 8자리는 제외 — 10자리 실코드 우선)
    codes = {e["code"] for e in emitted}
    def is_leaf(c):
        return not any(o != c and o.startswith(c) for o in codes)
    leaves = [e for e in emitted if is_leaf(e["code"])]

    items = []
    for e in leaves:
        r = {}
        if e["general"]:
            r["mfn"] = "Free" if e["general"].lower() == "free" else e["general"]
        k = korus_rate(e["special"])
        if k:
            r["korus"] = "Free" if k.lower() == "free" else k
        if e["other"]:
            r["general"] = e["other"]
        item = {"c": e["code"], "e": SEP.join(e["path"]), "v": "",
                "u": (e["units"][0] if e["units"] else ""), "r": r}
        if e["add"]:
            item["add"] = 1              # 9903 추가관세 대상 → 앱에서 경고
        items.append(item)
    return items


RATES_META = [
    {"key": "korus", "hero": 1, "highlight": True, "badge": "🇰🇷",
     "label": {"ko": "한·미 FTA (KORUS)", "en": "Korea-US FTA (KORUS)", "vi": "FTA Hàn-Mỹ (KORUS)"},
     "tip": {"ko": "한·미 FTA 세율 — 한국산 원산지증명 제출 시 적용 (한국 수출 시 핵심)",
             "en": "KORUS FTA rate — with Korean certificate of origin",
             "vi": "Thuế FTA Hàn-Mỹ — khi có C/O Hàn Quốc"}},
    {"key": "mfn", "hero": 2,
     "label": {"ko": "기본 관세 (MFN)", "en": "Base duty (MFN)", "vi": "Thuế cơ bản (MFN)"},
     "tip": {"ko": "일반 최혜국(MFN) 세율 — FTA 미적용 시. 'Free'는 무관세",
             "en": "General (MFN) rate — when FTA is not used. 'Free' = duty-free",
             "vi": "Thuế suất MFN — khi không dùng FTA. 'Free' = miễn thuế"}},
    {"key": "general", "hero": 3,
     "label": {"ko": "일반 (비협정국)", "en": "Column 2 (non-NTR)", "vi": "Cột 2 (không NTR)"},
     "tip": {"ko": "정상무역관계(NTR) 없는 극소수 국가에만 적용 (한국은 해당 없음)",
             "en": "Applies only to a few non-NTR countries (not Korea)",
             "vi": "Chỉ áp dụng cho vài nước không NTR (không phải Hàn Quốc)"}},
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    src = args[0] if args else DEFAULT_SRC
    if not (src.startswith("http") or os.path.exists(src)):
        raise SystemExit(f"원본을 찾을 수 없습니다: {src}\n  hts.usitc.gov 의 Export JSON 을 받아 경로를 넘기세요.")

    print(f"원본: {src}")
    rows = load(src)
    items = build(rows)

    # 통계
    add = sum(1 for it in items if it.get("add"))
    korus = sum(1 for it in items if "korus" in it["r"])
    dup = len(items) - len({it["e"] for it in items})
    print(f"  코드(리프): {len(items)}")
    print(f"  한·미 FTA 세율 있는 코드: {korus}")
    print(f"  9903 추가관세 대상(경고 표시): {add} ({add/len(items)*100:.0f}%)")
    print(f"  설명 중복: {dup} ({dup/len(items)*100:.1f}%)")

    if check:
        print("  --check: 파일 안 씀. 샘플 3개:")
        for it in items[:3]:
            print("   ", json.dumps(it, ensure_ascii=False)[:150])
        return

    meta = {"country": "US", "name_ko": "미국", "name_en": "United States", "flag": "🇺🇸",
            "version": "2026 Rev.12", "digits": 10,
            "model": "claude-sonnet-5",   # 미국은 코드 多·구분 미묘 → 분류는 sonnet 으로 정확도 우선

            "updated": _dt.date.today().isoformat(), "built_at": _dt.date.today().isoformat(),
            "source": {"ko": "미국 HTS 2026 (USITC)", "en": "US HTS 2026 (USITC)", "vi": "HTS Hoa Kỳ 2026 (USITC)"},
            "provenance": {"authority": "USITC Harmonized Tariff Schedule",
                           "url": "https://hts.usitc.gov", "format": "json", "national_digits": 10,
                           "cadence": "수시 개정(Revision)", "layers": "base+overlay",
                           "note": "1단계 기본세율만. 9903 추가관세(232/301/122)는 별도 오버레이 필요(품목 절반 이상 해당)."},
            "count": len(items),
            "rates": [{k: s[k] for k in ("key", "label", "tip", "hero", "highlight", "badge") if k in s}
                      for s in RATES_META],
            "notice": {"ko": "미국은 이 기본세율 위에 추가관세(232·301 등)가 얹히는 품목이 많습니다. 🅐 표시가 있으면 실제 부과세율은 더 높을 수 있어요.",
                       "en": "Many US items carry extra duties (232/301) on top of this base rate. Where 🅐 appears, the real rate may be higher.",
                       "vi": "Nhiều mặt hàng Mỹ có thuế bổ sung (232/301) trên thuế cơ bản này. Khi có 🅐, thuế thực tế có thể cao hơn."}}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "items": items}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  생성 완료: data/US.json ({os.path.getsize(OUT)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
