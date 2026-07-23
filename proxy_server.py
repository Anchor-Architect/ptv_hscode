#!/usr/bin/env python3
"""
anchor · HS Code Finder — 로컬 서버 (정적 파일 + Anthropic 프록시)

기존 `python3 -m http.server` 를 대체합니다.
  - 정적 파일(index_v2.html, hs_data.json 등)을 그대로 서빙하고
  - /api/messages 요청을 받아 서버 쪽에서 Anthropic API로 대신 전달합니다.

핵심: API 키는 코드가 아니라 '환경변수'로 넣습니다. 브라우저에는 절대 노출되지 않습니다.

실행 방법
  1) 이 폴더에서 터미널 열기
  2) export ANTHROPIC_API_KEY="여기에-발급받은-키"      (Windows: set ANTHROPIC_API_KEY=...)
  3) python3 proxy_server.py
  4) 브라우저에서 http://localhost:8000/index_v2.html 열기
"""

import json
import os
import sys
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def load_dotenv(path=".env"):
    """의존성 없이 .env 파일을 읽어 환경변수로 올립니다.
    이미 설정된 환경변수(예: 배포 대시보드에서 주입한 값)는 덮어쓰지 않습니다.
    python-dotenv 를 설치했다면 그걸 써도 되지만, 여기선 표준 라이브러리만 사용합니다."""
    here = os.path.dirname(os.path.abspath(__file__))
    full = os.path.join(here, path)
    if not os.path.exists(full):
        return
    with open(full, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")  # 양쪽 따옴표 제거
            os.environ.setdefault(key, val)  # 기존 환경변수 우선


load_dotenv()

PORT = int(os.environ.get("PORT", "8000"))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class Handler(SimpleHTTPRequestHandler):
    # 정적 파일은 이 스크립트가 있는 폴더에서 서빙
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/messages":
            self.send_error(404, "Not found")
            return

        if not API_KEY:
            self._send_json(500, {
                "error": "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
                         "터미널에서 export ANTHROPIC_API_KEY=... 후 서버를 다시 실행하세요."
            })
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            client_body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "잘못된 요청 본문(JSON 파싱 실패)"})
            return

        # 브라우저가 보낸 messages/model/max_tokens 를 그대로 Anthropic 으로 전달.
        # 키와 버전 헤더는 이 서버(=신뢰 영역)에서만 붙입니다.
        upstream_req = urllib.request.Request(
            ANTHROPIC_URL,
            data=json.dumps(client_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(upstream_req, timeout=60) as resp:
                self._send_json(resp.status, json.loads(resp.read()))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail)
            except json.JSONDecodeError:
                pass
            self._send_json(e.code, {"error": "Anthropic API 오류", "detail": detail})
        except Exception as e:  # 네트워크/타임아웃 등
            self._send_json(502, {"error": "업스트림 연결 실패", "detail": str(e)})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    if not API_KEY:
        print("⚠  ANTHROPIC_API_KEY 가 설정되지 않았습니다.", file=sys.stderr)
        print("   AI 판단 모드를 쓰려면:  export ANTHROPIC_API_KEY=\"발급받은-키\"", file=sys.stderr)
        print("   (키 없이도 서버는 뜨지만, 앱은 데모(키워드 근사) 모드로 동작합니다)\n", file=sys.stderr)
    else:
        print("✓ API 키 감지됨 (…%s). AI 판단 모드 사용 가능.\n" % API_KEY[-4:], file=sys.stderr)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"→ http://localhost:{PORT}/index_v2.html  (Ctrl+C 로 종료)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.", file=sys.stderr)
        server.shutdown()


if __name__ == "__main__":
    main()
