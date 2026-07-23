anchor · HS Code Finder — 1차 버전 실행 안내
=============================================

[중요] 이 앱은 반드시 로컬 웹서버로 열어야 합니다.
파일(index_v2.html)을 브라우저에 직접 드래그하면 데이터(hs_data.json)를
불러오지 못합니다. (브라우저 보안 정책)

■ 실행 방법 (Mac/Linux)
  1) 이 폴더에서 터미널 열기
  2) python3 -m http.server 8000
  3) 브라우저에서 http://localhost:8000/index_v2.html 열기

■ 실행 방법 (Windows)
  1) 이 폴더에서 명령프롬프트 열기
  2) python -m http.server 8000
  3) 브라우저에서 http://localhost:8000/index_v2.html 열기

■ 파일 구성
  - index_v2.html   : 1차 버전 (붙여넣기 UX, 한/영/베, 근거·되물음·기억)
  - hs_data.json    : 2026 관세표 정제 데이터 (11,414개 최종 코드)
  - hs2026_clean.csv: 정제 원본 (DB 이관용)

■ AI 판단 모드
  - 이 앱은 Claude API 환경에서 열면 AI가 근거와 함께 최적 코드를 판단합니다.
  - 일반 로컬 환경(데모)에서는 키워드 근사 결과를 보여줍니다.
    (동의어 보정 포함 — 예: áo thun ↔ áo phông)

■ 데이터 기준
  - 2026년 베트남 수출입 관세표 (BIEU THUE XNK 2026)
