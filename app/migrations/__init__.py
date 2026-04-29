"""증분 스키마 마이그레이션 — 데이터 영구 보존 보장.

설계 원칙:
  1. 각 마이그레이션은 고유한 MIGRATION_ID (정수, 증가) 와 up(conn) 함수를 가짐
  2. 실행된 마이그레이션은 schema_migrations 테이블에 기록됨
  3. 이미 실행된 것은 건너뜀 (멱등성)
  4. 각 up() 함수는 IF NOT EXISTS / 컬럼 체크 등으로 **두 번 실행돼도 안전**
  5. DROP / DELETE / TRUNCATE 금지 → 데이터 절대 안 날아감

새 마이그레이션 추가 방법:
  1. migrations/NNN_설명.py 파일 생성
  2. MIGRATION_ID = NNN (다음 번호), DESCRIPTION = "..." 정의
  3. def up(conn): 안에서 cur.execute("ALTER ... IF NOT EXISTS")
  4. 기존 마이그레이션 수정 금지 (한 번 배포된 것은 절대 변경 X)
"""
import importlib
import sys

APPLIED_TABLE = "schema_migrations"


def run_all(conn):
    """등록된 모든 마이그레이션 중 아직 적용 안 된 것만 순서대로 실행."""
    _ensure_tracking_table(conn)
    applied = _get_applied(conn)
    modules = _list_migrations()
    if not modules:
        return
    pending = [m for m in modules if m["id"] not in applied]
    if not pending:
        _log("모든 마이그레이션 적용됨 (변경사항 없음)")
        return
    _log(f"적용 대상: {[m['id'] for m in pending]}")
    for m in pending:
        try:
            _log(f"→ {m['id']:03d}  {m['description']}")
            m["up"](conn)
            _mark_applied(conn, m["id"], m["description"])
        except Exception as e:
            _log(f"❌ {m['id']:03d} 실패: {e}")
            raise
    _log("마이그레이션 완료")


def _log(msg):
    try:
        print(f"[MIGRATE] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _ensure_tracking_table(conn):
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {APPLIED_TABLE} (
            id          INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _get_applied(conn) -> set:
    try:
        rows = conn.cursor().execute(
            f"SELECT id FROM {APPLIED_TABLE}"
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def _mark_applied(conn, mid: int, description: str):
    cur = conn.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {APPLIED_TABLE} (id, description) VALUES (?, ?)",
        (mid, description),
    )
    conn.commit()


def _list_migrations():
    """migrations/ 안의 NNN_*.py 를 import 순서대로 반환."""
    import pkgutil
    from pathlib import Path
    pkg_path = Path(__file__).parent
    mods = []
    # pkgutil 은 PyInstaller 환경에서 제대로 동작하지 않을 수 있어
    # 파일 시스템 탐색 + importlib 직접 호출이 더 안전
    names = []
    # 파일명 패턴: m001_설명.py  (숫자 시작 불가한 파이썬 규칙 준수)
    try:
        for p in sorted(pkg_path.glob("m[0-9][0-9][0-9]_*.py")):
            names.append(p.stem)
    except Exception:
        names = []

    # PyInstaller / frozen 환경 — pkgutil.iter_modules 로도 시도
    if not names:
        try:
            for finder, name, ispkg in pkgutil.iter_modules([str(pkg_path)]):
                if name.startswith("m") and len(name) > 4 and name[1:4].isdigit() and name[4:5] == "_":
                    names.append(name)
            names.sort()
        except Exception:
            pass

    for name in names:
        try:
            mod = importlib.import_module(f"app.migrations.{name}")
            mid = getattr(mod, "MIGRATION_ID", None)
            desc = getattr(mod, "DESCRIPTION", name)
            up = getattr(mod, "up", None)
            if mid is None or up is None:
                continue
            mods.append({"id": int(mid), "description": desc, "up": up, "module": name})
        except Exception as e:
            _log(f"모듈 로드 실패 {name}: {e}")
    mods.sort(key=lambda x: x["id"])
    return mods
