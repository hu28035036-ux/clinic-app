"""세션 07 검증 — POST /api/ai/manual/{search,ask} 및 manual_qa 서비스 테스트.

⚠ 외부 LLM 호출은 절대 하지 않는다 — FakeProvider 로 stub.
⚠ 환자 DB 접근 금지 — manual_qa 는 knowledge/manuals/ 만 검색한다.

실행:
    cd <repo_root>
    venv/Scripts/python.exe -m pytest tests/test_ai_manual_qa.py -v
    venv/Scripts/python.exe tests/test_ai_manual_qa.py    # standalone

검증:
  ① 매뉴얼 있는 질문 (예약문자 작성)        : answer/sources, not_found=False, LLM 1회
  ② 매뉴얼 없는 질문 (오늘 점심 추천)        : not_found=True, LLM 0회
  ③ PII 마스킹 (전화번호 포함 질문)          : masked_question 에 010 미포함
  ④ LLM 환각 PII (응답에 전화번호) 사후 마스킹 : answer 에 원본 전화번호 미포함
  ⑤ manual_search — RAG 만, LLM 호출 없음    : sources 반환
  ⑥ endpoint: 빈 질문 → 400                  : pytest 전용
  ⑦ endpoint: AI 비활성 → 503                : pytest 전용
  ⑧ endpoint: manual/search 빈 질문 → 400    : pytest 전용
  ⑨ endpoint: manual/search 정상 200          : pytest 전용 (LLM 미호출)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# fmt: off
from sqlalchemy import create_engine  # noqa: E402, I001
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.services.ai import manual_qa as ai_manual_qa  # noqa: E402
from app.services.ai import provider as ai_provider  # noqa: E402
from app.services.rag.search import reset_cache as _rag_reset_cache  # noqa: E402
# fmt: on


PASS = "[PASS]"
FAIL = "[FAIL]"


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


class FakeProvider(ai_provider.AiProvider):
    """LLM 호출을 stub. text 와 호출 인자를 기록."""
    name = "fake"

    def __init__(self, return_text="발췌에 따르면 예약 문자 탭에서 작성합니다.\n\n참고: sms_compose.md"):
        super().__init__(model="fake-1", api_key="fake-key")
        self.return_text = return_text
        self.calls = []

    def is_ready(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> ai_provider.AiResult:
        self.calls.append({"prompt": prompt, "system": system})
        return ai_provider.AiResult(text=self.return_text)


# ─────────── 테스트 ───────────


def test_1_normal_manual_question():
    """① 매뉴얼 있는 질문 → answer + sources, not_found=False, LLM 1회 호출.

    세션 09 변경: LOW_SCORE_THRESHOLD=2 가 적용되어 한국어 검색 score=1 인
    질문은 LLM 호출 없이 unknown 처리됨. 따라서 score>=2 가 보장되는 더
    구체적인 질문으로 수정.
    """
    _rag_reset_cache()
    db = setup_db()
    fake = FakeProvider()
    res = ai_manual_qa.ask_manual_question(
        db, "예약문자 작성", provider_override=fake,
    )
    ok = (
        res["not_found"] is False
        and isinstance(res["answer"], str)
        and len(res["answer"]) > 0
        and isinstance(res["sources"], list)
        and len(res["sources"]) >= 1
        and len(fake.calls) == 1                # LLM 1회 호출
        and any("sms_compose" in (s.get("path") or "") for s in res["sources"])
    )
    assert ok, res
    return ok, {"answer_first60": res["answer"][:60],
                "sources": [s.get("path") for s in res["sources"]],
                "calls": len(fake.calls)}


def test_2_unknown_question_no_llm():
    """② 매뉴얼에 없는 질문 → not_found=True, LLM 호출 0회."""
    _rag_reset_cache()
    db = setup_db()
    fake = FakeProvider(return_text="이 응답은 호출되지 않아야 함")
    res = ai_manual_qa.ask_manual_question(
        db, "오늘 점심 메뉴 추천해줘 짜장면 짬뽕", provider_override=fake,
    )
    ok = (
        res["not_found"] is True
        # 세션 09: NOT_FOUND 안내문에 "관리자에게 확인해주세요" 가 추가됨
        and "매뉴얼에서 답을 찾지 못했습니다." in res["answer"]
        and res["sources"] == []
        and res["confidence"] == "unknown"
        and len(fake.calls) == 0                # LLM 미호출
    )
    assert ok, res
    return ok, {"answer": res["answer"], "calls": len(fake.calls)}


def test_3_pii_masked_in_question():
    """③ 사용자 질문에 전화번호가 섞여도 masked_question 에서 제거."""
    _rag_reset_cache()
    db = setup_db()
    fake = FakeProvider()
    res = ai_manual_qa.ask_manual_question(
        db,
        "010-1234-5678 환자가 예약문자 작성을 어떻게 해야 하나요?",
        provider_override=fake,
    )
    masked = res["masked_question"]
    # LLM 으로 보낸 prompt 에도 원본 번호가 들어가지 않았는지 검증
    prompt_has_phone = any(
        "010-1234-5678" in c["prompt"] or "01012345678" in c["prompt"]
        for c in fake.calls
    )
    ok = (
        "010-1234-5678" not in masked
        and "01012345678" not in masked
        and "[PHONE]" in masked
        and prompt_has_phone is False
    )
    assert ok, {"masked": masked, "prompt": fake.calls[0]["prompt"][:200] if fake.calls else ""}
    return ok, {"masked_first120": masked[:120]}


def test_4_pii_masked_in_answer():
    """④ LLM 환각 — 응답에 전화번호가 섞이면 사후 마스킹된다."""
    _rag_reset_cache()
    db = setup_db()
    # 일부러 답변에 "전화: 010-1234-5678" 을 박아둠
    fake = FakeProvider(
        return_text="예약문자 작성은 예약 문자 탭에서 합니다. 문의 010-1234-5678 로 연락하세요."
    )
    res = ai_manual_qa.ask_manual_question(
        db, "예약문자 작성 방법", provider_override=fake,
    )
    ok = (
        res["not_found"] is False
        and "010-1234-5678" not in res["answer"]
        and "[PHONE]" in res["answer"]
    )
    assert ok, {"answer": res["answer"]}
    return ok, {"answer_first120": res["answer"][:120]}


def test_5_manual_search_no_llm():
    """⑤ manual_search — RAG 검색만, LLM 호출 없음."""
    _rag_reset_cache()
    res = ai_manual_qa.manual_search("백업은 어디서 해?")
    ok = (
        isinstance(res["sources"], list)
        and len(res["sources"]) >= 1
        and "backup" in (res["sources"][0].get("path") or "")
        and isinstance(res["masked_question"], str)
    )
    assert ok, res
    return ok, {"top_path": res["sources"][0].get("path") if res["sources"] else None}


def test_6_no_provider_returns_not_found():
    """⑥ provider 가 None 으로 들어오면 LLM 호출 없이 not_found=True 로 안전 처리."""
    _rag_reset_cache()
    db = setup_db()
    res = ai_manual_qa.ask_manual_question(
        db, "예약문자 작성", provider_override=None,
    )
    ok = (
        res["not_found"] is True
        and res["answer"] == "매뉴얼에서 답을 찾지 못했습니다."
    )
    assert ok, res
    return ok, {"sources_count": len(res["sources"])}


# ─────────── pytest-only: endpoint 테스트 ───────────


def test_endpoint_ask_400_when_empty(client):
    """⑦ POST /api/ai/manual/ask 빈 질문 → 400."""
    resp = client.post("/api/ai/manual/ask", json={"question": "  "})
    assert resp.status_code == 400, resp.text


def test_endpoint_ask_503_when_disabled(client):
    """⑧ POST /api/ai/manual/ask AI 비활성 → 503."""
    resp = client.post(
        "/api/ai/manual/ask",
        json={"question": "예약문자 작성은 어떻게 해?"},
    )
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert "AI 기능이 꺼져" in body.get("detail", ""), body


def test_endpoint_search_400_when_empty(client):
    """⑨ POST /api/ai/manual/search 빈 질문 → 400."""
    resp = client.post("/api/ai/manual/search", json={"question": ""})
    assert resp.status_code == 400, resp.text


def test_endpoint_search_200_no_llm(client):
    """⑩ POST /api/ai/manual/search 정상 → 200 (AI 비활성에도 동작)."""
    _rag_reset_cache()
    resp = client.post(
        "/api/ai/manual/search",
        json={"question": "예약문자 작성"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body.get("sources"), list)
    assert "masked_question" in body


# ─────────── 러너 (standalone 모드) ───────────

ALL = [
    ("① 매뉴얼 있는 질문 (mock LLM)",      test_1_normal_manual_question),
    ("② 매뉴얼 없는 질문 → LLM 미호출",    test_2_unknown_question_no_llm),
    ("③ PII 마스킹 (질문 입력)",            test_3_pii_masked_in_question),
    ("④ PII 마스킹 (LLM 환각 응답)",        test_4_pii_masked_in_answer),
    ("⑤ manual_search RAG-only",            test_5_manual_search_no_llm),
    ("⑥ provider None 안전 처리",           test_6_no_provider_returns_not_found),
]


def main():
    pass_n = 0
    fail_n = 0
    for name, fn in ALL:
        try:
            ok, payload = fn()
        except Exception as e:
            ok, payload = False, f"EXCEPTION: {e!r}"
        mark = PASS if ok else FAIL
        print(f"{mark}  {name}")
        if not ok:
            print(f"    >> {payload}")
            fail_n += 1
        else:
            pass_n += 1
    print()
    print(f"통과: {pass_n} / 전체: {pass_n + fail_n}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
