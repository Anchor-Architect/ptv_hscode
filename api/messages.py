"""
Vercel 서버리스 함수 — /api/messages

프론트엔드(index_v2.html)가 보낸 요청을 서버 쪽에서 Anthropic API로 대신 전달합니다.
API 키는 코드가 아니라 Vercel 프로젝트의 'Environment Variables' 에서 주입됩니다.
(로컬 개발은 proxy_server.py 를 계속 쓰면 됩니다. 이 파일은 배포 전용.)

표준 라이브러리만 사용 → requirements.txt 불필요.
"""

import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            self._send_json(500, {
                "error": "ANTHROPIC_API_KEY 가 설정되지 않았습니다. "
                         "Vercel 프로젝트 Settings → Environment Variables 에 등록하세요."
            })
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            client_body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "잘못된 요청 본문(JSON 파싱 실패)"})
            return

        upstream_req = urllib.request.Request(
            ANTHROPIC_URL,
            data=json.dumps(client_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(upstream_req, timeout=30) as resp:
                self._send_json(resp.status, json.loads(resp.read()))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail)
            except json.JSONDecodeError:
                pass
            self._send_json(e.code, {"error": "Anthropic API 오류", "detail": detail})
        except Exception as e:
            self._send_json(502, {"error": "업스트림 연결 실패", "detail": str(e)})
