"""apply_update 의 updater 실행 방식 + updater.bat 의 pause 위치 회귀 방지.

검증 포인트:
  1. Popen 명령이 'cmd /k' 가 아닌 'cmd /c' 로 자식 콘솔을 띄운다 — /k 면 정상 종료 후에도
     사용자가 직접 콘솔을 닫아야 했던 회귀.
  2. apply_update 가 proc.poll() 로 "updater 즉시 종료 검증" 을 하지 않는다 — proc 는
     중간 launcher cmd 일 뿐이라 updater 의 생존 여부와 무관하다.
  3. updater.bat 의 pause 는 :rollback 라벨 뒤 (실패 경로) 에만 존재 — 성공 경로엔 없음.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from app.routers import api as api_mod

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────
# (1) Popen 호출이 /c 로 자식 콘솔을 띄우는지
# ─────────────────────────────────────────────────────────


def test_apply_update_uses_cmd_slash_c_not_slash_k():
    """apply_update 의 Popen 인자에 'cmd', '/k' 시퀀스가 없어야 함.

    /k 는 명령 실행 후 콘솔 유지 — 정상 업데이트 후에도 콘솔이 그대로 남아 사용자가
    직접 닫아야 했던 UX 문제. /c 로 바꿔 성공 경로는 자동 종료, 실패(rollback) 경로는
    updater.bat 안의 pause 로 사용자 입력 대기.
    """
    src = inspect.getsource(api_mod.apply_update)

    # docstring 제거 후 검사 — 안내문에 '/k' 가 들어갈 수도 있음
    code_only = re.sub(r'""".*?"""', '', src, count=1, flags=re.DOTALL)

    # 두 cmd 토큰 사이에 '/k' 가 인자로 들어가 있는지 검사
    # 정상: ["cmd", "/c", "start", "", "cmd", "/c", str(updater)]
    # 회귀: ["cmd", "/c", "start", "", "cmd", "/k", str(updater)]
    assert '"/k"' not in code_only and "'/k'" not in code_only, (
        "apply_update 의 Popen 명령에 '/k' 가 포함됨 — 성공 후 콘솔이 안 닫혀 회귀."
    )


def test_apply_update_does_not_poll_launcher_cmd():
    """apply_update 가 proc.poll() 로 updater 생존을 판정하지 않아야 함.

    proc 는 `start` 를 호출하는 launcher cmd /c 셸이라 start 가 윈도우를 띄운 직후
    바로 returncode=0 으로 끝남 — updater 자체가 살아있는지와 무관.
    이런 잘못된 검증을 다시 도입하지 않도록 회귀 방지.

    docstring + '#' 주석을 모두 제거한 뒤 실제 실행 코드에서만 검사.
    """
    src = inspect.getsource(api_mod.apply_update)
    code_only = re.sub(r'""".*?"""', '', src, count=1, flags=re.DOTALL)
    # '#' 으로 시작하는 라인(주석) 제거
    code_lines = [
        line for line in code_only.splitlines()
        if not line.strip().startswith("#")
    ]
    code_no_comments = "\n".join(code_lines)

    assert "proc.poll(" not in code_no_comments, (
        "apply_update 가 다시 proc.poll() 로 launcher cmd 를 검사하고 있음 — "
        "updater 생존 검증으로 오해된 회귀."
    )


# ─────────────────────────────────────────────────────────
# (2) updater.bat 의 pause 위치
# ─────────────────────────────────────────────────────────


def _read_bat() -> str:
    return (PROJECT_ROOT / "updater.bat").read_text(encoding="utf-8")


def test_updater_bat_pause_only_on_rollback_path():
    """updater.bat 의 pause 명령은 :rollback 라벨 뒤에만 등장."""
    bat = _read_bat()
    rollback_idx = bat.find(":rollback")
    assert rollback_idx > 0, "updater.bat 에 :rollback 라벨이 없습니다 — 회귀."

    # 'pause' 토큰이 단어로 등장하는 위치 모두 찾기 (주석/문자열 제외)
    pause_positions = []
    for m in re.finditer(r"^\s*pause\b", bat, flags=re.MULTILINE):
        pause_positions.append(m.start())

    # 모든 pause 가 :rollback 라벨 뒤에 있어야 함
    for pos in pause_positions:
        assert pos > rollback_idx, (
            "updater.bat 의 pause 가 성공 경로(rollback 전)에서 발견됨 — "
            "성공 후에도 사용자가 콘솔을 직접 닫아야 하는 회귀."
        )
    assert len(pause_positions) >= 1, (
        "updater.bat 에 pause 가 전혀 없음 — rollback 시 사용자가 오류 메시지를 못 보고 "
        "콘솔이 닫히는 회귀."
    )


def test_updater_bat_success_exit_has_no_pause():
    """성공 경로(exit /b 0)와 그 직전 5줄 안에 pause 가 없어야 함."""
    bat = _read_bat()
    # 첫 번째 'exit /b 0' 위치 찾기 (성공 경로). 두 번째는 없음 — 한 번만 등장해야 함.
    exit0 = re.search(r"exit\s*/b\s*0", bat)
    assert exit0, "updater.bat 에 'exit /b 0' (성공 경로) 가 없습니다."
    around = bat[max(0, exit0.start() - 200):exit0.start()]
    assert not re.search(r"^\s*pause\b", around, flags=re.MULTILINE), (
        "성공 경로 직전에 pause 가 있음 — 정상 업데이트 후에도 사용자 입력을 기다리는 회귀."
    )
