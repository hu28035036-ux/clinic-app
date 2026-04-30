"""RAG (Retrieval-Augmented Generation) — knowledge/ 키워드 검색.

외부 LLM 호출 없이 결정론적으로 동작.
sms_guides/ 톤 가이드 검색에 1차 사용.
"""
from .search import search  # noqa: F401
