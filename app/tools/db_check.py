"""DB 무결성 + 통계 점검 — run.py --check 로 실행.

console=False 인 GUI 빌드에서는 print 출력이 보이지 않으므로,
결과를 텍스트 파일로 저장하고 메모장으로 자동 오픈.
"""
import sqlite3
import sys
import io
import os
import subprocess
from pathlib import Path


def run_check():
    """DB 점검 실행.
    ⚠ 결과 파일(txt) 은 **어떤 경우에도** 생성되도록 try/finally 로 보장.
       DB 미존재 등 조기 return 시에도 안내 메시지가 담긴 파일이 생성됨.
    """
    from ..config import get_db_path, APP_VERSION, APP_BUILD_DATE
    db = Path(get_db_path())

    # 출력을 buffer 에 쌓음 (stdout 이 None 일 수 있음)
    buf = io.StringIO()
    def P(s=""): buf.write(s + "\n")

    try:
        _body(buf, P, db, APP_VERSION, APP_BUILD_DATE)
    finally:
        # ── 반드시 파일로 결과 저장 (조기 return 이어도 여기는 실행됨) ──
        _write_result(buf.getvalue())


def _body(buf, P, db, APP_VERSION, APP_BUILD_DATE):
    """실제 점검 로직. 여기서 return 되더라도 finally 에서 파일은 쓰임."""
    P("")
    P("━" * 64)
    P(f"  도수치료예약 v{APP_VERSION}  ·  DB 점검")
    P(f"  빌드일: {APP_BUILD_DATE}")
    P("━" * 64)
    P(f"  DB 위치 : {db}")

    if not db.exists():
        P("  ❌ DB 파일이 없습니다. 프로그램을 한 번 실행하면 자동 생성됩니다.")
        P("━" * 64)
        return

    size_mb = db.stat().st_size / 1024 / 1024
    P(f"  DB 크기 : {size_mb:.2f} MB")
    P("")

    c = sqlite3.connect(str(db))
    try:
        # ── 적용된 마이그레이션 ──
        try:
            rows = c.execute(
                "SELECT id, description, applied_at "
                "FROM schema_migrations ORDER BY id"
            ).fetchall()
            if rows:
                P("  [ 적용된 마이그레이션 ]")
                for mid, desc, at in rows:
                    P(f"    ✓ {mid:03d}  {desc}  ({at})")
            else:
                P("  [ 마이그레이션 ] 적용 기록 없음 (최초 실행 전)")
        except sqlite3.OperationalError:
            P("  [ 마이그레이션 ] schema_migrations 테이블 없음")
            P("     → v1.2.2 이하 버전이거나 프로그램을 아직 한 번도 실행 안 함")
        P("")

        # ── 테이블별 건수 ──
        P("  [ 테이블별 레코드 수 ]")
        tables = [
            ("patients", "환자"),
            ("appointments", "예약"),
            ("treatment_assignments", "예약-치료 배정"),
            ("employees", "직원(의사/치료사)"),
            ("treatments", "치료항목"),
            ("patient_treatment_counts", "환자별 카운트"),
            ("sms_logs", "문자 발송 로그"),
            ("sms_templates", "문자 템플릿"),
            ("sms_settings", "문자 연동 설정"),
            ("audit_logs", "감사 로그"),
        ]
        for t, label in tables:
            try:
                n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                status = "  " if n == 0 else "● "
                P(f"    {status}{t:30s} {n:>8,}건  ({label})")
            except Exception as e:
                P(f"    ? {t:30s} (조회 실패: {e})")
        P("")

        # ── 환자 상태 상세 ──
        try:
            total = c.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
            reserved = c.execute(
                "SELECT COUNT(*) FROM appointments WHERE status='reserved'"
            ).fetchone()[0]
            approved = c.execute(
                "SELECT COUNT(*) FROM appointments WHERE status='approved'"
            ).fetchone()[0]
            canceled = c.execute(
                "SELECT COUNT(*) FROM appointments WHERE status='canceled'"
            ).fetchone()[0]
            P("  [ 예약 상태 분포 ]")
            P(f"    총 {total:,}  ·  예약됨 {reserved:,}  ·  완료 {approved:,}  ·  취소 {canceled:,}")
        except Exception:
            pass
        P("")

        # ── 무결성 검사 ──
        P("  [ DB 무결성 검사 ]")
        integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
        P(f"    {'✓' if integrity == 'ok' else '❌'} {integrity}")
        P("")

        # ── 최근 백업 ──
        from ..config import get_backup_dir
        backup_dir = Path(get_backup_dir())
        bks = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        P("  [ 최근 자동 백업 ]")
        if not bks:
            P("    (백업 없음 — 관리자 → 시스템 → 자동 백업 설정 권장)")
        else:
            for p in bks[:5]:
                from datetime import datetime
                mt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                sz = p.stat().st_size / 1024 / 1024
                P(f"    · {p.name:40s} {sz:>6.2f} MB  {mt}")
            if len(bks) > 5:
                P(f"    ... 외 {len(bks)-5}개 더 있음")
        P("")
    finally:
        c.close()

    P("━" * 64)
    P("  점검 완료. 창을 닫으셔도 됩니다.")
    P("━" * 64)


def _write_result(text: str):
    """결과를 파일로 저장.
    - 환경변수 DOSU_CHECK_OUT 가 있으면 그 경로로
    - 없으면 %TEMP%\\도수치료예약_DB점검_{timestamp}.txt 로
    실패해도 조용히 통과 (.bat 이 fail 경로로 안내).
    """
    import tempfile
    out_path = os.environ.get("DOSU_CHECK_OUT")
    if not out_path:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(tempfile.gettempdir(), f"도수치료예약_DB점검_{ts}.txt")
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        # 실패해도 예외를 삼키지 않으면 run.py 에서 잡아 로그에 남김
        raise
