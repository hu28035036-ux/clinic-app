"""seed_dev_dummy.py — 격리된 dev DB 에 더미 데이터 (환자 50 / 치료사 8 / 의사 2) 시드.

사용자가 직접 dev 서버를 띄우기 전에 1회 실행. 운영 DB 절대 미접근.

격리 경로:
  - DB:      tests/temp/dev_clinic.db
  - APPDATA: tests/temp/dev_appdata/

본 스크립트는 환경 변수를 *직접 설정한 후* app.database 를 import → 격리 DB 만 사용.
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent

    # 격리 환경 강제
    tmp_dir = project_root / "tests" / "temp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / "dev_clinic.db"
    appdata = tmp_dir / "dev_appdata"
    appdata.mkdir(exist_ok=True)

    os.environ["DOSU_DB_PATH"] = str(db_path)
    os.environ["APPDATA"] = str(appdata)

    # 프로젝트 루트를 sys.path 에 (app 모듈 import 가능하게)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 안전 검증 — 운영 DB 경로면 즉시 중단
    from app.config import get_db_path
    actual = str(get_db_path())
    if "dev_clinic" not in actual.replace("\\", "/"):
        print(f"[X] 격리 DB 경로 적용 실패. 실제: {actual}", file=sys.stderr)
        return 1
    print(f"[OK] 격리 DB 경로: {actual}")

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.database import SessionLocal, init_db
    from app.models import models

    init_db()  # 마이그레이션 자동
    print("[OK] 마이그레이션 m001~m020 적용")

    random.seed(42)
    db = SessionLocal()
    try:
        # ──────── 의사 2명 ────────
        for name, lic in [("김의사", "LIC-1001"), ("이의사", "LIC-1002")]:
            existing = db.query(models.Doctor).filter_by(license_no=lic).first()
            if not existing:
                db.add(models.Doctor(name=name, specialty="재활의학과", license_no=lic))

        # ──────── 치료사 8명 ────────
        therapist_names = [
            "박치료사", "김치료사", "이치료사", "최치료사",
            "정치료사", "강치료사", "박치료사", "조치료사",  # 박치료사 동명
        ]
        for i, name in enumerate(therapist_names):
            db.add(models.Employee(
                name=name, role="therapist",
                color="#%06x" % random.randint(0, 0xFFFFFF),
                active=True, sort_order=10 + i,
            ))

        db.flush()
        # ──────── 환자 50명 (의도적 동명이인 / 차트번호 / 연락처 중복 일부) ────────
        surnames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '신']
        given = [
            '민준', '서연', '지호', '하은', '도윤', '수아', '시우', '서윤', '준우', '지유',
            '주원', '지민', '건우', '하린', '우진', '수빈', '선우', '예린', '시현', '다은',
            '연우', '채원', '지훈', '시연', '은우', '유진', '준서', '지원', '이안', '윤서',
            '도현', '서현', '승우', '은서', '재윤', '다인', '민재', '채아', '준혁', '수민',
            '지안', '서아', '민서', '예진', '우주', '민지', '하준', '윤하', '진우', '소율',
        ]
        for i in range(50):
            sn = random.choice(surnames)
            gn = given[i % len(given)]
            # 동명이인 시드 (5/15 박환자, 25/35 김환자)
            if i in (5, 15):
                full_name = "박환자"
            elif i in (25, 35):
                full_name = "김환자"
            else:
                full_name = sn + gn
            chart_no = f"{20000 + i}"
            phone = "" if i in (3, 13, 23) else f"010-{2000+i:04d}-{3000+i:04d}"
            year = 1950 + (i % 60)
            birth = f"{year:04d}-01-15"
            db.add(models.Patient(
                name=full_name, chart_no=chart_no,
                birth_date=birth, phone=phone,
            ))

        db.commit()

        # ──────── 치료항목 alias 시드 (m020 테이블 활용) ────────
        from sqlalchemy import text
        manual30 = db.query(models.Treatment).filter_by(code='manual30').first()
        eswt = db.query(models.Treatment).filter_by(code='eswt').first()
        manual60 = db.query(models.Treatment).filter_by(code='manual60').first()
        injection = db.query(models.Treatment).filter_by(code='injection').first()
        alias_pairs = []
        if manual30:
            alias_pairs += [(manual30.id, '도수30'), (manual30.id, '도30')]
        if manual60:
            alias_pairs += [(manual60.id, '도수60'), (manual60.id, '도60')]
        if eswt:
            alias_pairs += [(eswt.id, 'ESWT'), (eswt.id, '체외'), (eswt.id, '충')]
        if injection:
            alias_pairs += [(injection.id, '주사'), (injection.id, '주')]
        for tid, alias in alias_pairs:
            try:
                db.execute(
                    text(
                        'INSERT INTO treatment_aliases (treatment_id, alias_name) '
                        'VALUES (:tid, :alias) ON CONFLICT(treatment_id, alias_name) DO NOTHING'
                    ),
                    {"tid": tid, "alias": alias},
                )
            except Exception:  # noqa: BLE001
                pass
        db.commit()

        counts = {
            "patients": db.query(models.Patient).count(),
            "employees": db.query(models.Employee).count(),
            "doctors": db.query(models.Doctor).count(),
            "treatments": db.query(models.Treatment).count(),
            "aliases_seeded": len(alias_pairs),
        }
        print(json.dumps(counts, ensure_ascii=False, indent=2))
    finally:
        db.close()

    print()
    print("[OK] 시드 완료. 다음 명령으로 dev 서버를 띄워 브라우저에서 확인:")
    print()
    print(f'    set DOSU_DB_PATH={db_path}')
    print(f'    set APPDATA={appdata}')
    print('    venv\\Scripts\\python.exe run.py')
    print()
    print("브라우저: http://localhost:8000")
    print("관리자 비번: admin1234")
    print()
    print("종료: 터미널에서 Ctrl+C 두 번")
    return 0


if __name__ == "__main__":
    sys.exit(main())
