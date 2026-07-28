# PTV · HS Code

2026년 베트남 수출입 관세표(Biểu thuế XNK) 기반으로, 인보이스·패킹리스트의 품목 설명을 붙여넣으면 가장 가까운 HS 코드를 세율 근거와 함께 찾아주는 웹 도구. 한국어·영어·베트남어 혼용 지원.

> **참조용** · 본 도구가 제시하는 HS 코드는 참조용입니다. 정확한 원재료·HS 해석·사용 목적에 따라 코드가 달라질 수 있으며, 최종 신고 분류는 통관 담당자가 확정합니다. 세율은 6개월~1년 주기로 갱신될 수 있으니 신고 시점에 재확인하세요.

## 구성

| 파일 | 역할 |
|---|---|
| `index_v2.html` | 프론트엔드(단일 파일, 바닐라 JS) |
| `data/<국가>.json` | 국가별 관세표 (품목 + 세율 정의). 앱은 선택한 국가 것만 로드 |
| `data/index.json` | 사용 가능한 국가 목록 |
| `tools/countries/*.json` | 국가별 원본 위치·컬럼 매핑·세율 정의 |
| `tools/build_country_data.py` | 원본(구글 시트/CSV) → `data/<국가>.json` 생성 |
| `tools/accuracy.html` | 정확도 회귀 테스트 (브라우저에서 실행) |
| `hs2026_clean.csv` | 베트남 관세표 원본 |
| `api/messages.py` | **배포용** Anthropic 프록시 (Vercel 서버리스 함수) |
| `proxy_server.py` | **로컬 개발용** 정적 서빙 + 프록시 |
| `vercel.json` | Vercel 라우팅/함수 설정 |

### 데이터 구조

관세표는 **국가별로 다릅니다** — 앞 6자리는 국제 공통(WCO)이지만 세분류 자릿수와
관세율은 국가마다 달라요. 그래서 세율 종류·라벨을 코드에 고정하지 않고
`data/<국가>.json` 의 `meta.rates` 에서 읽습니다. 새 국가를 추가할 때 앱 코드는
건드리지 않아도 됩니다.

```
data/VN.json
  meta.rates[]  ← 세율 종류·라벨(3개 국어)·설명·화면 표시 순서
  items[]       ← { c: 코드, e: 영문 경로, v: 현지어 경로, u: 단위, r: {세율키: 값} }
```

`?country=KR` 처럼 쿼리로 국가를 지정할 수 있습니다(기본 `VN`).

## 로컬 실행

```bash
cp .env.example .env      # .env 를 열어 실제 ANTHROPIC_API_KEY 입력
python3 proxy_server.py   # http://localhost:8000/index_v2.html
```

- API 키는 코드가 아니라 `.env`(git 제외)에만 둡니다. 프론트엔드에 키를 넣으면 안 됩니다(노출·CORS).
- 키가 없으면 앱은 키워드 근사(데모) 모드로 동작합니다.

## Vercel 배포

1. Vercel에서 이 GitHub 저장소를 **Import**
2. **Settings → Environment Variables** 에 `ANTHROPIC_API_KEY` 등록 (**새로 발급받은 키** 권장)
3. **Deploy**

정적 파일은 그대로 서빙되고, `/api/messages` 요청은 `api/messages.py` 서버리스 함수가 처리합니다. 키는 서버에만 있고 브라우저에 노출되지 않습니다.

## 데이터 갱신 · 국가 추가

원본은 **구글 시트에서 편집**하고, 관세표가 바뀔 때만 변환 스크립트를 돌립니다.
런타임에 시트를 조회하지 않으므로(API 지연·할당량 문제) 조회는 정적 파일만큼 빠릅니다.

```bash
python3 tools/build_country_data.py vn --check   # 변경 없이 통계만 확인
python3 tools/build_country_data.py vn           # data/VN.json 생성
python3 tools/build_country_data.py --all        # 등록된 모든 국가
```

**새 국가 추가**
1. `tools/countries/<국가>.json` 작성 — 원본 위치, 컬럼 매핑, 세율 정의(라벨·설명·표시순서)
2. 위 스크립트 실행

**구글 시트를 원본으로 쓰려면** 시트를 '링크가 있는 모든 사용자 · 뷰어'로 공유하고,
설정의 `source_csv` 를 아래 형식으로 바꿉니다.

```
https://docs.google.com/spreadsheets/d/<시트ID>/export?format=csv&gid=<탭ID>
```

세율은 법령 개정으로 6개월~1년 주기 변동될 수 있습니다. 갱신 후에는
`tools/accuracy.html` 로 정확도가 떨어지지 않았는지 확인하세요.

### 알려진 데이터 한계

베트남 원본에는 6자리 소호 설명이 없어, 형제 코드끼리 설명이 같은 항목이
**약 10%** 남아 있습니다. 이 경우 앞 6자리까지는 분류가 맞지만 마지막 2자리는
자동으로 정할 수 없어, 앱이 적합도를 낮추고 경고를 표시합니다.

---

데이터 기준: 2026년 베트남 수출입 관세표
