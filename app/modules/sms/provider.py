"""modules.sms.provider — 외부 발송 provider 인터페이스 + Fake / NotConfigured 구현 (19-10 신규).

본 모듈은 외부 SMS 발송 서비스 (문자나라 등) 의 *추상 인터페이스* 와 *테스트 / dev
용 Fake 구현* 을 정의한다. **실제 외부 호출 ⊥ — 본 19-10 시점**.

19-10 본 세션 범위:
  - ``SmsProvider`` Protocol (Python typing.Protocol) — caller 가 의존하는 인터페이스.
  - ``FakeSmsProvider`` — *테스트 / dev 안전 fallback* (외부 호출 ⊥, 기록만).
  - ``NotConfiguredProvider`` — SMS 설정 미완료 시 사용 (호출 시 *명시적 거부*).
  - ``ProviderResult`` dataclass — 발송 결과 (status_code / kind / detail / vendor 응답).
  - 라우터 무수정 — 운영 외부 발송은 라우터의 기존 ``urllib.request`` 흐름이 담당.

# COMPAT: 본 모듈은 *helper / 인터페이스* 만 — 라우터 미채택. 19-12+ 시점에
#         라우터의 ``sms_send`` 가 본 ``SmsProvider`` 를 채택해 테스트 격리 +
#         실제 발송이 같은 인터페이스 공유하는 구조 후보.

# SAFETY: ``FakeSmsProvider`` 는 *외부 HTTP 호출 ⊥* — ``send`` 호출 시 기록만 하고
#         성공으로 가장된 합성 결과 반환. 테스트 환경에서 *실제 발송 사고 차단*.
#         ``NotConfiguredProvider`` 는 명시적 거부 (호출 시 ``ProviderNotConfiguredError``).
#         본 모듈 *import 만으로 외부 API 호출 ⊥* — ``urllib`` / ``requests`` /
#         ``httpx`` 미참조.

# NOTE: 실제 운영 발송은 라우터의 ``sms_send`` 인라인 ``urllib.request`` 가 담당
#       (api.py:3225~3445). 본 19-10 가 *대체 ⊥* — 본체 흐름 보존. 19-12+ 시점에
#       ``MunjanaraProvider`` 를 추가해 라우터가 본 인터페이스를 채택할 후보.

# RISK: ``SmsProvider`` 는 Protocol — 런타임 검증은 mypy / pyright 정적 검사. 본
#       모듈 자체는 *실행 시 isinstance 검사 ⊥* (Protocol 의 한계). 호출자가
#       ``send`` 메서드 시그니처 정합을 보장.

# TODO(19-12): 라우터 ``sms_send`` 가 ``provider.SmsProvider.send(...)`` 호출로
#              전환 — 그 시점에 ``MunjanaraProvider`` (실제 외부 발송) 추가.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


# ─── 발송 결과 dataclass ──────────────────────────────────────────────────────


@dataclass
class ProviderResult:
    """외부 발송 결과 (provider 응답).

    COMPAT: ``api.py:sms_send`` (line 3425~3426 / 3353~3354 / 3365~3367 등) 의
    ``results.append({...})`` dict literal 과 의미 정합. 본 dataclass 는 *type
    안전 컨테이너* — 라우터 응답으로 변환 시 ``to_dict()`` 호출.

    필드:
      ``phone``       : 수신 번호 (마스킹 ⊥ — 응답 dict 에 평문 포함, 기존 동작 정합).
      ``result``      : ``"success"`` / ``"fail"``.
      ``kind``        : 분류 코드 (``"ok"`` / ``"precheck"`` / ``"http_error"`` /
                        ``"network_error"`` / ``"rejected_by_vendor"`` / ``"exception"`` /
                        ``"unknown"`` / ``"not_configured"`` 등).
      ``status_code`` : HTTP status code (옵션).
      ``detail``      : 사용자 노출 detail 문자열 (마스킹 적용된 상태).
    """

    phone: str
    result: str
    kind: str
    status_code: int | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """라우터 응답 dict 변환.

        COMPAT: ``api.py:sms_send`` (line 3425~3426) 의 dict literal 정합. ``status_code``
        가 None 이면 dict 에 포함 ⊥ (api.py 정합 — precheck / network_error 분기).
        """
        out: dict[str, Any] = {
            "phone": self.phone,
            "result": self.result,
            "kind": self.kind,
            "detail": self.detail,
        }
        if self.status_code is not None:
            out["status_code"] = self.status_code
        return out


# ─── Provider 추상 인터페이스 ─────────────────────────────────────────────────


class SmsProvider(Protocol):
    """외부 SMS 발송 provider Protocol.

    구현체 (``FakeSmsProvider`` / ``NotConfiguredProvider`` / 향후 ``MunjanaraProvider``) 는
    동일한 ``send`` 시그니처를 만족해야 한다.

    NOTE: Protocol — 런타임 ``isinstance`` 검사 ⊥. 호출자 / 구현체 정적 검사로 정합 보장.
    """

    def send(
        self,
        *,
        items: list[dict[str, Any]],
        settings: Any,
    ) -> list[ProviderResult]:
        """외부 SMS 발송 — 인자별 결과 리스트 반환.

        인자:
          ``items``    : 발송 대상 dict 리스트 (각 dict 는 ``phone / body / patient_id`` 키).
          ``settings`` : SMS 설정 (``SmsSetting`` ORM-like — 호출자 주입).

        반환: 각 ``items`` 항목에 대응하는 ``ProviderResult`` 리스트.
        """
        ...


# ─── 명시적 거부 예외 ────────────────────────────────────────────────────────


class ProviderNotConfiguredError(Exception):
    """SMS 설정 미완료 시 발송 시도 → 명시적 거부.

    NOTE: 라우터 채택 시 ``HTTPException(400, ...)`` 으로 변환.
    """


class ProviderExternalCallProhibitedError(Exception):
    """본 19-10 환경에서 *실제 외부 호출* 이 시도되면 raise.

    SAFETY: 테스트 / dev 안전 가드 — ``FakeSmsProvider`` 가 외부 호출을 시도하면
    실수 / 코드 회귀 신호. 본 19-10 모듈은 *외부 API 호출 ⊥* 보장.
    """


# ─── FakeSmsProvider — 테스트 / dev 용 ────────────────────────────────────────


class FakeSmsProvider:
    """*외부 호출 ⊥* — 발송 시도를 ``calls`` 에 기록만 하고 합성 성공 결과 반환.

    SAFETY: 본 provider 는 *실제 발송 ⊥* — ``urllib`` / ``requests`` / ``httpx``
    미사용. 테스트 환경 / dev 환경에서 SMS 발송 흐름을 *외부 호출 없이* 검증.

    NOTE: ``calls`` 리스트로 호출 인자 검증 가능 — caller 가 ``provider.calls`` 로
    접근. 19-12+ 라우터 채택 시점에 *테스트 격리* 를 보장하는 핵심 장치.
    """

    def __init__(self, *, default_kind: str = "ok") -> None:
        self.calls: list[dict[str, Any]] = []
        self.default_kind = default_kind

    def send(
        self,
        *,
        items: list[dict[str, Any]],
        settings: Any,
    ) -> list[ProviderResult]:
        """기록만 하고 합성 성공 결과 반환 — 외부 호출 ⊥.

        SAFETY: 본 메서드는 *외부 HTTP 호출 ⊥* — 항상 in-memory 합성 응답.
        실수로 외부 호출을 시도하는 경로가 추가되면 ``ProviderExternalCallProhibitedError``
        를 명시적으로 raise (현재 구현은 외부 호출 *경로 자체가 부재*).
        """
        self.calls.append({
            "items": list(items),
            "settings_id": getattr(settings, "id", None),
        })
        results: list[ProviderResult] = []
        for it in items or []:
            phone = (it.get("phone") or "").strip()
            results.append(
                ProviderResult(
                    phone=phone,
                    result="success",
                    kind=self.default_kind,
                    status_code=200,
                    detail="fake_provider_synthetic_success",
                )
            )
        return results


# ─── NotConfiguredProvider — 설정 미완료 fallback ────────────────────────────


@dataclass
class NotConfiguredProvider:
    """SMS 설정이 미완료된 환경에서 사용 — 호출 시 명시적 거부.

    NOTE: 라우터 채택 시 ``provider.send(...)`` 호출 전에 설정 검사를 라우터가
    수행하지만, *방어적* 으로 본 fallback 도입. 기본 fixture 에서 SMS 설정이 비어
    있어도 *외부 호출 ⊥* 를 보장.
    """

    missing: list[str] = field(default_factory=list)

    def send(
        self,
        *,
        items: list[dict[str, Any]],
        settings: Any,
    ) -> list[ProviderResult]:
        """모든 항목을 ``not_configured`` 로 fail 처리.

        SAFETY: 외부 호출 ⊥. 발송 시도 시도 자체를 거부.
        """
        from app.modules.sms import service as _service

        message = _service.build_missing_setting_message(self.missing or ["설정 미완료"])
        return [
            ProviderResult(
                phone=(it.get("phone") or "").strip(),
                result="fail",
                kind="not_configured",
                status_code=None,
                detail=message,
            )
            for it in (items or [])
        ]


__all__ = [
    "ProviderResult",
    "SmsProvider",
    "ProviderNotConfiguredError",
    "ProviderExternalCallProhibitedError",
    "FakeSmsProvider",
    "NotConfiguredProvider",
]
