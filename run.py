"""진입점 - 메인 PC 자동 설정 버전.
첫 실행 시 자동으로 메인 모드로 세팅되어 바로 사용 가능.
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


def main():
    # DB 점검 모드: 별도 독립 실행 경로
    if "--check" in sys.argv:
        _run_check_mode()
        return

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
