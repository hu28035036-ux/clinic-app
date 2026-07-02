from pydantic import BaseModel


class PatientChartIn(BaseModel):
    """차트 작성/수정 입력 (SOAP 통합 본문). author_id 미지정 시 예약 담당치료사로 폴백."""

    content: str = ""
    treatment_start_date: str = ""   # 치료 시작일 (YYYY-MM-DD, 선택)
    session_no: int | None = None    # 회차 (선택)
    author_id: str = ""
