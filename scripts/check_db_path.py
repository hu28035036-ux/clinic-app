"""DB 경로 안전 검사 — run_check.bat 의 마지막 단계.

이 스크립트는 별도 프로세스에서 실행되어, 현재 환경에서 결정되는 DB 경로를 출력하고,
경로에 위험한 패턴이 있으면 경고를 띄운다.

운영 환경에서 단독 실행 시:
   → '%APPDATA%\\도수치료예약\\clinic.db' 가 정상적으로 출력됨 (그게 정상)

테스트 환경에서 실행 시 (DOSU_DB_PATH 또는 격리된 APPDATA 가 설정된 상태):
   → tests/temp/... 경로가 출력됨
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows 콘솔(cp949)에서 한글 / 특수문자 출력 시 UnicodeEncodeError 방지.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    # 프로젝트 루트를 sys.path 에
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from app.config import get_db_path
    except Exception as e:
        print(f"[X] app.config import 실패: {e}")
        return 1

    db_path = get_db_path()
    raw = str(db_path)
    norm = raw.lower().replace("\\", "/")

    print("=" * 60)
    print("DB 경로 안전 검사")
    print("=" * 60)
    print(f"  DOSU_DB_PATH 환경변수 : {os.environ.get('DOSU_DB_PATH', '(없음)')}")
    print(f"  APPDATA 환경변수      : {os.environ.get('APPDATA', '(없음)')}")
    print(f"  결정된 DB 경로        : {raw}")
    print()

    is_test = ("temp" in norm) or ("test" in norm) or ("/tests/" in norm)
    is_prod_pattern = (
        "appdata/roaming/도수치료예약" in norm
        and "clinic.db" in norm
        and "/tests/" not in norm
    )

    if is_test:
        print("[OK] 테스트 격리 경로입니다 ('temp' 또는 'test' 포함).")
        return 0

    if is_prod_pattern:
        # 운영 환경에서 단독 실행한 경우 — 정상.
        print("[INFO] 운영 DB 경로가 감지되었습니다.")
        print("       이 스크립트가 운영 환경에서 단독으로 실행된 경우라면 정상입니다.")
        print("       (테스트 중에는 이 경로가 보이면 안 됩니다 — conftest.py 를 확인하세요.)")
        return 0

    print(f"[?] 알 수 없는 DB 경로: {raw}")
    print("    경로에 'temp' / 'test' 도 없고, 운영 패턴도 아닙니다.")
    print("    의도한 경로인지 확인이 필요합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
