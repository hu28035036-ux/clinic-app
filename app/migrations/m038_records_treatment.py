"""038 — 기록 탭을 치료항목 기반으로 전환 + 집계 자동화 기반.

배경:
  - 기록(record) 탭이 메뉴얼/C-Arm/리뷰이벤트 3개로 하드코딩되어 있었음.
  - 이를 치료항목(Treatment)에 'requires_record' 플래그를 켠 항목으로 동적
    구성하도록 바꾼다. 기록필요 항목의 직원별 건수는 집계에 자동 반영된다.

변경:
  1. treatments.requires_record (INTEGER NOT NULL DEFAULT 0) 추가.
  2. record_entries.treatment_id (TEXT NULL) + 인덱스 추가.
  3. (1회성, 비파괴) 기존 고정 기록 탭(record_tab_settings)을 그대로 보존하기
     위해, 각 탭에 대응하는 '기록 필요' 치료항목을 생성하고 기존 record_entries
     의 tab_key 를 새 treatment_id 로 백필한다.
     → 업그레이드 직후에도 기존 기록 탭/데이터가 그대로 보인다. 사용자가
       이후 이름/인센티브 조정 또는 불필요 항목 삭제·병합.

원칙 (다른 마이그레이션과 동일):
  - DROP/DELETE/TRUNCATE 없음 — 데이터 절대 안 건드림.
  - 컬럼 존재 체크 / IF NOT EXISTS — 두 번 실행돼도 안전.
"""
import uuid
from datetime import datetime

MIGRATION_ID = 38
DESCRIPTION = "기록 탭 치료항목화 (treatments.requires_record + record_entries.treatment_id + 레거시 백필)"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _unique_short(base: str, used: set[str]) -> str:
    base = (base or "").strip()[:10] or "기록"
    if base not in used:
        return base
    for i in range(2, 100):
        cand = f"{base[:8]}{i}"
        if cand not in used:
            return cand
    return uuid.uuid4().hex[:10]


def _default_category_id(cur) -> str | None:
    if not _table_exists(cur, "employee_categories"):
        return None
    # default_can_manual 우선, 없으면 sort_order 가장 앞 활성 과
    try:
        row = cur.execute(
            "SELECT id FROM employee_categories WHERE active=1 "
            "ORDER BY default_can_manual DESC, sort_order, name LIMIT 1"
        ).fetchone()
    except Exception:
        row = cur.execute(
            "SELECT id FROM employee_categories ORDER BY sort_order LIMIT 1"
        ).fetchone()
    return row[0] if row else None


def up(conn):
    cur = conn.cursor()

    # 1. treatments.requires_record
    if _table_exists(cur, "treatments"):
        if "requires_record" not in _columns(cur, "treatments"):
            cur.execute(
                "ALTER TABLE treatments "
                "ADD COLUMN requires_record INTEGER NOT NULL DEFAULT 0"
            )

    # 2. record_entries.treatment_id
    if _table_exists(cur, "record_entries"):
        if "treatment_id" not in _columns(cur, "record_entries"):
            cur.execute("ALTER TABLE record_entries ADD COLUMN treatment_id TEXT")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_record_entries_treatment_id "
            "ON record_entries(treatment_id)"
        )

    # 3. 레거시 기록 탭 → 기록필요 치료항목 생성 + 백필 (마이그레이션은 1회만 실행)
    if _table_exists(cur, "treatments") and _table_exists(cur, "record_tab_settings"):
        used_codes = {r[0] for r in cur.execute("SELECT code FROM treatments").fetchall()}
        used_shorts = {r[0] for r in cur.execute("SELECT short FROM treatments").fetchall()}
        base_sort_row = cur.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM treatments"
        ).fetchone()
        base_sort = int(base_sort_row[0] or 0)
        default_cat = _default_category_id(cur)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        tabs = cur.execute(
            "SELECT tab_key, label, category_id, sort_order "
            "FROM record_tab_settings ORDER BY sort_order, tab_key"
        ).fetchall()
        for i, (tab_key, label, category_id, sort_order) in enumerate(tabs):
            rec_code = f"rec_{tab_key}"[:40]
            label_s = (label or tab_key).strip()
            target_code = rec_code
            # 0) 이미 마이그레이션됨(rec_ 코드 존재) → 그 항목 재사용 (멱등).
            existing_rec = cur.execute(
                "SELECT id FROM treatments WHERE code=?", (rec_code,)
            ).fetchone()
            if existing_rec:
                tid = existing_rec[0]
            else:
                # 1) 같은 이름의 '활성' 치료항목이 이미 있으면 재사용 — 중복 생성 방지.
                #    그 항목에 '기록 필요'를 켜고 기록을 거기에 연결한다.
                reuse = cur.execute(
                    "SELECT id, code FROM treatments WHERE name=? AND active=1 "
                    "ORDER BY sort_order, code LIMIT 1",
                    (label_s,),
                ).fetchone()
                if reuse:
                    tid, target_code = reuse[0], reuse[1]
                    cur.execute(
                        "UPDATE treatments SET requires_record=1 WHERE id=?", (tid,)
                    )
                else:
                    # 2) 없으면 기록용 치료항목을 새로 생성.
                    tid = uuid.uuid4().hex
                    target_code = rec_code
                    short = _unique_short(label_s, used_shorts)
                    used_shorts.add(short)
                    used_codes.add(rec_code)
                    cat = (category_id or "").strip() or default_cat
                    cur.execute(
                        "INSERT INTO treatments "
                        "(id, code, name, category_id, short, default_minutes, role, "
                        " count_increment, show_in_patient, active, sort_order, price, "
                        " requires_record, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            tid, rec_code, label_s[:50], cat, short, 30,
                            "therapist", 1, 0, 1, base_sort + 100 + i, 0,
                            1, now, now,
                        ),
                    )
            # 기존 기록 항목 백필 — treatment_id 연결 + tab_key 를 대상 치료항목 code 로 통일.
            # (집계/카운트는 tab_key(=code) 기준으로 묶이므로 일관성 필요)
            cur.execute(
                "UPDATE record_entries SET treatment_id=?, tab_key=? "
                "WHERE tab_key=? AND (treatment_id IS NULL OR treatment_id='')",
                (tid, target_code, tab_key),
            )

    conn.commit()
