"""PII 가드 — 외부 LLM 으로 보내기 전 개인정보 차단/치환.

원칙 (CLAUDE.md / 세션 정책):
  외부 전송 금지:
    - 전화번호 / 생년월일 / 차트번호
    - 환자 메모 / 예약 메모
    - 직원 개인정보 (생년월일/전화)
  토큰화 권장:
    - 환자명  →  '환자A', '환자B' (필요 시 매핑 dict 와 함께 전달)
  허용:
    - 치료항목명, 예약 시각(요일/HH:MM), 병원명/병원전화
    - 카운트, 통계 수치 (개인 식별 불가능한 형태)

이 단계에서는 호출 사이트가 아직 없음 — 함수만 정의해 두고
다음 세션 (sms_suggest 등) 에서 import 해서 사용.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


# 차단/탐지 정규식 — 한국 환경 기준
_RE_PHONE_FULL = re.compile(r"\b0\d{1,2}[-\.\s]?\d{3,4}[-\.\s]?\d{4}\b")
_RE_PHONE_DIGITS = re.compile(r"\b0\d{9,10}\b")
_RE_BIRTH_DASH = re.compile(r"\b(19|20)\d{2}[-./](0[1-9]|1[0-2])[-./](0[1-9]|[12]\d|3[01])\b")
_RE_BIRTH_PLAIN = re.compile(r"\b(19|20)\d{6}\b")  # YYYYMMDD
# 차트번호: 숫자 5~10 자리. 너무 일반적이라 길이로만 1차 필터.
_RE_CHART = re.compile(r"\b\d{5,10}\b")

# 한국 주민등록번호 패턴 (혹시 메모에 박혀있을 경우)
_RE_RRN = re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b")


@dataclass
class PiiScanResult:
    found: dict[str, list[str]]   # 종류 → 매치 샘플
    cleaned: str                  # 마스킹된 텍스트

    @property
    def has_blocking(self) -> bool:
        """전송을 차단해야 할 결정적 PII (전화/생년월일/RRN) 가 발견됐는지."""
        for k in ("phone", "birth", "rrn"):
            if self.found.get(k):
                return True
        return False


def scan(text: str) -> PiiScanResult:
    """텍스트에서 PII 패턴 탐지 + 마스킹된 사본 반환.

    탐지만 하고 차단 결정은 호출자 책임 (PiiScanResult.has_blocking).
    """
    if not text:
        return PiiScanResult(found={}, cleaned=text or "")

    found: dict[str, list[str]] = {}
    cleaned = text

    def _scrub(pattern: re.Pattern, kind: str, replacement: str):
        nonlocal cleaned
        matches = pattern.findall(cleaned)
        if matches:
            # findall 반환이 그룹 튜플이면 첫 그룹만 샘플로
            samples = []
            for m in matches[:3]:
                samples.append(m if isinstance(m, str) else (m[0] if m else ""))
            found.setdefault(kind, []).extend(samples)
        cleaned = pattern.sub(replacement, cleaned)

    _scrub(_RE_RRN, "rrn", "[RRN]")
    _scrub(_RE_PHONE_FULL, "phone", "[PHONE]")
    _scrub(_RE_PHONE_DIGITS, "phone", "[PHONE]")
    _scrub(_RE_BIRTH_DASH, "birth", "[BIRTH]")
    _scrub(_RE_BIRTH_PLAIN, "birth", "[BIRTH]")
    _scrub(_RE_CHART, "chart_no_maybe", "[NUM]")

    return PiiScanResult(found=found, cleaned=cleaned)


def tokenize_patient_name(name: str, index: int) -> str:
    """환자명 → '환자A', '환자B' … 같은 토큰. index 는 0부터.

    27 명을 넘으면 '환자AA' 형태로 자릿수 늘림 (단순 구현).
    """
    if index < 0:
        index = 0
    letters = []
    n = index
    while True:
        letters.append(chr(ord("A") + (n % 26)))
        n //= 26
        if n == 0:
            break
        n -= 1
    return "환자" + "".join(reversed(letters))


def build_safe_appointment_context(
    *,
    patient_name_token: str,
    treatment_summary: str,
    reserved_at_label: str,    # 예: "내일(5/1 수) 14:30"
    clinic_name: str = "",
    clinic_phone: str = "",
) -> dict:
    """SMS 추천 등에 사용할 수 있는 '안전' 컨텍스트 구조.

    PII (실명/전화/생년월일/차트/메모) 는 의도적으로 받지 않는다.
    호출자가 토큰화/요약된 값만 넣어야 함.
    """
    return {
        "patient": patient_name_token,
        "treatment": treatment_summary,
        "reserved_at": reserved_at_label,
        "clinic_name": clinic_name,
        "clinic_phone": clinic_phone,
    }


# 차단 결정 진입점 — 호출자(라우터/서비스) 가 외부 LLM 전송 직전에 호출.
def assert_safe_for_external(text: str) -> PiiScanResult:
    """text 에 결정적 PII 있으면 그 사실을 PiiScanResult 로 알린다.

    라우터/서비스 레이어는 이 결과의 has_blocking 이 True 면
    AiPiiBlocked 를 발생시키고 호출을 중단해야 한다.
    """
    return scan(text)
