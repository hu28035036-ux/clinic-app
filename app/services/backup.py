"""자동 백업 서비스 (단계 G #18).

기능:
- 시작 시 1회 자동 백업 (오늘 백업이 없으면)
- 내부 타이머: 설정된 주기마다 자동 백업 (최소 5분)
- 보관 개수 초과 시 가장 오래된 파일 자동 삭제
- 수동 "지금 백업" 버튼
- "최근 백업으로 복원" — 가장 최근 파일을 현재 DB로 덮어쓰기
"""
import shutil, threading, time
from datetime import datetime
from pathlib import Path

from ..config import get_db_path, get_backup_dir
from ..database import SessionLocal
from ..models.models import SystemSetting

BACKUP_PREFIX = "clinic_"
BACKUP_SUFFIX = ".db"

_timer_thread = None
_stop_flag = threading.Event()


def list_backups() -> list:
    """백업 파일 목록 (최신순)."""
    d = get_backup_dir()
    files = sorted(d.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"), reverse=True)
    return [
        {
            "name": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        }
        for f in files
    ]


def make_backup() -> dict:
    """현재 DB 파일을 백업 폴더에 타임스탬프 이름으로 복사."""
    db_path = Path(get_db_path())
    if not db_path.exists():
        return {"ok": False, "error": "DB 파일이 없습니다."}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = get_backup_dir() / f"{BACKUP_PREFIX}{ts}{BACKUP_SUFFIX}"
    try:
        shutil.copy2(db_path, dest)
        _enforce_keep_limit()
        return {"ok": True, "name": dest.name, "size": dest.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def restore_by_name(filename: str) -> dict:
    """지정한 백업 파일명으로 복원.

    안전망: 복원 전 현재 DB를 before_restore 파일로 자동 저장.
    """
    backups = list_backups()
    target = next((b for b in backups if b["name"] == filename), None)
    if not target:
        return {"ok": False, "error": f"백업 파일을 찾을 수 없습니다: {filename}"}
    target_path = Path(target["path"])
    db_path = Path(get_db_path())

    # 안전망: 현재 상태 백업 1회
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = get_backup_dir() / f"{BACKUP_PREFIX}before_restore_{ts}{BACKUP_SUFFIX}"
        if db_path.exists():
            shutil.copy2(db_path, safe)
    except Exception:
        pass

    # 복원
    try:
        from ..database import engine
        engine.dispose()
        shutil.copy2(target_path, db_path)
        return {"ok": True, "restored_from": target_path.name,
                "msg": f"{target_path.name} 으로 복원됨. 서버를 재시작하세요."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _enforce_keep_limit():
    """SystemSetting.auto_backup_keep_count 초과 시 오래된 것 삭제."""
    try:
        db = SessionLocal()
        ss = db.query(SystemSetting).first()
        keep = (ss.auto_backup_keep_count or 30) if ss else 30
        db.close()
    except Exception:
        keep = 30
    files = sorted(get_backup_dir().glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    extra = len(files) - keep
    if extra > 0:
        for f in files[:extra]:
            try: f.unlink()
            except Exception: pass


def restore_latest() -> dict:
    """가장 최근 백업을 현재 DB 위에 덮어씀.

    위험: 호출 즉시 현재 DB가 백업본으로 교체됨. 호출 직전 안전망 백업 1회 자동 실행.
    """
    backups = list_backups()
    if not backups:
        return {"ok": False, "error": "백업 파일이 없습니다."}
    latest = Path(backups[0]["path"])
    db_path = Path(get_db_path())

    # 안전망: 현재 상태 백업 1회 (복원 후 되돌리기 가능)
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = get_backup_dir() / f"{BACKUP_PREFIX}before_restore_{ts}{BACKUP_SUFFIX}"
        if db_path.exists():
            shutil.copy2(db_path, safe)
    except Exception:
        pass

    # 복원
    try:
        # 엔진 종료 후 파일 교체
        from ..database import engine
        engine.dispose()
        shutil.copy2(latest, db_path)
        return {"ok": True, "restored_from": latest.name,
                "msg": f"{latest.name} 으로 복원됨. 서버를 재시작하세요."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def auto_backup_once_at_startup():
    """시작 시 오늘 백업이 없으면 1회 자동 (Q4 (가): 조용히)."""
    today_str = datetime.now().strftime("%Y%m%d")
    files = list(get_backup_dir().glob(f"{BACKUP_PREFIX}{today_str}_*{BACKUP_SUFFIX}"))
    if files:
        return  # 오늘 이미 백업 있음
    make_backup()


def _timer_loop():
    """타이머 루프 — DB 설정 주기마다 백업."""
    while not _stop_flag.is_set():
        try:
            db = SessionLocal()
            ss = db.query(SystemSetting).first()
            enabled = bool(ss.auto_backup_enabled) if ss else True
            interval = max(5, (ss.auto_backup_interval_min or 60)) if ss else 60
            db.close()
        except Exception:
            enabled, interval = False, 60

        # 주기만큼 대기 (1분 단위로 깨어나서 stop 플래그 확인)
        sleep_total = interval * 60
        slept = 0
        while slept < sleep_total and not _stop_flag.is_set():
            time.sleep(min(60, sleep_total - slept))
            slept += 60

        if _stop_flag.is_set(): break
        if enabled:
            try: make_backup()
            except Exception: pass


def start_auto_backup():
    """앱 부팅 후 호출 — 시작 백업 1회 + 타이머 시작."""
    global _timer_thread
    auto_backup_once_at_startup()
    if _timer_thread and _timer_thread.is_alive():
        return
    _stop_flag.clear()
    _timer_thread = threading.Thread(target=_timer_loop, daemon=True, name="auto-backup")
    _timer_thread.start()


def stop_auto_backup():
    _stop_flag.set()
