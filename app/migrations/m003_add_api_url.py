"""003 — v1.2.0: sms_settings.api_url 컬럼 + 기본값."""

MIGRATION_ID = 3
DESCRIPTION = "sms_settings.api_url 추가 (문자나라 공식 URL)"

DEFAULT_URL = "https://munjanara.co.kr/send.sys"


def up(conn):
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(sms_settings)").fetchall()]
    if not cols:
        # sms_settings 테이블이 아직 없으면 Base.metadata.create_all 이 나중에 생성
        return
    if "api_url" not in cols:
        cur.execute("ALTER TABLE sms_settings ADD COLUMN api_url VARCHAR(500) DEFAULT ''")
    # 빈 값 / 과거 추정 URL 이면 공식 URL 로 보정
    cur.execute(
        "UPDATE sms_settings SET api_url=? "
        "WHERE api_url IS NULL OR api_url='' "
        "  OR api_url LIKE '%send_mms.php%' "
        "  OR api_url LIKE '%send_sms.php%' "
        "  OR api_url LIKE '%send_lms.php%'",
        (DEFAULT_URL,),
    )
    conn.commit()
