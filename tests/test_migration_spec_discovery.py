"""dosu_clinic.spec 의 마이그레이션 자동 등록 회귀 방지 테스트.

이전에는 spec 파일에 m001~m008 을 사람이 직접 적어놨고,
새 마이그레이션 추가 시 등록 깜빡 → 빌드본에서 마이그레이션 실패 → DB 스키마 불일치
사용자 에러로 이어지는 위험이 있었다.

이제는 spec 이 글롭 패턴으로 자동 감지하므로,
이 테스트가 깨진다면:
  1) spec 의 글롭 패턴이 바뀌었거나
  2) 마이그레이션 파일이 m*_*.py 외 다른 네이밍으로 추가됐거나
  3) app/migrations/__init__.py 의 동적 로딩 로직과 불일치 발생
중 하나로, 즉시 점검 필요.
"""
from __future__ import annotations

import glob
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _glob_migration_modules() -> list[str]:
    """spec 파일이 사용하는 것과 동일한 글롭 패턴으로 마이그레이션 모듈명 목록 반환."""
    files = sorted(glob.glob(str(PROJECT_ROOT / "app" / "migrations" / "m*_*.py")))
    mods = []
    for p in files:
        norm = p.replace("\\", "/").split("app/migrations/")[-1].replace(".py", "")
        mods.append(f"app.migrations.{norm}")
    return mods


def test_at_least_one_migration_discovered():
    """spec 글롭이 마이그레이션을 1개 이상 찾아내는지 — 패턴 망가짐 감지."""
    mods = _glob_migration_modules()
    assert len(mods) >= 1, (
        "spec 글롭 패턴이 마이그레이션을 못 찾고 있습니다 — "
        "디렉토리 이동이나 네이밍 변경 발생?"
    )


def test_all_migration_files_match_pattern():
    """app/migrations/ 안 m*_*.py 를 제외한 다른 모듈 파일이 끼어있지 않은지.

    예: 'm99_test.py' 라든가 잘못된 네이밍의 마이그레이션이 있으면 spec 이 못 찾음.
    """
    mig_dir = PROJECT_ROOT / "app" / "migrations"
    all_py = sorted(p.name for p in mig_dir.glob("*.py") if p.name != "__init__.py")
    pattern_matched = sorted(p.name for p in mig_dir.glob("m*_*.py"))
    assert all_py == pattern_matched, (
        f"마이그레이션 디렉토리에 패턴(m*_*.py) 에 안 맞는 파일이 있습니다.\n"
        f"  전체:  {all_py}\n"
        f"  매칭: {pattern_matched}\n"
        f"이 파일들은 자동 등록에서 빠질 수 있어 빌드본에서 마이그레이션 실패 가능."
    )


def test_spec_uses_glob_not_hardcoded_list():
    """spec 파일 자체에 동적 글롭 코드가 들어있고, 하드코딩 리스트가 (대부분) 사라졌는지."""
    spec_path = PROJECT_ROOT / "dosu_clinic.spec"
    src = spec_path.read_text(encoding="utf-8")
    assert "_glob.glob('app/migrations/m*_*.py')" in src, (
        "spec 에 마이그레이션 자동 글롭 코드가 누락됨 — 회귀."
    )
    # 자동 글롭 도입 후엔 m001~m008 같은 일일 등록이 더 이상 필요 없음.
    # 'app.migrations.m001_baseline' 같은 하드코딩이 다시 들어왔다면 자동 글롭과 중복으로 깨질 수 있음.
    # 주석 라인(예시 안내)은 제외.
    hardcoded_lines = [
        line for line in src.splitlines()
        if "'app.migrations.m" in line
        and "_" in line
        and not line.lstrip().startswith("#")
    ]
    assert hardcoded_lines == [], (
        "spec 에 마이그레이션 모듈명이 하드코딩되어 있습니다:\n  "
        + "\n  ".join(hardcoded_lines)
        + "\n자동 글롭과 중복되므로 제거 필요."
    )


def test_glob_modules_actually_importable():
    """글롭으로 찾은 모듈명이 실제로 importable 한지 (네이밍 변환 검증)."""
    import importlib

    mods = _glob_migration_modules()
    failed = []
    for mod_name in mods:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            failed.append((mod_name, str(e)))
    assert not failed, f"마이그레이션 모듈 import 실패: {failed}"
