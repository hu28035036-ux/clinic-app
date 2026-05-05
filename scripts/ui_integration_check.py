"""ui_integration_check.py — AI 도우미 UI 통합 라이브 검증.

자동 모드:
- 격리 DB + uvicorn 백그라운드
- GET / → main.html 응답 → AI 도우미 partial 마크업 포함 확인
- GET /static/css/_ai_helper.css → 200 + CSS 내용 (디자인 토큰 변수 검증)
- GET /static/js/ai_helper.js → 200 + JS 내용 (aiHelper 함수 정의 확인)
- 응답 시 X-Admin-Token 없이도 / 페이지 접근은 정상 (admin 인증은 endpoint 만)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent

    tmp_dir = project_root / "tests" / "temp" / f"ui_check_{uuid.uuid4().hex[:8]}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["DOSU_DB_PATH"] = str(tmp_dir / "test_clinic_ui.db")
    env["APPDATA"] = str(tmp_dir / "appdata")
    Path(env["APPDATA"]).mkdir(parents=True, exist_ok=True)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    port = 18767
    proc = subprocess.Popen(
        [
            str(project_root / "venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
            "--log-level", "warning",
        ],
        env=env, cwd=str(project_root),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    base = f"http://127.0.0.1:{port}"
    results: dict = {"ok": True, "steps": []}

    try:
        ready = False
        for _ in range(60):
            time.sleep(0.5)
            if proc.poll() is not None:
                break
            try:
                r = httpx.get(f"{base}/api/health", timeout=2.0)
                if r.status_code in (200, 401, 404):
                    ready = True
                    break
            except (httpx.ConnectError, httpx.ReadTimeout):
                continue
        if not ready:
            stdout, stderr = proc.communicate(timeout=5)
            results["ok"] = False
            results["stderr"] = stderr.decode("utf-8", errors="replace")[-2000:]
            print(json.dumps(results, ensure_ascii=False))
            return 1

        with httpx.Client(base_url=base, timeout=15.0, follow_redirects=True) as client:
            # ── 1. GET / → main.html
            r = client.get("/")
            html = r.text if r.status_code == 200 else ""
            checks = {
                "ai-helper-card class": "ai-helper-card" in html,
                "AI 예약 도우미 title": "AI 예약 도우미" in html,
                "x-data aiHelper": 'x-data="aiHelper"' in html,   # Codex 지적 fix: 실제 partial 마커
                "_ai_helper.css link": "_ai_helper.css" in html,
                "ai_helper.js script": "ai_helper.js" in html,
                "tab-reserve section": 'id="tab-reserve"' in html,
                "기존 캘린더 #day-board": '"day-board"' in html or "day-board" in html,
                "기존 환자 검색": "patient-quick-search" in html,
            }
            results["steps"].append({
                "step": "main_html",
                "status": r.status_code,
                "checks": checks,
                "ok": r.status_code == 200 and all(checks.values()),
            })
            if not all(checks.values()):
                results["ok"] = False

            # ── 2. CSS 파일
            r2 = client.get("/static/css/_ai_helper.css")
            css = r2.text if r2.status_code == 200 else ""
            css_checks = {
                "--ai-helper-primary": "--ai-helper-primary" in css,
                "ai-helper-card class": ".ai-helper-card" in css,
                "ai-helper-btn--primary": ".ai-helper-btn--primary" in css,
                "디자인 토큰 색": "#1F3D2B" in css,  # primary green
            }
            results["steps"].append({
                "step": "ai_helper_css",
                "status": r2.status_code,
                "checks": css_checks,
                "ok": r2.status_code == 200 and all(css_checks.values()),
            })
            if not (r2.status_code == 200 and all(css_checks.values())):
                results["ok"] = False

            # ── 3. JS 파일
            r3 = client.get("/static/js/ai_helper.js")
            js = r3.text if r3.status_code == 200 else ""
            js_checks = {
                "aiHelper function": "window.aiHelper" in js,
                "onParse": "onParse" in js,
                "onSelectPatient": "onSelectPatient" in js,
                "onApprove": "onApprove" in js,
                "/api/ai/commands/parse": "/api/ai/commands/parse" in js,
                "X-Admin-Token": "X-Admin-Token" in js,
                "dosu_admin_token": "dosu_admin_token" in js,
            }
            results["steps"].append({
                "step": "ai_helper_js",
                "status": r3.status_code,
                "checks": js_checks,
                "ok": r3.status_code == 200 and all(js_checks.values()),
            })
            if not (r3.status_code == 200 and all(js_checks.values())):
                results["ok"] = False

            # ── 4. 기존 화면 회귀 — main 페이지 의 기존 탭 / 기능 모두 보존
            existing_checks = {
                "예약 탭 버튼": "switchTab('tab-reserve'" in html,
                "환자 탭": "tab-patients" in html,
                "직원 탭": "tab-therapists" in html,
                "예약 문자 탭": "tab-sms" in html,
                # v1.3.5+ : AI 도우미 탭 (tab-ai-manual) UI 제거 — 백엔드 보존
                "AI 도우미 탭 제거 (UI)": "switchTab('tab-ai-manual'" not in html,
                "관리자 탭": "tab-admin" in html or "admin-tab-btn" in html,
            }
            results["steps"].append({
                "step": "existing_ui_regression",
                "checks": existing_checks,
                "ok": all(existing_checks.values()),
            })
            if not all(existing_checks.values()):
                results["ok"] = False

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
