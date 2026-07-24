"""애플리케이션 경로 및 설정 관리"""
import os, sys, json, uuid, secrets, re, threading, time
from pathlib import Path

# config.json 쓰기 직렬화용 락 (동시 save_config 가 서로의 임시파일을 덮어써
# config.json 이 깨지는 것을 방지). 같은 프로세스 내 스레드 보호용.
_CONFIG_WRITE_LOCK = threading.Lock()

APP_NAME = "도수치료예약"

# ─── 앱 버전 (배포 시 업데이트) ───
# 이 값은 프로그램 폴더에 포함되어 교체됨. %APPDATA%\도수치료예약\ 은 유지.
# 빌드 규칙: MAJOR.MINOR.PATCH (예: 1.2.3)
APP_VERSION = "1.3.56"
APP_BUILD_DATE = "2026-07-24"

# PyInstaller onedir/onefile 로 빌드된 실행본인지 여부.
#   True(배포 exe): 정적 자산을 ?v= 버전으로 무효화하므로 영구 캐시(immutable) 안전.
#   False(dev/run.py): 편집 즉시 반영되도록 캐시 끔(no-cache).
# 정적파일 Cache-Control 분기(main.py) 에서 사용.
IS_FROZEN = hasattr(sys, "_MEIPASS")

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
    # SyncOp(변경 기록) 보존 일수 — 지나면 자동 삭제 (무한 누적 방지).
    # ⚠ 이 기간보다 오래 꺼져 있던 sub 노드는 op 재생으로 따라잡을 수 없음
    #   → 신규/장기 오프라인 노드는 메인 PC 의 clinic.db 파일 복사로 부트스트랩.
    "sync_op_retention_days": 180,
    "slot_minutes": 30, "open_time": "08:30", "close_time": "18:30",
    # 야간당직 기준 퇴근시간 — 이 시각 이후 실제 퇴근분을 야간당직 시간으로 집계.
    # 운영 종료(close_time)와 별개로 관리 (관리자 설정에서 변경).
    "duty_baseline_end_time": "18:30",
    "lunch_enabled": False, "lunch_start": "12:30", "lunch_end": "13:30",
    # 헤더/브라우저 탭에 표시되는 앱(홈페이지) 이름 — 관리자 탭에서 수정.
    # base.html 이 Jinja 전역 app_title() 로 라이브 조회 (pages.py).
    "app_title": "병원 예약 관리",
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

def _salvage_secrets(p: Path) -> dict:
    """손상된 config.json 에서 보존할 핵심 값만 정규식으로 건져낸다.

    JSON 파싱이 깨져도 관리자 비밀번호 해시 등은 평문 패턴으로 추출 가능.
    기본값 재생성 시 이 값들을 덮어써 비번이 admin1234 로 초기화되는 사고를 막는다.
    """
    out: dict = {}
    try:
        raw = p.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return out
    for key in ("admin_password_hash", "node_id", "sync_secret",
                "update_manifest_url", "update_last_seen_version"):
        m = re.search(rf'"{key}"\s*:\s*"([^"\\]*)"', raw)
        if m and m.group(1):
            out[key] = m.group(1)
    if "admin_password_hash" in out:
        mb = re.search(r'"admin_password_changed"\s*:\s*(true|false)', raw)
        out["admin_password_changed"] = (mb.group(1) == "true") if mb else True
    return out


def load_config() -> dict:
    p = get_config_path()
    if not p.exists():
        cfg = dict(DEFAULT_CONFIG)
        cfg["node_id"] = uuid.uuid4().hex[:12]
        cfg["sync_secret"] = secrets.token_urlsafe(32)
        save_config(cfg); return cfg
    try:
        with open(p, "r", encoding="utf-8-sig") as f: cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("config.json 최상위가 객체가 아님")
    except Exception:
        # 손상된 config — 앱 시작 불가보다 기본값 재생성이 낫다.
        # 원본은 .broken_<ts> 로 보존하고, 비번 해시 등 핵심 비밀값은 건져서 보존
        #   (corrupted config → 기본값 재생성 시 비밀번호가 admin1234 로 초기화되어
        #    변경한 관리자 비밀번호가 거부되던 문제 방지).
        salvaged = _salvage_secrets(p)
        try:
            import time as _time
            p.rename(p.with_name(f"config.json.broken_{int(_time.time())}"))
        except Exception:
            pass
        cfg = dict(DEFAULT_CONFIG)
        cfg["node_id"] = uuid.uuid4().hex[:12]
        cfg["sync_secret"] = secrets.token_urlsafe(32)
        cfg.update(salvaged)
        if not cfg.get("node_id"):
            cfg["node_id"] = uuid.uuid4().hex[:12]
        if not cfg.get("sync_secret"):
            cfg["sync_secret"] = secrets.token_urlsafe(32)
        save_config(cfg); return cfg
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
    # 원자적 저장: 임시 파일에 전부 쓴 뒤 os.replace 로 교체.
    # 직접 쓰다 정전되면 config.json 이 깨져 앱이 시작 불가가 됨 (비번 해시·node_id 소실).
    #
    # ⚠ 동시성: 요청 처리 스레드풀 + sync/backup 백그라운드 스레드가 동시에
    #   save_config 를 호출할 수 있다. 과거엔 고정 tmp 이름("config.json.tmp")을
    #   공유해 동시 쓰기가 서로를 덮어쓰며 config.json 이 깨졌고, 다음 load_config()
    #   가 이를 손상으로 보고 기본값(비번 admin1234)으로 재생성 → 변경한 관리자
    #   비밀번호가 "틀렸다"고 거부되는 간헐적 문제가 있었음.
    #   → ① 프로세스/호출별 고유 tmp 이름  ② 쓰기 구간 Lock 으로 직렬화.
    p = get_config_path()
    tmp = p.with_name(f"{p.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    with _CONFIG_WRITE_LOCK:
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # Windows: 다른 스레드가 config.json 을 읽는 중(load_config open)이면
            #   os.replace 가 PermissionError(WinError 5)로 실패할 수 있다.
            #   읽기 핸들은 매우 짧으므로 잠깐 재시도하면 성공 — 실패 시 쓰기가
            #   유실되면 비번 변경 등이 조용히 사라지므로 재시도로 보장.
            last_err = None
            for _ in range(20):
                try:
                    os.replace(tmp, p)
                    last_err = None
                    break
                except PermissionError as e:
                    last_err = e
                    time.sleep(0.02)
            if last_err is not None:
                raise last_err
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass

def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"): return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent.parent / relative
