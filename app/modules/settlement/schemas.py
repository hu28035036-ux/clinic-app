from typing import List

from pydantic import BaseModel, Field


class SettlementGridEntry(BaseModel):
    performed_on: str
    employee_id: str
    treatment_id: str
    quantity: int = 0
    memo: str = ""


class SettlementGridIn(BaseModel):
    date_from: str
    date_to: str
    category_id: str = ""
    entries: List[SettlementGridEntry] = Field(default_factory=list)
    # True: 정산 탭 조회 시 집계를 자동 반영하는 호출 — 감사/동기화 로그를 생략한다.
    # (조회할 때마다 audit_logs/sync_ops 가 수십~수백 건 쌓이는 것을 막기 위함.
    #  정산 스냅샷은 집계의 단방향 파생이라 원본 예약/기록/manual 로그로 추적 충분.)
    silent: bool = False
