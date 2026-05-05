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
    'app.routers.ai_harness_router',
    'app.routers.ai_commands_router',
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
    # 19-3 modules.calendar 후보 구조 — 표시용 view-model 순수 helper
    # COMPAT: 기존 app.routers.api 의 _serialize_appointment / _serialize_employee /
    #         _lighten_hex 그대로 동작 (라우터 무수정).
    'app.modules.calendar',
    'app.modules.calendar.view_models',
    # 19-4 modules.appointments 후보 구조 — availability 판정 helper (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 _lunch_window / _check_lunch_block / _check_version
    #         / _bump_version 그대로 동작.
    # 19-9 추가 — appointments 예약 service / repository / rules / schemas 후보 구조 (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 모든 예약 핸들러 (create/update/approve/cancel/
    #         revert/delete/split/assign/list/last/history/manual-history-summary) 그대로 동작.
    # SAFETY: 응답 dict 키 변경 ⊥ — schemas.py 의 contract 상수가 회귀 검출.
    'app.modules.appointments',
    'app.modules.appointments.availability',
    'app.modules.appointments.rules',
    'app.modules.appointments.repository',
    'app.modules.appointments.service',
    'app.modules.appointments.schemas',
    # 19-5 modules.leaves 후보 구조 — 휴무 도메인 규칙 / 조회 / service helper (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 휴무 핸들러 + AI action_leave 흐름 그대로 동작.
    'app.modules.leaves',
    'app.modules.leaves.rules',
    'app.modules.leaves.repository',
    'app.modules.leaves.service',
    # 19-6 modules.treatments 후보 구조 — 치료항목 분류 / 조회 / 직렬화 / 완료체크 (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 치료항목 / 완료체크 / 통계 흐름 그대로 동작.
    # RISK: 시간 가중치 합산 (count_increment 곱셈) 도입 ⊥ — manual60=1 정책 보존.
    'app.modules.treatments',
    'app.modules.treatments.rules',
    'app.modules.treatments.repository',
    'app.modules.treatments.service',
    'app.modules.treatments.completion_rules',
    # 19-7 modules.patients / modules.notes 후보 구조 — 환자·메모 도메인 (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 환자 / 메모 흐름 그대로 동작.
    # SAFETY: PII 마스킹 helper 는 로그 / AI prompt 전용 — 운영 응답 dict 영향 ⊥.
    'app.modules.patients',
    'app.modules.patients.rules',
    'app.modules.patients.repository',
    'app.modules.patients.service',
    'app.modules.notes',
    'app.modules.notes.rules',
    # 19-8 modules.therapists 후보 구조 — 치료사 / 직원 도메인 (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 _serialize_employee / 통계 id→name 매핑 / 도수치료 표 흐름 그대로 동작.
    # NOTE: doctors / medical_staff 전용 모듈은 *후속 검토* — 현재 진료과 / 진료실 / 오더 / 처방 / EMR 기능 부재.
    'app.modules.therapists',
    'app.modules.therapists.rules',
    'app.modules.therapists.repository',
    'app.modules.therapists.service',
    # 19-10 modules.sms 후보 구조 — 문자 / SMS 도메인 (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 SMS 핸들러 (/sms/setting, /sms/templates, /sms/tomorrow-targets, /sms/send) 그대로 동작.
    # SAFETY: provider.FakeSmsProvider 는 외부 호출 ⊥ — 본 모듈 import 만으로 외부 발송 사고 차단. 문자나라 계정 / API key 원문 노출 ⊥.
    'app.modules.sms',
    'app.modules.sms.rules',
    'app.modules.sms.templates',
    'app.modules.sms.service',
    'app.modules.sms.provider',
    'app.modules.sms.schemas',
    # 19-11 modules.stats 후보 구조 — 통계 도메인 (라우터 무수정)
    # COMPAT: 기존 app.routers.api 의 통계 핸들러 (/stats/summary, /stats/by-hour, /stats/by-weekday, /stats/by-treatment, /stats/daily, /stats/aggregate, /stats/by-therapist, /stats/manual-by-therapist, /stats/daily-by-therapist) 그대로 동작.
    # RISK: 시간 가중치 방식 (manual30=1, manual60=2) 회귀 방지 — rules.MANUAL_COUNT_INCREMENT_PER_APPT = 1 가드.
    'app.modules.stats',
    'app.modules.stats.rules',
    'app.modules.stats.repository',
    'app.modules.stats.aggregators',
    'app.modules.stats.service',
    'app.modules.stats.schemas',
    # 19-12 modules.admin / backup / audit / export_import 후보 구조 (라우터 무수정)
    # COMPAT: 기존 app.routers.api / app.routers.ai 의 관리자 / about / config / system-settings /
    #         backup / restore / audit-logs / data-convert 핸들러 그대로 동작.
    # SAFETY: API key / 문자나라 계정 / sync_secret / admin_password_hash 원문 비노출 정책 단일 원천.
    # RISK: 운영 DB 보호 (engine.dispose + atomic rename) 정책 변경 ⊥. audit detail 500자 cap 변경 ⊥.
    'app.modules.admin',
    'app.modules.admin.service',
    'app.modules.admin.schemas',
    'app.modules.backup',
    'app.modules.backup.service',
    'app.modules.backup.schemas',
    'app.modules.audit',
    'app.modules.audit.service',
    'app.modules.audit.schemas',
    'app.modules.export_import',
    'app.modules.export_import.service',
    'app.modules.export_import.schemas',
    # 19-13 modules.ai.commands 후보 구조 — AI commands Preview/Approval/Execute 경계 (라우터 무수정)
    # COMPAT: 기존 app.routers.ai 의 action/parse/preview/execute, sms/{validate,draft}, manual/{search,ask} 그대로 동작.
    # SAFETY: 본 패키지 = byte-equivalent helper 만 — 실제 LLM 호출 ⊥, DB 변경 ⊥, SMS 발송 ⊥.
    # RISK: AI 가 사용자 승인 없이 DB 변경 ⊥ — Preview/Execute 경계 정책 단일 원천. local-first 가드.
    'app.modules.ai',
    'app.modules.ai.commands',
    'app.modules.ai.commands.schemas',
    'app.modules.ai.commands.safety',
    'app.modules.ai.commands.preview',
    'app.modules.ai.commands.executor',
    'app.modules.ai.commands.service',
    'app.modules.ai.commands.adapters',
    # 20-1 그룹 A — F-15 의사 가드 + F-7 privacy retention + F-8 audit retention
    # SAFETY: doctors 도메인 부재 — DB 근거 없는 의사 정보 응답 차단 (post-19-P / F-15).
    # NOTE: 환자 18개월 비활성 마스킹 / AI 로그 6개월 / audit_log 5년 자동 정리 헬퍼.
    'app.modules.ai.safety',
    'app.modules.ai.safety.doctor_guard',
    'app.modules.privacy',
    'app.modules.privacy.retention',
    'app.modules.audit.retention',
    # 20-2 그룹 B — F-13 /api/health + F-12 modules/notes/service + F-14 calendar 회귀
    # NOTE: F-13 = /api/health 신설 (db_ok / migration_version / backup_age /
    # disk_free / version / uptime). F-12 = notes/service.py (Patient/Appointment
    # memo read/write 헬퍼). F-14 = 19-3 view_models.py 회귀 (코드 신설 ⊥).
    'app.modules.health.service',
    'app.modules.health.router',
    'app.modules.notes.service',
    # 20-3-3 F-1 (c) — Doctor 별도 테이블 + /api/doctors CRUD (가벼운 의사만)
    # NOTE: Department / Room / DoctorSchedule / Patient.doctor_id 부재 (사용자 §5-7 (c) 결정)
    # SAFETY: license_no / specialty 응답 노출 — admin 권한 게이트 (require_admin) + audit detail 에 비저장
    'app.modules.doctors',
    'app.modules.doctors.router',
    'app.modules.doctors.service',
    'app.modules.doctors.schemas',
    # 20-3-4 F-2 — 반복 예약 (a) N회만 + (i) 미래만 일괄 + (ii) 충돌 skip
    # NOTE: AppointmentSeries 모델 + Appointment.series_id FK 추가. m017 마이그레이션.
    'app.modules.appointment_series',
    'app.modules.appointment_series.router',
    'app.modules.appointment_series.service',
    'app.modules.appointment_series.schemas',
    # 20-3-5 F-3 — 자원 (치료실 v1, 장비 후속) + Appointment.resource_id FK
    # NOTE: capacity=1 정책 (사용자 §7-7 (i)). F-2 시리즈 + F-3 충돌 통합.
    'app.modules.resources',
    'app.modules.resources.router',
    'app.modules.resources.service',
    'app.modules.resources.schemas',
    # AI 명령 모듈 (Phase 1+) — app/ai/* (예약 도우미 / 휴무 도우미 등)
    # NOTE: 기존 app.services.ai (RAG / SMS draft) 와 분리된 신규 패키지.
    'app.ai',
    'app.ai.ai_command_schema',
    'app.ai.ai_provider',
    'app.ai.ai_audit',
    'app.ai.ai_parser',
    'app.ai.ai_resolver',
    'app.ai.ai_validator',
    'app.ai.ai_preview',
    'app.ai.ai_new_patient_flow',
    'app.ai.ai_executor',
    'app.ai.ai_safety',
    'app.ai.ai_harness',
    'app.ai.ai_appointment_change',
    'app.ai.ai_leave',
    'app.ai.ai_sms_prepare',
    'app.ai.ai_summary',
    'app.ai.ai_ops',
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
