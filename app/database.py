"""SQLAlchemy 엔진 / 세션 + 증분 마이그레이션.

v1.2.2 부터:
  - DB 파일 삭제 로직(_reset_database) 제거 → 데이터 절대 안 날아감
  - app.migrations 모듈의 증분 마이그레이션이 스키마 변경 관리
  - SCHEMA_VERSION 상수는 참고용 (실제 판정은 schema_migrations 테이블이 담당)

이전 버전(_reset_database) 로직은 더 이상 호출되지 않지만
코드는 보존 (응급 상황 시 수동 호출 가능).
"""
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_db_path, get_appdata_dir

# 스키마 버전 — 참고용 (v1.2.2 부터는 실제 판정에 쓰이지 않음).
# 과거 파일 schema_version.txt 는 호환을 위해 계속 읽고 씀.
SCHEMA_VERSION = 6

DB_URL = f"sqlite:///{get_db_path()}"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _schema_version_file() -> Path:
    return get_appdata_dir() / "schema_version.txt"


def _read_schema_version() -> int:
    p = _schema_version_file()
    if not p.exists():
        return 0
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except Exception:
        return 0


def _write_schema_version(v: int):
    try:
        _schema_version_file().write_text(str(v), encoding="utf-8")
    except Exception:
        pass


def _reset_database():
    """[⚠ 위험] DB 파일 삭제. v1.2.2 부터는 자동 호출되지 않음.
    수동 복구가 필요한 극한 상황에서만 사용.
    """
    global engine, SessionLocal
    try:
        engine.dispose()
    except Exception:
        pass
    db_path = Path(get_db_path())
    if db_path.exists():
        db_path.unlink()
    engine = create_engine(
        DB_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    SessionLocal.configure(bind=engine)


def _legacy_migrate_add_columns():
    """v1.2.1 이전 방식의 ALTER TABLE 들 — 이제 마이그레이션 001~004 가 담당.

    하위 호환을 위해 보존. 중복 실행돼도 IF NOT EXISTS / 컬럼 체크로 안전.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        # employees.sort_order
        cols = [r[1] for r in cur.execute("PRAGMA table_info(employees)").fetchall()]
        if cols and "sort_order" not in cols:
            cur.execute("ALTER TABLE employees ADD COLUMN sort_order INTEGER DEFAULT 0")
            rows = cur.execute(
                "SELECT id FROM employees ORDER BY role, name"
            ).fetchall()
            for idx, (eid,) in enumerate(rows):
                cur.execute(
                    "UPDATE employees SET sort_order=? WHERE id=?", (idx + 1, eid)
                )
        # appointments.version
        appt_cols = [r[1] for r in cur.execute("PRAGMA table_info(appointments)").fetchall()]
        if appt_cols and "version" not in appt_cols:
            cur.execute("ALTER TABLE appointments ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    finally:
        conn.close()


def _run_migrations():
    """app.migrations 의 증분 마이그레이션 실행."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        from . import migrations as _m
        _m.run_all(conn)
    finally:
        conn.close()


def init_db():
    """v1.2.2 초기화 흐름:
      1. 엔진 + 모델 기반 테이블 생성 (없는 것만 만듦 · create_all)
      2. 레거시 ALTER TABLE 보정 (v1.2.0 이전 호환)
      3. 증분 마이그레이션 실행 (앞으로 모든 스키마 변경)
      4. 시드 데이터 투입
    """
    # ⚠ v1.2.2 부터 '스키마 버전 다름 → DB 삭제' 로직은 제거됨.
    # 아래 한 줄을 호출하지 않음으로써 환자 데이터 영구 보존 보장.
    #   if current != SCHEMA_VERSION: _reset_database()  ← 삭제됨

    Base.metadata.create_all(bind=engine)
    _legacy_migrate_add_columns()
    _run_migrations()

    # 시드
    from .services.seed import seed_defaults
    db = SessionLocal()
    try:
        seed_defaults(db)
        db.commit()
    finally:
        db.close()

    # 참고용 스키마 버전 기록 (호환)
    _write_schema_version(SCHEMA_VERSION)
