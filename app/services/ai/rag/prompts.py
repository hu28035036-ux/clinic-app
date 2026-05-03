"""RAG 프롬프트 템플릿 — 18-1 골격 + 버전 관리.

원칙 (``docs/ai_rag_architecture_plan.md`` §16):
  - 프롬프트 변경은 새 버전 추가 (기존 버전 삭제 금지) → A/B 비교 가능.
  - 응답/로그에 ``prompt_version`` 기록.

18-1 시점에는 현행 ``manual_qa._MANUAL_SYSTEM_PROMPT`` (``manual_qa.py:33-45``)
를 ``manual_qa.system`` 의 ``v1`` 로 고정한다. 실제 사용 (라우터/pipeline 에
주입) 은 18-2 이후.
"""
from __future__ import annotations

# manual_qa.py:33-45 의 시스템 프롬프트와 1:1 (v1.3.3 동작 보존).
# 본 문자열을 manual_qa.py 가 재사용하지는 않는다 (18-1 범위 외).
_MANUAL_QA_SYSTEM_V1 = (
    "당신은 한국 도수치료 클리닉 직원의 업무 매뉴얼 어시스턴트입니다.\n"
    "아래 '매뉴얼 발췌' 안에 있는 내용에만 근거해서 한국어로 간결하게 답하세요.\n"
    "매뉴얼 발췌에 없는 내용은 추측하거나 만들어내지 말고 "
    "'매뉴얼에서 답을 찾지 못했습니다.' 라고만 답하세요.\n"
    "출처 문서에 없는 기능명, 버튼명, API endpoint, 설정값을 만들지 마세요.\n"
    "의료 진단/치료효과/완치 같은 의료 판단을 하지 마세요.\n"
    "AI 가 직접 문자 발송하거나 DB 를 수정할 수 없다는 점을 사실대로 알리세요.\n"
    "이 시스템 외부 주제(주식/날씨/일반상식 등)는 "
    "'업무 매뉴얼 범위를 벗어납니다' 로만 답하세요.\n"
    "환자 이름·전화번호·생년월일·차트번호·환자 메모는 절대 만들어내지 마세요.\n"
    "답변은 단계가 있으면 번호 목록으로 정리하고, 마지막에 사용한 매뉴얼 파일명을 한 줄로 표시하세요."
)


PROMPTS: dict[str, dict[str, str]] = {
    "manual_qa.system": {
        "v1": _MANUAL_QA_SYSTEM_V1,
    },
    # 신규 prompt 가 도입되면 본 dict 에 추가. 기존 항목 삭제 금지.
}

# 현재 라우터/pipeline 이 기본으로 사용해야 할 버전 매핑.
DEFAULT_VERSIONS: dict[str, str] = {
    "manual_qa.system": "v1",
}


def get_prompt(name: str, version: str = "") -> str:
    """이름+버전으로 프롬프트 조회. 버전 미지정 시 ``DEFAULT_VERSIONS``."""
    versions = PROMPTS.get(name)
    if versions is None:
        raise KeyError(f"unknown prompt name: {name!r}")
    v = version or DEFAULT_VERSIONS.get(name, "")
    if v not in versions:
        raise KeyError(f"unknown prompt version: {name!r}.{v!r}")
    return versions[v]


__all__ = ["PROMPTS", "DEFAULT_VERSIONS", "get_prompt"]
