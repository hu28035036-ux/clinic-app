"""진입점 - 메인 PC 자동 설정 + 개발 모드 자동 더미 시드.

- 빌드본 (PyInstaller frozen) : 운영 DB (`%APPDATA%\\도수치료예약\\clinic.db`) 사용 — 기존 동작 그대로.
- 소스에서 직접 실행 (개발 PC) : 자동 개발 모드
    * 격리 DB:      tests/temp/dev_clinic.db
    * 격리 APPDATA: tests/temp/dev_appdata/
    * 더미 자동 시드 (환자 50 / 치료사 8 / 의사 2 / 치료항목 alias) — 1회 멱등
    * 운영 DB 절대 미접근

운영 DB 로 띄우고 싶을 때 (개발 PC 에서도): `python run.py --prod`
"""
import os, sys, time, threading, webbrowser, socket, ctypes

# ⚠ --check 모드: 무거운 import (uvicorn 등) 전에 처리
#   console=False 빌드에서도 결과가 파일로 저장돼 bat 이 띄움
#   실패 시 원인 추적을 위해 log.txt 에 오류 기록
if "--check" in sys.argv:
    import tempfile, traceback
    _log_path = os.path.join(tempfile.gettempdir(), "도수치료예약_DB점검_log.txt")
    try:
        from app.tools.db_check import run_check
        run_check()
    except Exception as e:
        try:
            with open(_log_path, "w", encoding="utf-8") as f:
                f.write(f"[X] --check 실행 실패\n{e}\n{traceback.format_exc()}\n")
        except Exception:
            pass
    sys.exit(0)

# ──────── 개발 모드 자동 감지 (app import 전 환경변수 설정) ────────
# 빌드본은 sys.frozen=True → 운영 DB 강제. 소스 실행만 격리 DB.
_IS_FROZEN = getattr(sys, "frozen", False)
_FORCE_PROD = "--prod" in sys.argv
_DEV_MODE = (not _IS_FROZEN) and (not _FORCE_PROD)

if _DEV_MODE:
    from pathlib import Path as _Path
    _root = _Path(__file__).resolve().parent
    _temp = _root / "tests" / "temp"
    _temp.mkdir(parents=True, exist_ok=True)
    _dev_db = _temp / "dev_clinic.db"
    _dev_appdata = _temp / "dev_appdata"
    _dev_appdata.mkdir(parents=True, exist_ok=True)
    os.environ["DOSU_DB_PATH"] = str(_dev_db)
    os.environ["APPDATA"] = str(_dev_appdata)

import uvicorn
from pathlib import Path
from app.config import load_config, save_config

# PyInstaller console=False(GUI) 모드에서는 sys.stdout/stderr 가 None
# → print() / isatty() 호출 시 AttributeError 방지
# errors='ignore' : CP949 환경에서 이모지 등 인코딩 불가 문자 무시
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8', errors='ignore')


def _open(url, delay=1.0):
    def go():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=go, daemon=True).start()


def _is_already_running(port=8000):
    """포트가 이미 열려있으면 다른 인스턴스가 실행 중"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result == 0
    except Exception:
        return False


def _get_local_ip():
    """이 PC의 LAN IP 알아내기 (다른 PC 접속용)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _create_desktop_shortcut(url):
    """바탕화면에 '병원 예약 관리.url' 자동 생성"""
    if sys.platform != "win32":
        return
    try:
        desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        if not desktop.exists():
            return
        shortcut = desktop / "병원 예약 관리.url"
        if shortcut.exists():
            return  # 이미 있으면 건들지 않음
        shortcut.write_text(
            f"[InternetShortcut]\nURL={url}\nIconIndex=0\n",
            encoding="utf-8"
        )
    except Exception:
        pass


def _minimize_console():
    """Windows에서 cmd 창 최소화 (기능에는 영향 없음)"""
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    except Exception:
        pass


def _ensure_main_mode():
    """첫 실행 시 자동으로 메인 모드로 설정"""
    cfg = load_config()
    if not cfg.get("mode"):
        # 첫 실행 → 메인 모드 자동 적용
        cfg["mode"] = "main"
        save_config(cfg)
        print("\n" + "="*60)
        print("[OK] 메인 서버 모드로 자동 설정되었습니다.")
        print("="*60)
    return cfg


def _run_check_mode():
    """--check 플래그: DB 점검만 하고 종료 (서버 기동 안 함)."""
    from app.tools.db_check import run_check
    run_check()


def _seed_dev_db_if_empty():
    """개발 모드에서 격리 DB 의 환자 테이블이 비어있으면 더미 시드 (멱등).

    호출 전제: `_DEV_MODE=True` 일 때만 의미 있음. 환경변수 (DOSU_DB_PATH/APPDATA) 는
    이미 module-top 에서 격리 경로로 설정됨.
    """
    if not _DEV_MODE:
        return
    # 마이그레이션 + 환자 테이블 존재 검사
    try:
        from app.database import init_db, SessionLocal
        init_db()
        from app.models import models
        db = SessionLocal()
        try:
            if db.query(models.Patient).count() > 0:
                return  # 이미 시드됨 — 멱등
        finally:
            db.close()
    except Exception as e:
        print(f"[WARN] 더미 시드 검사 실패 (무시하고 진행): {e}")
        return

    # 시드 실행 (subprocess — 동일 환경변수 상속, 격리 DB 에 INSERT)
    import subprocess
    seed_script = Path(__file__).resolve().parent / "scripts" / "seed_dev_dummy.py"
    if not seed_script.exists():
        print(f"[WARN] 시드 스크립트 없음: {seed_script}")
        return
    print("\n[INFO] 개발 모드: 더미 데이터 시드 중 (1회) ...")
    try:
        result = subprocess.run(
            [sys.executable, str(seed_script)],
            env=os.environ.copy(),
            capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            timeout=60,
        )
        if result.returncode == 0:
            print("[OK] 더미 시드 완료 (환자 50 / 치료사 8 / 의사 2 / 치료항목 alias)\n")
        else:
            print(f"[WARN] 시드 실패 (exit {result.returncode}): {result.stderr[:300]}\n")
    except Exception as e:
        print(f"[WARN] 시드 실행 실패: {e}\n")


def main():
    # DB 점검 모드: 별도 독립 실행 경로
    if "--check" in sys.argv:
        _run_check_mode()
        return

    # 개발 모드: 격리 DB 에 더미 자동 시드 (1회 멱등)
    if _DEV_MODE:
        _seed_dev_db_if_empty()

    cfg = _ensure_main_mode()
    port = int(cfg.get("port", 8000))

    # 이미 실행 중이면 → 브라우저만 열고 종료
    if _is_already_running(port):
        print(f"이미 실행 중입니다. 브라우저를 엽니다.")
        webbrowser.open(f"http://127.0.0.1:{port}")
        time.sleep(2)
        return

    host = cfg.get("host", "0.0.0.0")
    local_ip = _get_local_ip()

    # 바탕화면 바로가기 자동 생성
    _create_desktop_shortcut(f"http://127.0.0.1:{port}")

    # 안내 출력
    print("\n" + "="*60)
    print("병원 예약 관리 - 메인 서버 실행 중")
    print("="*60)
    if _DEV_MODE:
        print("⚙ 개발 모드 (격리 DB + 더미 데이터)")
        print(f"   DB:      {os.environ.get('DOSU_DB_PATH')}")
        print(f"   APPDATA: {os.environ.get('APPDATA')}")
        print(f"   관리자비번: admin1234")
        print(f"   운영 DB 로 띄우려면: python run.py --prod")
        print("="*60)
    print(f"이 PC에서:    http://127.0.0.1:{port}")
    print(f"다른 PC/폰:   http://{local_ip}:{port}")
    print("="*60)
    print("다른 기기에서 접속 시 위 주소를 사용하세요.")
    print("종료하려면 이 창을 닫거나 Ctrl+C")
    print("="*60 + "\n")

    # 브라우저 자동 열기
    _open(f"http://127.0.0.1:{port}/")

    # 잠시 후 콘솔 최소화 (서버 시작 메시지 출력 후)
    if sys.stdout is None or not sys.stdout.isatty() or os.environ.get("AUTO_MINIMIZE", "0") == "1":
        threading.Timer(3.0, _minimize_console).start()

    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
