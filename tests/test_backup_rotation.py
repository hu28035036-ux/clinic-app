"""백업 목록 정렬 + 보관 개수 정리 회귀 테스트.

배경 버그 (2026-06-11 수정):
  1. ``list_backups`` 가 **파일명 문자열 정렬** 로 "최신" 을 판정 —
     ``clinic_before_*`` 스냅샷이 'b' > 숫자 정렬 때문에 날짜형 백업보다
     항상 위로 와서, ``restore_latest`` ("가장 최근 백업으로 복원" 버튼) 가
     수개월 전 before_update 스냅샷을 복원할 수 있었음 (데이터 소실).
  2. ``_enforce_keep_limit`` 가 단일 그룹 + 파일명 정렬이라:
     - 스냅샷은 영원히 삭제되지 않고 무한 누적 (디스크)
     - 스냅샷 개수 ≥ keep 이 되면 일반 자동백업이 생성 직후 즉시 삭제
       (자동백업 무력화)

수정 후 정책:
  - ``list_backups`` : mtime(수정시각) 기준 최신순.
  - ``_enforce_keep_limit`` : 일반(clinic_<ts>) / 스냅샷(clinic_before_*)
    그룹을 분리해 각각 keep 개수 적용, mtime 기준 오래된 것부터 삭제.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta

import app.services.backup as backup_mod
import app.services.sync as sync_mod


def _touch(d, name: str, *, age_days: float) -> None:
    """age_days 전 mtime 을 가진 더미 백업 파일 생성."""
    p = d / name
    p.write_bytes(b"dummy")
    ts = time.time() - age_days * 86400
    os.utime(p, (ts, ts))


def _make_backup_dir(tmp_path, monkeypatch):
    d = tmp_path / "backups"
    d.mkdir()
    monkeypatch.setattr(backup_mod, "get_backup_dir", lambda: d)
    return d


# ──────────────────────── list_backups 정렬 ────────────────────────


def test_list_backups_sorted_by_mtime_not_filename(tmp_path, monkeypatch):
    """before_* 스냅샷이 있어도 mtime 이 진짜 최신인 파일이 맨 위."""
    d = _make_backup_dir(tmp_path, monkeypatch)
    # 파일명 정렬로는 before_update(v1.3.9) > before_update(v1.3.22) > 날짜형 순서가 됨
    _touch(d, "clinic_before_update_v1.3.9_20260501_120000.db", age_days=40)
    _touch(d, "clinic_before_update_v1.3.22_20260610_130000.db", age_days=1)
    _touch(d, "clinic_before_restore_20260520_100000.db", age_days=22)
    _touch(d, "clinic_20260609_090000.db", age_days=2)
    _touch(d, "clinic_20260611_090000.db", age_days=0)  # 진짜 최신

    rows = backup_mod.list_backups()
    names = [r["name"] for r in rows]
    assert names[0] == "clinic_20260611_090000.db"
    # 전체가 mtime 내림차순
    mtimes = [r["mtime"] for r in rows]
    assert mtimes == sorted(mtimes, reverse=True)


def test_list_backups_row_keys_unchanged(tmp_path, monkeypatch):
    """COMPAT: 응답 row key 4개 (name/path/size/mtime) 계약 유지."""
    from app.modules.backup.schemas import BACKUP_LIST_ROW_KEYS

    d = _make_backup_dir(tmp_path, monkeypatch)
    _touch(d, "clinic_20260611_090000.db", age_days=0)
    rows = backup_mod.list_backups()
    assert len(rows) == 1
    assert set(rows[0].keys()) == BACKUP_LIST_ROW_KEYS


def test_restore_latest_targets_true_latest(tmp_path, monkeypatch):
    """restore_latest 가 옛 스냅샷이 아닌 mtime 최신 파일을 대상으로 삼는다.

    실제 복원(파일 교체) 까지 가지 않도록 shutil.copy2 를 가로채 대상만 기록.
    """
    d = _make_backup_dir(tmp_path, monkeypatch)
    _touch(d, "clinic_before_update_v1.3.9_20260501_120000.db", age_days=40)
    _touch(d, "clinic_20260611_090000.db", age_days=0)

    copied = {}

    def _fake_copy2(src, dst):
        copied["src"] = str(src)
        copied["dst"] = str(dst)

    # 안전망 백업(sqlite_safe_copy) / 워커 정지 / 엔진 dispose 는 그대로 둬도
    # 테스트 격리 DB 에서 무해 — 파일 교체만 가로챈다.
    monkeypatch.setattr(backup_mod.shutil, "copy2", _fake_copy2)
    result = backup_mod.restore_latest()
    assert result["ok"] is True
    assert result["restored_from"] == "clinic_20260611_090000.db"
    assert copied["src"].endswith("clinic_20260611_090000.db")


# ──────────────────────── _enforce_keep_limit 그룹 분리 ────────────────────────


def test_keep_limit_deletes_oldest_regular_backups(tmp_path, monkeypatch):
    """일반 백업은 keep 초과분을 오래된 것(mtime)부터 삭제."""
    d = _make_backup_dir(tmp_path, monkeypatch)
    for i in range(5):
        _touch(d, f"clinic_2026060{i+1}_090000.db", age_days=10 - i)

    backup_mod._enforce_keep_limit(keep=3)
    remaining = sorted(p.name for p in d.glob("*.db"))
    assert remaining == [
        "clinic_20260603_090000.db",
        "clinic_20260604_090000.db",
        "clinic_20260605_090000.db",
    ]


def test_keep_limit_prunes_safety_snapshots_separately(tmp_path, monkeypatch):
    """스냅샷(clinic_before_*)도 자체 그룹으로 keep 적용 — 무한 누적 방지."""
    d = _make_backup_dir(tmp_path, monkeypatch)
    for i in range(5):
        _touch(d, f"clinic_before_update_v1.3.{i}_20260601_12000{i}.db",
               age_days=20 - i)

    backup_mod._enforce_keep_limit(keep=2)
    remaining = sorted(p.name for p in d.glob("*.db"))
    assert remaining == [
        "clinic_before_update_v1.3.3_20260601_120003.db",
        "clinic_before_update_v1.3.4_20260601_120004.db",
    ]


def test_keep_limit_snapshots_do_not_crowd_out_regular(tmp_path, monkeypatch):
    """핵심 회귀: 스냅샷이 keep 개수를 다 차지해도 일반 백업은 살아남는다.

    이전 코드는 스냅샷 ≥ keep 이면 일반 백업(정렬상 앞쪽)이 전부 삭제돼
    자동백업이 무력화됐음.
    """
    d = _make_backup_dir(tmp_path, monkeypatch)
    for i in range(4):  # 스냅샷 4개 (keep=3 초과)
        _touch(d, f"clinic_before_update_v1.3.{i}_20260601_12000{i}.db",
               age_days=30 - i)
    _touch(d, "clinic_20260611_090000.db", age_days=0)  # 오늘의 자동백업

    backup_mod._enforce_keep_limit(keep=3)
    remaining = sorted(p.name for p in d.glob("*.db"))
    # 일반 백업 생존 + 스냅샷은 오래된 1개만 삭제
    assert "clinic_20260611_090000.db" in remaining
    assert len([n for n in remaining if n.startswith("clinic_before_")]) == 3


# ──────────────────────── 일일 유지보수 (audit retention 연결) ────────────────────────


def test_daily_maintenance_prunes_old_audit_logs():
    """run_daily_maintenance 가 5년 지난 audit_log 를 정리한다 (F-8 자동 트리거)."""
    from app.database import SessionLocal
    from app.models import models as _m

    db = SessionLocal()
    try:
        old = _m.AuditLog(
            ts=datetime.utcnow() - timedelta(days=6 * 365),
            actor="test", action="test_rotation.old", detail="old",
        )
        recent = _m.AuditLog(
            ts=datetime.utcnow() - timedelta(days=1),
            actor="test", action="test_rotation.recent", detail="recent",
        )
        db.add_all([old, recent])
        db.commit()
        old_id, recent_id = old.id, recent.id
    finally:
        db.close()

    sync_mod.run_daily_maintenance()

    db = SessionLocal()
    try:
        assert db.query(_m.AuditLog).filter_by(id=old_id).first() is None
        assert db.query(_m.AuditLog).filter_by(id=recent_id).first() is not None
    finally:
        db.close()
