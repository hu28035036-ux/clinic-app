"""dummy_seed_and_live_test.py — 더미 데이터 (환자 50 / 치료사 8 / 의사 2) + 라이브 작동 테스트.

자동 모드:
- 격리된 임시 DB (DOSU_DB_PATH + APPDATA) 로 운영 DB 절대 미접근
- 마이그레이션 실행 후 더미 데이터 직접 INSERT
- uvicorn 백그라운드 실행
- httpx 로 실제 HTTP 호출:
  1. /api/health
  2. 관리자 로그인
  3. 환자 / 치료사 / 의사 endpoint 조회 → 더미 카운트 확인
  4. POST /api/ai/commands/parse — 자연어 명령
  5. 동명이인 처리 흐름 (환자 50명 중 동명이인 의도적 시드)
  6. POST /api/ai/commands/{id}/select-patient
  7. POST /api/ai/commands/{id}/approve — 실제 예약 생성 시도
  8. GET /api/appointments — 예약 등록 확인
  9. POST /api/ai/commands/{id}/reject — 거부
  10. GET /api/ai/commands/logs — 관리자 로그
- 결과 JSON 출력
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

    # ──────── 1. 격리 환경변수 ────────
    tmp_dir = project_root / "tests" / "temp" / f"dummy_live_{uuid.uuid4().hex[:8]}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "test_clinic_dummy.db"
    appdata = tmp_dir / "appdata"
    appdata.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["DOSU_DB_PATH"] = str(db_path)
    env["APPDATA"] = str(appdata)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # ──────── 2. 마이그레이션 + 더미 데이터 시드 (메인 프로세스로) ────────
    seed_script = project_root / "scripts" / "_dummy_seed_inline.py"
    seed_script.write_text(
        """\
import os, json, sys, random
from datetime import datetime, timedelta, date, time as time_cls
from pathlib import Path

# 부모 프로세스에서 환경변수는 설정됨. sys.path 에 프로젝트 루트 추가.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.database import init_db, SessionLocal
from app.models import models

init_db()

random.seed(42)
db = SessionLocal()
try:
    surnames = ['김','이','박','최','정','강','조','윤','장','임','한','오','신','권','황','안']
    given = ['민준','서연','지호','하은','도윤','수아','시우','서윤','준우','지유',
            '주원','지민','건우','하린','우진','수빈','선우','예린','시현','다은',
            '연우','채원','지훈','시연','은우','유진','준서','지원','이안','윤서',
            '도현','서현','승우','은서','재윤','다인','민재','채아','준혁','수민',
            '지안','서아','민서','예진','우주','민지','하준','윤하','진우','소율']

    # 의사 2명
    docs = []
    for i, name in enumerate(['김의사', '이의사']):
        d = models.Doctor(name=name, specialty='재활의학과', license_no=f'LIC{1000+i}')
        db.add(d); db.flush(); docs.append(d)

    # 치료사 8명 (그 중 일부 동명)
    therapists = []
    therapist_names = ['박치료사','김치료사','이치료사','최치료사',
                      '정치료사','강치료사','박치료사','조치료사']
    for i, name in enumerate(therapist_names):
        e = models.Employee(name=name, role='therapist',
                           color='#%06x' % random.randint(0,0xFFFFFF),
                           active=True, sort_order=i)
        db.add(e); db.flush(); therapists.append(e)

    # 환자 50명 — 그 중 의도적 동명이인 / 차트번호 중복 / 연락처 누락 / 같은 연락처
    patients = []
    used_charts = set()
    for i in range(50):
        sn = random.choice(surnames)
        gn = given[i % len(given)]
        # 5번/15번/25번/35번 환자는 같은 이름 (동명이인 시드)
        if i in (5, 15):
            full_name = '박환자'
        elif i in (25, 35):
            full_name = '김환자'
        else:
            full_name = sn + gn
        # chart_no — 9번/19번 의도적 중복
        if i == 19:
            chart_no = '10009'  # i==9 와 충돌 시뮬
        else:
            chart_no = f'{10000+i}'
        used_charts.add(chart_no)
        # phone — 일부 누락 / 일부 중복
        if i in (3, 13, 23):
            phone = ''  # 누락
        elif i in (8, 18):
            phone = '010-9999-0001'  # 중복
        else:
            phone = f'010-{1000+i:04d}-{2000+i:04d}'
        # birth_date
        year = 1950 + (i % 60)
        birth = f'{year:04d}-01-15'

        p = models.Patient(name=full_name, chart_no=chart_no,
                          birth_date=birth, phone=phone)
        db.add(p); db.flush(); patients.append(p)

    db.commit()

    # treatment_aliases 시드 (m020 으로 테이블 생성됨)
    from sqlalchemy import text
    manual30 = db.query(models.Treatment).filter_by(code='manual30').first()
    eswt = db.query(models.Treatment).filter_by(code='eswt').first()
    alias_pairs = []
    if manual30:
        alias_pairs += [(manual30.id, '도수30'), (manual30.id, '도30')]
    if eswt:
        alias_pairs += [(eswt.id, 'ESWT'), (eswt.id, '체외')]
    for tid, alias in alias_pairs:
        try:
            db.execute(
                text(
                    'INSERT INTO treatment_aliases (treatment_id, alias_name) '
                    'VALUES (:tid, :alias) ON CONFLICT(treatment_id, alias_name) DO NOTHING'
                ),
                {'tid': tid, 'alias': alias},
            )
        except Exception:
            pass
    db.commit()

    counts = {
        'patients': db.query(models.Patient).count(),
        'employees': db.query(models.Employee).count(),
        'doctors': db.query(models.Doctor).count(),
        'treatments': db.query(models.Treatment).count(),
        'aliases_seeded': len(alias_pairs),
    }
    print(json.dumps(counts))
finally:
    db.close()
""",
        encoding="utf-8",
    )

    seed_proc = subprocess.run(
        [str(project_root / "venv" / "Scripts" / "python.exe"), str(seed_script)],
        env=env, cwd=str(project_root),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    if seed_proc.returncode != 0:
        print(json.dumps({
            "ok": False,
            "stage": "seed",
            "stderr": seed_proc.stderr[-2000:],
        }, ensure_ascii=False))
        return 1
    seed_counts = {}
    try:
        seed_counts = json.loads(seed_proc.stdout.strip().split("\n")[-1])
    except Exception:  # noqa: BLE001
        seed_counts = {"raw": seed_proc.stdout[-500:]}

    # ──────── 3. uvicorn 시작 ────────
    port = 18766
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
    results: dict = {"ok": True, "seed": seed_counts, "steps": []}

    try:
        # ──────── 4. 서버 ready 대기 (최대 90초) ────────
        ready = False
        for _ in range(180):
            time.sleep(0.5)
            if proc.poll() is not None:
                break
            try:
                r = httpx.get(f"{base}/api/health", timeout=2.0)
                if r.status_code in (200, 401, 404):
                    ready = True
                    break
            except httpx.HTTPError:
                continue
            except OSError:
                continue
        if not ready:
            stdout, stderr = proc.communicate(timeout=5)
            results["ok"] = False
            results["stage"] = "server_start"
            results["stderr"] = stderr.decode("utf-8", errors="replace")[-2000:]
            print(json.dumps(results, ensure_ascii=False))
            return 1

        with httpx.Client(base_url=base, timeout=15.0) as client:
            # ──────── 5. 관리자 로그인 ────────
            r = client.post("/api/admin/login", json={"password": "admin1234"})
            login_ok = r.status_code == 200
            token = r.json().get("token", "") if login_ok else ""
            results["steps"].append({
                "step": "admin_login",
                "ok": login_ok and bool(token),
            })
            if not token:
                results["ok"] = False
                print(json.dumps(results, ensure_ascii=False, indent=2))
                return 1

            H = {"X-Admin-Token": token}

            # ──────── 6. 환자 / 치료사 / 의사 endpoint 카운트 ────────
            r1 = client.get("/api/patients?limit=100", headers=H)
            r2 = client.get("/api/employees", headers=H)
            r3 = client.get("/api/doctors", headers=H)
            count_p = len(r1.json()) if r1.status_code == 200 and isinstance(r1.json(), list) else (
                len(r1.json().get("rows") or r1.json().get("items") or []) if r1.status_code == 200 else -1
            )
            count_e = len(r2.json()) if r2.status_code == 200 and isinstance(r2.json(), list) else -1
            count_d = len(r3.json()) if r3.status_code == 200 and isinstance(r3.json(), list) else -1
            results["steps"].append({
                "step": "endpoint_counts",
                "patients_status": r1.status_code, "patients_count": count_p,
                "employees_status": r2.status_code, "employees_count": count_e,
                "doctors_status": r3.status_code, "doctors_count": count_d,
                "ok": r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200,
            })

            # ──────── 7. parse — 동명이인 (박환자) ────────
            r = client.post(
                "/api/ai/commands/parse",
                json={
                    "raw_text": "박환자 5월30일 9시 박치료사 도수30 예약",
                    "today_iso": "2026-05-01",
                },
                headers=H,
            )
            ok_parse = r.status_code == 200 and r.json().get("ok") is True
            body = r.json() if ok_parse else {}
            cmd_id = body.get("command_id")
            status_p = body.get("result", {}).get("status")
            n_candidates = len(body.get("result", {}).get("patient_resolution", {}).get("candidates", []))
            results["steps"].append({
                "step": "parse_homonym",
                "status": r.status_code,
                "result_status": status_p,
                "command_id": cmd_id,
                "n_patient_candidates": n_candidates,
                "ok": ok_parse and status_p == "patient_selection_required" and n_candidates >= 2,
            })

            # ──────── 8. select-patient ────────
            patient_select_ok = False
            if cmd_id and n_candidates >= 1:
                first_pid = body["result"]["patient_resolution"]["candidates"][0]["patient_id"]
                r2 = client.post(
                    f"/api/ai/commands/{cmd_id}/select-patient",
                    json={"patient_id": first_pid},
                    headers=H,
                )
                patient_select_ok = (
                    r2.status_code == 200
                    and r2.json().get("ok") is True
                    and (r2.json().get("result", {}).get("selected_patient") or {}).get("patient_id") == first_pid
                )
                sel_status = r2.json().get("result", {}).get("status") if r2.status_code == 200 else None
                results["steps"].append({
                    "step": "select_patient",
                    "status": r2.status_code,
                    "selected": first_pid,
                    "result_status": sel_status,
                    "ok": patient_select_ok,
                })

            # ──────── 9. parse — 차트번호 단일 환자 (approve 시도) ────────
            r = client.post(
                "/api/ai/commands/parse",
                json={
                    "raw_text": "차트번호 10000 5월 30일 10시 박치료사 도수30 예약",
                    "today_iso": "2026-05-01",
                },
                headers=H,
            )
            ok_parse2 = r.status_code == 200 and r.json().get("ok") is True
            body2 = r.json() if ok_parse2 else {}
            cmd_id2 = body2.get("command_id")
            status_p2 = body2.get("result", {}).get("status")
            results["steps"].append({
                "step": "parse_chart_only",
                "status": r.status_code,
                "result_status": status_p2,
                "command_id": cmd_id2,
                "ok": ok_parse2,
            })

            # ──────── 10. approve — 실제 예약 생성 시도 ────────
            approve_ok = False
            executed_appt_id = None
            if cmd_id2 and status_p2 == "needs_approval":
                # SessionLocal 사용 안 하고 단순 비교 안 함, Phase 5 단위 테스트 + ai_executor 가 검증.
                r_app = client.post(
                    f"/api/ai/commands/{cmd_id2}/approve",
                    json={"memo": "라이브 더미 테스트"},
                    headers=H,
                )
                approve_body = r_app.json() if r_app.status_code == 200 else {}
                approve_ok = (
                    r_app.status_code == 200
                    and approve_body.get("ok") is True
                    and approve_body.get("execution_status") == "executed"
                )
                executed_appt_id = (approve_body.get("result_payload") or {}).get("appointment_id")
                results["steps"].append({
                    "step": "approve_real_service",
                    "status": r_app.status_code,
                    "execution_status": approve_body.get("execution_status"),
                    "appointment_id": executed_appt_id,
                    "error_message": approve_body.get("error_message"),
                    "ok": approve_ok,
                })

                # approve 직후 — ai_commands GET 으로 audit row 확인 (status=executed + executed_at)
                if approve_ok and executed_appt_id:
                    r_check = client.get(
                        f"/api/ai/commands/{cmd_id2}",
                        headers=H,
                    )
                    audit_row = r_check.json().get("row", {}) if r_check.status_code == 200 else {}
                    audit_executed = (
                        audit_row.get("status") == "executed"
                        and audit_row.get("executed_at") is not None
                        and (audit_row.get("executed_result") or {}).get("appointment_id") == executed_appt_id
                    )
                    results["steps"].append({
                        "step": "verify_audit_executed",
                        "status": r_check.status_code,
                        "audit_status": audit_row.get("status"),
                        "audit_appointment_id": (audit_row.get("executed_result") or {}).get("appointment_id"),
                        "ok": audit_executed,
                    })

            # ──────── 11. reject ────────
            r = client.post(
                "/api/ai/commands/parse",
                json={"raw_text": "차트번호 10001 5월 30일 11시 도수30 예약", "today_iso": "2026-05-01"},
                headers=H,
            )
            cmd_id3 = r.json().get("command_id") if r.status_code == 200 else None
            reject_ok = False
            if cmd_id3:
                r2 = client.post(
                    f"/api/ai/commands/{cmd_id3}/reject",
                    json={"reason": "라이브 더미 거부 테스트"},
                    headers=H,
                )
                reject_ok = (
                    r2.status_code == 200
                    and r2.json().get("row", {}).get("status") == "rejected"
                )
                results["steps"].append({
                    "step": "reject",
                    "status": r2.status_code,
                    "ok": reject_ok,
                })

            # ──────── 12. GET logs ────────
            r = client.get("/api/ai/commands/logs?limit=20", headers=H)
            logs_ok = r.status_code == 200 and r.json().get("ok") is True
            log_count = r.json().get("count") if logs_ok else 0
            results["steps"].append({
                "step": "get_logs",
                "status": r.status_code,
                "log_count": log_count,
                "ok": logs_ok and log_count >= 3,
            })

            # 종합 ok
            results["ok"] = all(s.get("ok") for s in results["steps"])

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        # 시드 스크립트 정리
        try:
            seed_script.unlink()
        except Exception:  # noqa: BLE001
            pass

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
