"""042 — 재고 관리 열(inventory_fields)에 관리자 전용(admin_only) 컬럼 추가.

용도:
  재고 관리 열을 '관리자 전용' 으로 지정하기 위한 플래그. 켜진 칸은 일반 직원이
  값을 입력할 수 없고 관리자 인증(require_admin) 시에만 입력 가능하다. m024(inventory
  신설) 이후 추가된 컬럼이므로, 이미 적용된 기존 DB(개발/운영)에 멱등 ALTER 로 보강.

원칙:
  - DROP/DELETE 절대 없음. ADD COLUMN 만.
  - PRAGMA table_info 로 컬럼 존재 확인 후 없을 때만 ADD (두 번 실행해도 안전).
  - create_all 로 새로 만들어진 DB(모델 기준)는 이미 컬럼이 있으므로 skip.
"""

MIGRATION_ID = 42
DESCRIPTION = "inventory_fields 에 관리자 전용(admin_only) 컬럼 추가"


def up(conn):
    cur = conn.cursor()
    existing = {r[1] for r in cur.execute("PRAGMA table_info(inventory_fields)")}

    if "admin_only" not in existing:
        cur.execute(
            "ALTER TABLE inventory_fields ADD COLUMN admin_only BOOLEAN DEFAULT 0"
        )

    conn.commit()
