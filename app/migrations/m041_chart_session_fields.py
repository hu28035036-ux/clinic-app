"""041 — 환자 차팅 테이블에 치료시작일 + 회차 컬럼 추가.

용도:
  차트 작성 시 치료 시작일(treatment_start_date)과 회차(session_no)를 선택 입력하기
  위한 컬럼. m040(patient_charts 신설) 이후 추가된 컬럼이므로, 이미 m040 까지 적용된
  기존 DB(개발/운영)에 멱등 ALTER 로 보강한다.

원칙:
  - DROP/DELETE 절대 없음. ADD COLUMN 만.
  - PRAGMA table_info 로 컬럼 존재 확인 후 없을 때만 ADD (두 번 실행해도 안전).
  - create_all 로 새로 만들어진 DB(모델 기준)는 이미 컬럼이 있으므로 모두 skip.
"""

MIGRATION_ID = 41
DESCRIPTION = "patient_charts 에 치료시작일(treatment_start_date) + 회차(session_no) 컬럼 추가"


def up(conn):
    cur = conn.cursor()
    existing = {r[1] for r in cur.execute("PRAGMA table_info(patient_charts)")}

    if "treatment_start_date" not in existing:
        cur.execute(
            "ALTER TABLE patient_charts "
            "ADD COLUMN treatment_start_date VARCHAR(10) DEFAULT ''"
        )
    if "session_no" not in existing:
        cur.execute(
            "ALTER TABLE patient_charts ADD COLUMN session_no INTEGER"
        )

    conn.commit()
