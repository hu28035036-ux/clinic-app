# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec - 병원 예약 관리 (배포용)
빌드 명령: pyinstaller dosu_clinic.spec
결과물:    dist/도수치료예약/  (폴더 안에 도수치료예약.exe)
"""
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# --- 숨은 모듈(PyInstaller가 자동 감지 못 하는 것들) 수집 ---
hidden = []
# ⚠ openpyxl 은 서브모듈 수십 개 + XML 스키마 데이터 파일 필요 →
#    수동 나열하면 누락 발생. collect_submodules 로 전수 포함.
for m in ('uvicorn', 'uvicorn.protocols', 'uvicorn.lifespan', 'uvicorn.loops',
          'openpyxl'):
    hidden += collect_submodules(m)

# AI SDK — provider 선택형. 둘 다 빌드에 포함해 사용자가 어느 쪽이든 선택 가능하게.
# ⚠ 과거에 try/except 로 collect 실패를 삼켜서 번들에 누락된 사고가 있었음 (v1.3.2).
#   이제는 실패 시 빌드를 즉시 중단해서 누락 사실을 빨리 발견한다.
_ai_sdk_modules = []
for m in ('openai', 'anthropic'):
    subs = collect_submodules(m)
    if not subs:
        raise RuntimeError(
            f"[spec] '{m}' SDK 가 venv 에 없거나 collect_submodules 가 빈 리스트를 "
            f"반환했습니다. 'pip install -r requirements.txt' 후 재빌드 하세요."
        )
    _ai_sdk_modules += subs
hidden += _ai_sdk_modules

hidden += [
    'app', 'app.main', 'app.config', 'app.database',
    'app.routers.pages', 'app.routers.api', 'app.routers.ai',
    'app.models.models', 'app.models.schemas', 'app.models.constants',
    'app.services.sync', 'app.services.auth',
    'app.services.backup', 'app.services.seed',
    # AI/RAG 서비스 (v1.3 단계 1+2) — 라우터에서 import 되므로 명시
    'app.services.ai',
    'app.services.ai.provider',
    'app.services.ai.openai_client',
    'app.services.ai.anthropic_client',
    'app.services.ai.pii',
    'app.services.ai.prompts',
    'app.services.ai.validators',
    'app.services.ai.ai_logging',
    'app.services.ai.sms_draft',
    'app.services.ai.manual_qa',
    # AI 휴무 액션 (v1.3.3 세션 16) — 라우터에서 import
    'app.services.ai.action_leave',
    'app.services.ai.date_resolver',
    # 18-7 관리자 상태 집계 — /api/ai/status 엔드포인트가 import.
    # 라우터는 'health as ai_status_mod' 로 import 하므로 PyInstaller 가
    # 자동 발견하지만 명시 등록으로 누락 방지.
    'app.services.ai.health',
    # 18-1~18-6 RAG 패키지 — manual_qa wrapper 가 rag.pipeline 을 통해
    # 간접 import. 일부 모듈 (reranker/confidence/store/similarity 등) 은
    # lazy import 라 PyInstaller 자동 발견 누락 위험 → 명시 등록.
    'app.services.ai.rag',
    'app.services.ai.rag.schemas',
    'app.services.ai.rag.prompts',
    'app.services.ai.rag.safety',
    'app.services.ai.rag.retriever',
    'app.services.ai.rag.pipeline',
    'app.services.ai.rag.reranker',     # 18-6
    'app.services.ai.rag.confidence',   # 18-6
    # 18-3/18-4 knowledge 패키지 — chunker/indexer/loader/normalizer/keyword_index
    'app.services.ai.knowledge',
    'app.services.ai.knowledge.loader',
    'app.services.ai.knowledge.normalizer',
    'app.services.ai.knowledge.chunker',
    'app.services.ai.knowledge.keyword_index',
    'app.services.ai.knowledge.indexer',
    # 18-5 vector 패키지 — indexer 가 lazy import (vector 패키지 부재 환경
    # 호환). 운영 빌드에서는 명시 등록 필수.
    'app.services.ai.vector',
    'app.services.ai.vector.embeddings',
    'app.services.ai.vector.store',
    'app.services.ai.vector.similarity',
    # RAG 검색 (knowledge/ 키워드 인덱스 로딩) — v1.3.3 keyword RAG (분리 전 경로)
    'app.services.rag',
    'app.services.rag.search',
    # 19-1 core 공통 유틸 (config/database/security re-export wrapper + errors/responses/time_utils/feature_flags 신규)
    # COMPAT: 기존 app.config / app.database / app.services.auth 도 그대로 동작
    'app.core',
    'app.core.config',
    'app.core.database',
    'app.core.security',
    'app.core.errors',
    'app.core.responses',
    'app.core.time_utils',
    'app.core.feature_flags',
    # 19-2 modules 후보 구조 (settings/health) — facade / re-export wrapper
    # COMPAT: 기존 app.routers.api / app.routers.ai / app.services.ai.health 그대로 동작
    'app.modules',
    'app.modules.settings',
    'app.modules.settings.serializers',
    'app.modules.health',
    # 증분 마이그레이션 — importlib 로 동적 로드되므로 명시 hidden import 필수
    # ⚠ 새 마이그레이션 추가 시 깜빡 위험 → 아래에서 자동 글롭으로 대체.
    'app.migrations',
    # DB 점검 도구
    'app.tools', 'app.tools.db_check',
    # SQLAlchemy는 sqlite 드라이버를 동적으로 불러오므로 반드시 포함
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.sqlite.pysqlite',
    # FastAPI/pydantic이 사용하는 하위 모듈
    'email.mime', 'email.mime.multipart', 'email.mime.text',
    # 파일 업로드(multipart) 지원
    'multipart', 'multipart.multipart',
    # openpyxl 의 의존 라이브러리 et_xmlfile (lazy import 라 놓침)
    'et_xmlfile',
    # openai / anthropic SDK 는 위 collect_submodules 루프에서 hidden 에 추가됨.
]

# --- 마이그레이션 자동 발견 ---
# app/migrations/m*_*.py 를 글롭으로 찾아서 hidden 에 자동 추가.
# 이전엔 m001~m008 을 spec 에 일일이 적었는데 새 마이그레이션 추가 시 등록을 깜빡하면
# 빌드본에서 importlib.import_module 이 실패해 DB 마이그레이션이 안 돌아 사용자 에러 발생.
# 이제는 파일이 추가되면 자동으로 감지됨.
import glob as _glob
_migration_files = sorted(_glob.glob('app/migrations/m*_*.py'))
_migration_modules = []
for _path in _migration_files:
    # 'app/migrations/m007_ai_settings.py' → 'app.migrations.m007_ai_settings'
    _norm = _path.replace('\\', '/').replace('.py', '').replace('/', '.')
    _migration_modules.append(_norm)
    hidden.append(_norm)

# 빌드 시점 안전망: 마이그레이션이 단 1개도 없으면 빌드 중단.
# (글롭 패턴 오타 / 디렉토리 이동 같은 사고를 즉시 발견)
if not _migration_modules:
    raise RuntimeError(
        "[spec] app/migrations/ 에서 m*_*.py 마이그레이션 파일을 1개도 못 찾았습니다. "
        "글롭 패턴이나 디렉토리 구조를 확인하세요."
    )
print(f"[spec] migration auto-register: {len(_migration_modules)} modules - {_migration_modules}")

# --- 포함할 리소스 파일 (템플릿 / CSS / 업데이터) ---
datas = [
    ('app/templates', 'app/templates'),
    ('app/static',    'app/static'),
    # v1.3: RAG 톤 가이드 + 인덱스. _MEIPASS/knowledge/ 에 그대로 풀림.
    ('knowledge',     'knowledge'),
    # updater.bat: 자동 업데이트 시 본체 종료 후 파일 교체 담당.
    # '.' 는 COLLECT 루트 = dist/도수치료예약/ — 그 루트에 updater.bat 배치.
    ('updater.bat',   '.'),
]
# openpyxl 은 XML/ZIP 관련 리소스 파일이 있어 collect_data_files 로 함께 복사해야
#   실제 .xlsx 파싱 시 누락 에러가 안 남
datas += collect_data_files('openpyxl')
# AI SDK 가 의존하는 데이터 파일 (예: openai 의 _resources, anthropic 의 _types).
# collect_submodules 만으로는 .py 만 잡혀 일부 토큰화/스키마 리소스가 누락될 수 있음.
datas += collect_data_files('openai')
datas += collect_data_files('anthropic')

# --- 아이콘 (icon.ico가 프로젝트 루트에 있으면 자동 사용) ---
icon_path = 'icon.ico' if os.path.exists('icon.ico') else None

a = Analysis(
    ['run.py'],
    pathex=['.'],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PyQt5', 'PyQt6'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# --- EXE: onedir 방식 (exclude_binaries=True가 핵심) ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='도수치료예약',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX는 백신 오탐 원인 → 끔
    console=False,        # ★ cmd 창 숨김 (작업표시줄에도 안 뜸)
    disable_windowed_traceback=False,
    icon=icon_path,
)

# --- 폴더 배포물 구성 ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='도수치료예약',   # ★ dist/도수치료예약/ 폴더가 최종 배포물
)

# --- 빌드 후처리: updater.bat 을 _internal/ 에서 배포 루트로 복사 ---
# PyInstaller datas 는 항상 _internal/ 밑에 들어가지만, updater.bat 은
# 루트(도수치료예약.exe 와 같은 폴더)에 있어야 %~dp0 경로가 맞음.
import shutil as _sh, os as _os
_dist_root = _os.path.join('dist', '도수치료예약')
_src_bat = _os.path.join(_dist_root, '_internal', 'updater.bat')
_dst_bat = _os.path.join(_dist_root, 'updater.bat')
if _os.path.exists(_src_bat):
    _sh.copy2(_src_bat, _dst_bat)
    print(f"[spec post-build] updater.bat -> {_dst_bat}")
