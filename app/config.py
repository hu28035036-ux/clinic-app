"""애플리케이션 경로 및 설정 관리"""
import os, sys, json, uuid, secrets
from pathlib import Path

APP_NAME = "도수치료예약"

# ─── 앱 버전 (배포 시 업데이트) ───
# 이 값은 프로그램 폴더에 포함되어 교체됨. %APPDATA%\도수치료예약\ 은 유지.
# 빌드 규칙: MAJOR.MINOR.PATCH (예: 1.2.3)
APP_VERSION = "1.3.15"
APP_BUILD_DATE = "2026-06-08"

def get_appdata_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        path = base / APP_NAME
    else:
        path = Path.home() / f".{APP_NAME}"
    path.mkdir(parents=True, exist_ok=True); return path

def get_db_path() -> Path:
    # 테스트/하네스 override — DOSU_DB_PATH 환경변수가 있으면 그 경로 사용.
    # 운영 환경은 환경변수 없이 그대로 %APPDATA%\도수치료예약\clinic.db.
    p = os.environ.get("DOSU_DB_PATH")
    if p:
        return Path(p)
    return get_appdata_dir() / "clinic.db"
def get_config_path() -> Path: return get_appdata_dir() / "config.json"
def get_backup_dir() -> Path:
    p = get_appdata_dir() / "backups"; p.mkdir(parents=True, exist_ok=True); return p

# mode: None(첫실행) | "main" | "sub"  - 모든 노드는 로컬 DB 보유
# main_url: sub 일 때 sync 대상
DEFAULT_CONFIG = {
    "mode": None, "node_id": None, "main_url": None, "peers": [],
    "sync_interval_sec": 15,
    "slot_minutes": 30, "open_time": "08:30", "close_time": "18:30",
    "lunch_enabled": False, "lunch_start": "12:30", "lunch_end": "13:30",
    "host": "0.0.0.0", "port": 8000,
    # ─── 업데이트 관련 (자동업데이트 확장용 훅) ───
    # update_manifest_url: 빈 문자열이면 "업데이트 확인" 은 수동 안내만 표시.
    #   운영 시 배포처 서버/GitHub Releases 에
    #     {"version":"1.2.3","download_url":"...","notes":"..."}
    #   형식의 JSON 을 올리고 이 URL 을 설정하면 자동 체크 활성화.
    "update_manifest_url": "",
    # 마지막으로 사용자에게 보여준 원격 버전 (안내 배너 중복 방지용)
    "update_last_seen_version": "",
    # ─── peer 노드 간 sync 인증 토큰 ───
    # /api/sync/pull, /api/sync/push 는 외부 노드가 호출하므로 관리자 세션 토큰만으론
    # 인증 못함 → X-Sync-Token 헤더 비교용 공유 비밀.
    # 비어있으면 load_config() 가 노드별 안전한 랜덤값을 자동 생성/저장.
    # 다른 노드와 페어링하려면 양쪽 config.json 의 sync_secret 값을 동일하게 맞춰야 함.
    "sync_secret": "",
}

def load_config() -> dict:
    p = get_config_path()
    if not p.exists():
        cfg = dict(DEFAULT_CONFIG)
        cfg["node_id"] = uuid.uuid4().hex[:12]
        cfg["sync_secret"] = secrets.token_urlsafe(32)
        save_config(cfg); return cfg
    with open(p, "r", encoding="utf-8-sig") as f: cfg = json.load(f)
    for k, v in DEFAULT_CONFIG.items(): cfg.setdefault(k, v)
    # node_id / sync_secret 자동 채움 — 둘 중 하나라도 비어있으면 생성 후 저장.
    dirty = False
    if not cfg.get("node_id"):
        cfg["node_id"] = uuid.uuid4().hex[:12]; dirty = True
    if not cfg.get("sync_secret"):
        cfg["sync_secret"] = secrets.token_urlsafe(32); dirty = True
    if dirty:
        save_config(cfg)
    return cfg

def save_config(cfg: dict) -> None:
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"): return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent.parent / relative
