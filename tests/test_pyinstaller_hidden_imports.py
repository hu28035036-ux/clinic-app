"""18-8 PyInstaller hidden imports 사전 검증.

목적:
  ``dosu_clinic.spec`` 의 ``hidden`` 리스트에 등록된 모든 모듈이 실제로
  import 가능한지 빌드 전 확인. 빌드 후 런타임 ImportError 를 사전 차단.

배경:
  v1.3.2 사고 — ``collect_submodules`` 실패가 try/except 로 삼켜져서 SDK 가
  번들에 누락. 이제는 spec 자체가 collect 실패 시 즉시 RuntimeError.

  18-1~18-7 추가 모듈 (rag/, knowledge/, vector/, health) 은 본 세션 (18-8)
  까지 spec hiddenimports 에 등록되지 않은 상태였음. 18-8 에서 누락만
  보강 (체크리스트 §16 "오타/누락만 허용").

검증 범위:
  1. spec 파일을 파싱해서 ``hidden`` 리스트 추출 (런타임 처리).
  2. 모든 Python 모듈명 (점 표기) 에 대해 ``importlib.import_module`` 시도.
  3. 실패 시 어떤 모듈이 실패했는지 명확히 보고.

원칙:
  - 외부 호출 0 — import 만 시도.
  - 실제 PyInstaller 실행은 본 테스트 범위 외 (사용자 승인 필요).
  - 본 테스트가 통과한다고 PyInstaller 빌드가 100% 성공한다는 보장은 X
    (data files / binary collection 은 별도 검증). 단, hidden imports
    누락 사고는 100% 차단.

상세: ``docs/checklists/18-8_final_release_checklist.md`` 완료 조건,
``docs/ai_rag_migration_plan.md`` §12 spec hidden import 체크리스트.
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

# ──────────────────────── spec 파싱 helper ────────────────────────


def _spec_path() -> Path:
    return Path(__file__).resolve().parent.parent / "dosu_clinic.spec"


def _extract_hidden_imports() -> list[str]:
    """``dosu_clinic.spec`` 에서 ``hidden`` 리스트의 문자열 항목 추출.

    spec 의 ``hidden += [...]`` 블록 안의 문자열 리터럴만 정규식으로 수집.
    ``collect_submodules`` 호출은 import-time 실행이 필요하므로 스킵 —
    별도 정확성은 spec 자체가 빌드 시 검증.
    """
    text = _spec_path().read_text(encoding="utf-8")
    # 단순 정규식: 'foo.bar' 또는 "foo.bar" 형식의 점 표기 모듈명만 수집.
    # 짧은 식별자 (예: 'multipart') 도 포함.
    # 주석 라인 제외 (# 으로 시작).
    out: list[str] = []
    # 파일 확장자 (모듈 아님 — datas/Analysis 항목으로 오인 방지).
    _file_ext_suffixes = (".py", ".ico", ".bat", ".txt", ".json", ".md", ".html",
                          ".css", ".js", ".sql", ".spec", ".cfg", ".toml", ".yml",
                          ".yaml", ".png", ".jpg", ".gif", ".svg")

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # 'name' 또는 "name" — 식별자/점 표기만.
        for m in re.finditer(r"['\"]([a-zA-Z_][a-zA-Z_0-9.]*)['\"]", line):
            name = m.group(1)
            # 파일 확장자 가진 문자열 — datas/Analysis 의 경로 항목, 모듈 아님.
            if name.lower().endswith(_file_ext_suffixes):
                continue
            # spec 자체의 변수/문자열 (예: name='도수치료예약', upx_exclude=[]) 제외.
            # 한글이 들어간 문자열은 식별자 패턴에 안 잡힘.
            # 모듈처럼 보이는 항목만 (점 포함 또는 알려진 single-token 모듈)
            if "." in name or name in (
                "app", "uvicorn", "openpyxl", "openai", "anthropic",
                "multipart", "et_xmlfile", "tkinter", "matplotlib",
                "numpy", "pandas", "PyQt5", "PyQt6",
            ):
                out.append(name)
    return out


def _classify_modules(items: list[str]) -> dict[str, list[str]]:
    """수집된 항목을 카테고리로 분류 — 디버깅 용이성."""
    cat: dict[str, list[str]] = {
        "app_routers": [],
        "app_services_ai": [],
        "app_services_rag": [],
        "app_services_other": [],
        "app_models": [],
        "app_misc": [],
        "third_party": [],
        "stdlib": [],
        "exclude_filter": [],  # spec excludes 항목
    }
    excludes = {"tkinter", "matplotlib", "numpy", "pandas", "PyQt5", "PyQt6"}
    for n in items:
        if n in excludes:
            cat["exclude_filter"].append(n)
        elif n.startswith("app.routers"):
            cat["app_routers"].append(n)
        elif n.startswith("app.services.ai"):
            cat["app_services_ai"].append(n)
        elif n.startswith("app.services.rag"):
            cat["app_services_rag"].append(n)
        elif n.startswith("app.services"):
            cat["app_services_other"].append(n)
        elif n.startswith("app.models"):
            cat["app_models"].append(n)
        elif n.startswith("app"):
            cat["app_misc"].append(n)
        elif n.startswith(("sqlalchemy", "fastapi", "pydantic", "uvicorn", "openpyxl",
                           "openai", "anthropic", "multipart", "et_xmlfile")):
            cat["third_party"].append(n)
        else:
            cat["stdlib"].append(n)
    return cat


# ──────────────────────── 1. spec 파싱 ────────────────────────


def test_spec_file_exists():
    """``dosu_clinic.spec`` 파일이 존재."""
    p = _spec_path()
    assert p.exists(), f"dosu_clinic.spec 미존재: {p}"


def test_spec_extracts_at_least_30_modules():
    """spec 에서 최소 30개 hidden import 모듈 추출 (sanity)."""
    items = _extract_hidden_imports()
    unique = set(items)
    assert len(unique) >= 30, (
        f"spec hidden imports 가 너무 적음: {len(unique)}개 (최소 30 기대)"
    )


# ──────────────────────── 2. import 가능성 ────────────────────────


def test_all_app_modules_importable():
    """spec 의 ``app.*`` hidden import 가 모두 실제로 import 가능.

    이 테스트가 fail 하면 PyInstaller 빌드 후 런타임 ImportError 가 발생할
    가능성이 매우 높음. 빌드 전에 사전 차단.
    """
    items = _extract_hidden_imports()
    cat = _classify_modules(items)

    app_modules = (
        cat["app_routers"]
        + cat["app_services_ai"]
        + cat["app_services_rag"]
        + cat["app_services_other"]
        + cat["app_models"]
        + cat["app_misc"]
    )

    failures: list[tuple[str, str]] = []
    for name in sorted(set(app_modules)):
        try:
            importlib.import_module(name)
        except Exception as e:
            failures.append((name, f"{type(e).__name__}: {e}"))

    assert not failures, (
        "spec hidden imports import 실패 (PyInstaller 빌드 후 런타임 ImportError 위험):\n"
        + "\n".join(f"  - {n}: {err}" for n, err in failures)
    )


def test_third_party_modules_importable():
    """spec 의 third-party hidden import (openai/anthropic/uvicorn/openpyxl 등) import 가능.

    SDK 미설치 환경에서는 spec 자체가 빌드 시 RuntimeError 를 발생시키므로,
    venv 가 정상 setup 된 환경에서만 본 테스트가 의미.
    """
    items = _extract_hidden_imports()
    cat = _classify_modules(items)

    failures: list[tuple[str, str]] = []
    for name in sorted(set(cat["third_party"])):
        try:
            importlib.import_module(name)
        except Exception as e:
            failures.append((name, f"{type(e).__name__}: {e}"))

    assert not failures, (
        "third-party hidden imports 실패:\n"
        + "\n".join(f"  - {n}: {err}" for n, err in failures)
    )


def test_stdlib_modules_importable():
    """spec 의 stdlib hidden import (sqlalchemy.dialects.sqlite, email.mime 등) import 가능."""
    items = _extract_hidden_imports()
    cat = _classify_modules(items)

    failures: list[tuple[str, str]] = []
    for name in sorted(set(cat["stdlib"])):
        try:
            importlib.import_module(name)
        except Exception as e:
            failures.append((name, f"{type(e).__name__}: {e}"))

    assert not failures, (
        "stdlib/hybrid hidden imports 실패:\n"
        + "\n".join(f"  - {n}: {err}" for n, err in failures)
    )


# ──────────────────────── 3. 18-1~18-7 신규 모듈 누락 검증 ────────────────────────


# 18-1~18-7 에서 추가된 신규 모듈 — spec hiddenimports 에 반드시 포함되어야 함.
EXPECTED_18_X_MODULES = (
    # 18-1 RAG 골격
    "app.services.ai.rag",
    "app.services.ai.rag.schemas",
    "app.services.ai.rag.prompts",
    "app.services.ai.rag.safety",
    "app.services.ai.rag.retriever",
    "app.services.ai.rag.pipeline",
    # 18-3 chunker
    "app.services.ai.knowledge",
    "app.services.ai.knowledge.loader",
    "app.services.ai.knowledge.normalizer",
    "app.services.ai.knowledge.chunker",
    "app.services.ai.knowledge.keyword_index",
    # 18-4 reindex (indexer)
    "app.services.ai.knowledge.indexer",
    # 18-5 vector
    "app.services.ai.vector",
    "app.services.ai.vector.embeddings",
    "app.services.ai.vector.store",
    "app.services.ai.vector.similarity",
    # 18-6 hybrid
    "app.services.ai.rag.reranker",
    "app.services.ai.rag.confidence",
    # 18-7 admin status
    "app.services.ai.health",
)


# 19-1 core 공통 유틸 (re-export wrapper 3 + 신규 helper 4 + __init__ = 8)
# spec hiddenimports 에 반드시 포함되어야 함 (PyInstaller 빌드본 import 안전성).
# COMPAT: 기존 app.config / app.database / app.services.auth 경로는 그대로 동작.
EXPECTED_19_X_CORE_MODULES = (
    "app.core",
    "app.core.config",
    "app.core.database",
    "app.core.security",
    "app.core.errors",
    "app.core.responses",
    "app.core.time_utils",
    "app.core.feature_flags",
)


@pytest.mark.parametrize("modname", EXPECTED_18_X_MODULES)
def test_18_X_module_in_spec_hidden_imports(modname):
    """18-1~18-7 신규 모듈이 spec hiddenimports 에 등록됨.

    spec 누락 시 PyInstaller 빌드는 통과해도 런타임 ImportError.
    각 모듈을 개별 parametrize 로 검증해서 fail 시 정확한 모듈명 보고.
    """
    items = _extract_hidden_imports()
    assert modname in items, (
        f"spec hiddenimports 에 {modname!r} 누락 — PyInstaller 빌드 후 런타임 ImportError 위험. "
        f"dosu_clinic.spec 의 hidden 리스트에 추가하세요."
    )


@pytest.mark.parametrize("modname", EXPECTED_18_X_MODULES)
def test_18_X_module_actually_importable(modname):
    """18-1~18-7 신규 모듈이 실제로 import 가능 (코드 자체 검증)."""
    try:
        importlib.import_module(modname)
    except Exception as e:
        pytest.fail(f"{modname} import 실패: {type(e).__name__}: {e}")


@pytest.mark.parametrize("modname", EXPECTED_19_X_CORE_MODULES)
def test_19_X_core_module_in_spec_hidden_imports(modname):
    """19-1 core 신규 모듈이 spec hiddenimports 에 등록됨.

    spec 누락 시 PyInstaller 빌드는 통과해도 런타임 ImportError.
    각 모듈을 개별 parametrize 로 검증해서 fail 시 정확한 모듈명 보고.
    """
    items = _extract_hidden_imports()
    assert modname in items, (
        f"spec hiddenimports 에 {modname!r} 누락 — PyInstaller 빌드 후 런타임 ImportError 위험. "
        f"dosu_clinic.spec 의 hidden 리스트에 추가하세요."
    )


@pytest.mark.parametrize("modname", EXPECTED_19_X_CORE_MODULES)
def test_19_X_core_module_actually_importable(modname):
    """19-1 core 신규 모듈이 실제로 import 가능 (코드 자체 검증).

    re-export wrapper (config/database/security) + 신규 helper
    (errors/responses/time_utils/feature_flags) 모두 검증.
    """
    try:
        importlib.import_module(modname)
    except Exception as e:
        pytest.fail(f"{modname} import 실패: {type(e).__name__}: {e}")


# 19-2 modules 후보 구조 (settings/health) — facade / 직렬화 helper.
# 19-3 추가 — modules.calendar 표시용 view-model helper.
# 19-4 추가 — modules.appointments availability 판정 helper (라우터 무수정).
# 19-5 추가 — modules.leaves 휴무 도메인 규칙 / 조회 / service helper (라우터 무수정).
# 19-6 추가 — modules.treatments 치료항목 분류 / 조회 / 직렬화 / 완료체크 (라우터 무수정).
# 19-7 추가 — modules.patients / modules.notes 환자·메모 도메인 (라우터 무수정).
# 19-8 추가 — modules.therapists 치료사 / 직원 도메인 (라우터 무수정).
# 19-9 추가 — modules.appointments rules / repository / service / schemas (라우터 무수정).
# 19-10 추가 — modules.sms rules / templates / service / provider / schemas (라우터 무수정).
# COMPAT: 기존 app.routers.api / app.routers.ai / app.services.ai.health 그대로 동작.
EXPECTED_19_X_MODULES_MODULES = (
    "app.modules",
    "app.modules.settings",
    "app.modules.settings.serializers",
    "app.modules.health",
    "app.modules.calendar",
    "app.modules.calendar.view_models",
    "app.modules.appointments",
    "app.modules.appointments.availability",
    "app.modules.appointments.rules",
    "app.modules.appointments.repository",
    "app.modules.appointments.service",
    "app.modules.appointments.schemas",
    "app.modules.leaves",
    "app.modules.leaves.rules",
    "app.modules.leaves.repository",
    "app.modules.leaves.service",
    "app.modules.treatments",
    "app.modules.treatments.rules",
    "app.modules.treatments.repository",
    "app.modules.treatments.service",
    "app.modules.treatments.completion_rules",
    "app.modules.patients",
    "app.modules.patients.rules",
    "app.modules.patients.repository",
    "app.modules.patients.service",
    "app.modules.notes",
    "app.modules.notes.rules",
    "app.modules.therapists",
    "app.modules.therapists.rules",
    "app.modules.therapists.repository",
    "app.modules.therapists.service",
    "app.modules.sms",
    "app.modules.sms.rules",
    "app.modules.sms.templates",
    "app.modules.sms.service",
    "app.modules.sms.provider",
    "app.modules.sms.schemas",
    "app.modules.stats",
    "app.modules.stats.rules",
    "app.modules.stats.repository",
    "app.modules.stats.aggregators",
    "app.modules.stats.service",
    "app.modules.stats.schemas",
    # 19-12 추가 — modules.admin / backup / audit / export_import (라우터 무수정).
    "app.modules.admin",
    "app.modules.admin.service",
    "app.modules.admin.schemas",
    "app.modules.backup",
    "app.modules.backup.service",
    "app.modules.backup.schemas",
    "app.modules.audit",
    "app.modules.audit.service",
    "app.modules.audit.schemas",
    "app.modules.export_import",
    "app.modules.export_import.service",
    "app.modules.export_import.schemas",
    # 19-13 추가 — modules.ai.commands AI commands Preview/Approval/Execute 경계 (라우터 무수정).
    "app.modules.ai",
    "app.modules.ai.commands",
    "app.modules.ai.commands.schemas",
    "app.modules.ai.commands.safety",
    "app.modules.ai.commands.preview",
    "app.modules.ai.commands.executor",
    "app.modules.ai.commands.service",
    "app.modules.ai.commands.adapters",
)


@pytest.mark.parametrize("modname", EXPECTED_19_X_MODULES_MODULES)
def test_19_X_modules_module_in_spec_hidden_imports(modname):
    """19-2 modules 신규 폴더가 spec hiddenimports 에 등록됨."""
    items = _extract_hidden_imports()
    assert modname in items, (
        f"spec hiddenimports 에 {modname!r} 누락 — PyInstaller 빌드 후 런타임 ImportError 위험. "
        f"dosu_clinic.spec 의 hidden 리스트에 추가하세요."
    )


@pytest.mark.parametrize("modname", EXPECTED_19_X_MODULES_MODULES)
def test_19_X_modules_module_actually_importable(modname):
    """19-2 modules 신규 폴더가 실제로 import 가능 (코드 자체 검증).

    settings/serializers + health (re-export wrapper) 모두 검증.
    """
    try:
        importlib.import_module(modname)
    except Exception as e:
        pytest.fail(f"{modname} import 실패: {type(e).__name__}: {e}")


# ──────────────────────── 4. data files 동봉 정합 ────────────────────────


def test_knowledge_directory_exists_for_data_bundle():
    """``knowledge/`` 디렉토리 존재 — spec datas 에 ``('knowledge', 'knowledge')`` 등록됨.

    spec 가 빌드 시 본 디렉토리를 ``_MEIPASS/knowledge/`` 로 복사.
    """
    p = _spec_path().parent / "knowledge"
    assert p.exists() and p.is_dir(), f"knowledge/ 디렉토리 미존재: {p}"
    # 최소 1개 매뉴얼 .md 파일 존재.
    md_files = list(p.rglob("*.md"))
    assert len(md_files) >= 1, f"knowledge/ 에 .md 파일 부재: {p}"


def test_app_templates_exists_for_data_bundle():
    """``app/templates/`` 디렉토리 존재 (main.html 등)."""
    p = _spec_path().parent / "app" / "templates"
    assert p.exists() and p.is_dir(), f"app/templates 미존재: {p}"


def test_app_static_exists_for_data_bundle():
    """``app/static/`` 디렉토리 존재 (CSS 등)."""
    p = _spec_path().parent / "app" / "static"
    assert p.exists() and p.is_dir(), f"app/static 미존재: {p}"


def test_updater_bat_exists_for_data_bundle():
    """``updater.bat`` 파일 존재 — spec post-build 가 dist 루트로 복사."""
    p = _spec_path().parent / "updater.bat"
    assert p.exists() and p.is_file(), f"updater.bat 미존재: {p}"


# ──────────────────────── 5. 마이그레이션 자동 발견 ────────────────────────


def test_migrations_directory_has_files():
    """``app/migrations/`` 에 m*_*.py 파일 1개 이상 — spec glob 자동 발견 보장."""
    p = _spec_path().parent / "app" / "migrations"
    assert p.exists() and p.is_dir()
    migrations = list(p.glob("m*_*.py"))
    assert len(migrations) >= 13, (
        f"마이그레이션 파일 부족: {len(migrations)}개 (m001~m013 최소 13개 기대). "
        f"발견: {sorted(m.name for m in migrations)}"
    )


def test_all_migration_modules_importable():
    """모든 마이그레이션 모듈이 import 가능 — spec glob 결과 검증."""
    p = _spec_path().parent / "app" / "migrations"
    migrations = sorted(p.glob("m*_*.py"))

    failures: list[tuple[str, str]] = []
    for mig_path in migrations:
        modname = f"app.migrations.{mig_path.stem}"
        try:
            importlib.import_module(modname)
        except Exception as e:
            failures.append((modname, f"{type(e).__name__}: {e}"))

    assert not failures, (
        "마이그레이션 모듈 import 실패 (spec glob 자동 발견 불가):\n"
        + "\n".join(f"  - {n}: {err}" for n, err in failures)
    )


def test_migrations_m001_to_m013_present():
    """m001 ~ m013 모두 존재 — 18-8 시점 마지막 마이그레이션 m013."""
    p = _spec_path().parent / "app" / "migrations"
    migrations = {m.stem.split("_", 1)[0] for m in p.glob("m*_*.py")}
    expected = {f"m{i:03d}" for i in range(1, 14)}  # m001 ~ m013
    missing = expected - migrations
    assert not missing, f"마이그레이션 누락: {missing}"


# ──────────────────────── 6. spec 자체 검증 ────────────────────────


def test_spec_does_not_have_silent_collect_failure():
    """spec 가 collect_submodules 실패를 try/except 로 삼키지 않음 (v1.3.2 사고 방지).

    ``raise RuntimeError`` 로 실패 시 즉시 빌드 중단해야 함.
    """
    text = _spec_path().read_text(encoding="utf-8")
    # 최소 한 번 이상 raise RuntimeError 가 있어야 (SDK collect 실패 가드).
    assert "raise RuntimeError" in text, (
        "spec 에 collect_submodules 실패 가드 (raise RuntimeError) 부재 — "
        "v1.3.2 SDK 누락 사고 재발 위험"
    )


def test_spec_excludes_heavy_unused_libraries():
    """spec excludes 에 tkinter / matplotlib / numpy / pandas / PyQt5/6 — 빌드 크기."""
    text = _spec_path().read_text(encoding="utf-8")
    for excl in ("tkinter", "matplotlib", "numpy", "pandas"):
        assert excl in text, f"spec excludes 에 {excl!r} 부재 — 빌드 크기 증가 위험"


def test_spec_console_disabled_for_windowed_app():
    """spec console=False — Windows 작업표시줄에 cmd 창 표시 안 함."""
    text = _spec_path().read_text(encoding="utf-8")
    assert "console=False" in text, "spec console=False 부재 — cmd 창 표시 위험"
