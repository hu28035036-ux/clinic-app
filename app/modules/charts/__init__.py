"""환자 차팅(SOAP 진료기록) 모듈.

치료완료(approved) 예약 1건당 SOAP 기록 1장(1:1). /api/charts/* 라우터 제공.
"""

from .router import router

__all__ = ["router"]
