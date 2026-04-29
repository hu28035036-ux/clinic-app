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
    # 증분 마이그레이션 — importlib 로 동적 로드되므로 명시 hidden import 필수
    'app.migrations',
    'app.migrations.m001_baseline',
    'app.migrations.m002_add_gender',
    'app.migrations.m003_add_api_url',
    'app.migrations.m004_add_indexes',
    'app.migrations.m005_treatment_price_incentive',
    'app.migrations.m006_manual_counts',
    'app.migrations.m007_ai_settings',
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
    # ⚠ openai / anthropic SDK 는 아직 requirements.txt 에 없음.
    # 실제 LLM 호출 기능을 켜는 단계에서 (a) requirements.txt 에 추가하고
    # (b) 여기 hiddenimports 에 'openai' / 'anthropic' (또는 collect_submodules)
    # 둘 다 등록해야 함.
]

# --- 포함할 리소스 파일 (템플릿 / CSS / 업데이터) ---
datas = [
    ('app/templates', 'app/templates'),
    ('app/static',    'app/static'),
    # updater.bat: 자동 업데이트 시 본체 종료 후 파일 교체 담당.
    # '.' 는 COLLECT 루트 = dist/도수치료예약/ — 그 루트에 updater.bat 배치.
    ('updater.bat',   '.'),
]
# openpyxl 은 XML/ZIP 관련 리소스 파일이 있어 collect_data_files 로 함께 복사해야
#   실제 .xlsx 파싱 시 누락 에러가 안 남
datas += collect_data_files('openpyxl')

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
