# PTV · HS Code

2026년 베트남 수출입 관세표(Biểu thuế XNK) 기반으로, 인보이스·패킹리스트의 품목 설명을 붙여넣으면 가장 가까운 HS 코드를 세율 근거와 함께 찾아주는 웹 도구. 한국어·영어·베트남어 혼용 지원.

> **참조용** · 본 도구가 제시하는 HS 코드는 참조용입니다. 정확한 원재료·HS 해석·사용 목적에 따라 코드가 달라질 수 있으며, 최종 신고 분류는 통관 담당자가 확정합니다. 세율은 6개월~1년 주기로 갱신될 수 있으니 신고 시점에 재확인하세요.

## 구성

| 파일 | 역할 |
|---|---|
| `index_v2.html` | 프론트엔드(단일 파일, 바닐라 JS) |
| `hs_data.json` | 정제된 관세표 데이터 (약 11,414개 코드) |
| `hs2026_clean.csv` | 정제 원본 (DB 이관·데이터 갱신용) |
| `api/messages.py` | **배포용** Anthropic 프록시 (Vercel 서버리스 함수) |
| `proxy_server.py` | **로컬 개발용** 정적 서빙 + 프록시 |
| `vercel.json` | Vercel 라우팅/함수 설정 |

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

## 데이터 갱신

베트남이 새 관세표를 공표하면 정제 CSV로 `hs_data.json`을 재생성해 교체합니다. 세율은 법령 개정으로 6개월~1년 주기 변동될 수 있어, 갱신 시 이전 버전과 비교(diff)해 변경분을 확인하는 것을 권장합니다.

---

데이터 기준: 2026년 베트남 수출입 관세표
