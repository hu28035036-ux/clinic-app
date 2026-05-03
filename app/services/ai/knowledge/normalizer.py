"""Markdown normalizer — 18-3 구현.

기능:
  - ``normalize_markdown(raw_text)`` : BOM 제거, CRLF→LF, 라인 우측 공백 strip.
    content_hash 안정성을 위해 동일 입력 → 동일 출력 보장.
  - ``extract_headings(raw_text)`` : 코드블록 외부의 markdown heading 라인을 추출.
    각 항목은 ``{"level", "text", "line", "section_path"}``.
  - ``extract_sections(raw_text)`` : heading 경계로 문서를 섹션 리스트로 자른다.
    각 섹션은 자기 heading 라인을 content 의 첫 줄로 포함한다.

원칙:
  - 외부 호출 0 (순수 함수).
  - 코드블록 (```...```) 내부의 ``#`` 는 heading 으로 인식하지 않는다.
  - 결정적 — 동일 입력 → 동일 출력.

18-4 chunker DB 영속화 시점에 본 모듈의 결과가 그대로 ``content_hash`` 입력으로
사용되므로, 정규화 규칙 변경은 신중히 (변경 시 모든 기존 hash 가 재계산됨).
"""
from __future__ import annotations

import re

# heading 패턴 — 라인 시작 ``# `` ~ ``###### ``
_RE_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_RE_CODE_FENCE = re.compile(r"^\s*```")


def normalize_markdown(raw_text: str) -> str:
    """결정적 마크다운 정규화 — BOM 제거 + CRLF→LF + 라인 우측 공백 strip.

    content_hash 안정성을 위한 진입점. 본문 내용/구조는 변경하지 않는다.
    """
    if not raw_text:
        return ""
    # BOM 제거
    text = raw_text.lstrip("﻿")
    # 라인 끝 정규화
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 라인별 우측 공백 strip
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines)


def extract_headings(raw_text: str) -> list[dict]:
    """코드블록 외부의 heading 라인을 추출.

    반환 항목 (요구사항 #8 의 section_path 정합):
      ``[{"level": int, "text": str, "line": int, "section_path": str}, ...]``
      - ``line`` 은 0-based.
      - ``section_path`` 은 누적 heading 텍스트 ``"h1 > h2 > h3"`` 형식.
    """
    text = normalize_markdown(raw_text)
    if not text:
        return []

    headings: list[dict] = []
    stack: list[tuple[int, str]] = []  # (level, text)
    in_code_block = False

    for idx, line in enumerate(text.split("\n")):
        if _RE_CODE_FENCE.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = _RE_HEADING.match(line)
        if not m:
            continue
        level = len(m.group(1))
        head_text = m.group(2).strip()
        # 같은/하위 레벨 pop
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, head_text))
        section_path = " > ".join(t for _, t in stack)
        headings.append(
            {
                "level": level,
                "text": head_text,
                "line": idx,
                "section_path": section_path,
            }
        )
    return headings


def extract_sections(raw_text: str) -> list[dict]:
    """heading 경계로 문서를 섹션 리스트로 자른다.

    반환 항목:
      ``[{"heading": str, "level": int, "section_path": str, "content": str}, ...]``
      - 각 섹션의 ``content`` 는 자기 heading 라인을 포함 (검색/LLM 전달 시
        heading 정보가 동봉되어야 하므로).
      - heading 이 0개인 문서 → 단일 섹션 (heading="", content=전체).
    """
    text = normalize_markdown(raw_text)
    if not text:
        return []

    lines = text.split("\n")
    sections: list[dict] = []
    in_code_block = False

    current_lines: list[str] = []
    current_heading = ""
    current_level = 0
    current_section_path = ""
    stack: list[tuple[int, str]] = []

    def _flush() -> None:
        # 빈 섹션 (heading 도 없고 내용도 없음) 은 emit 하지 않음
        content = "\n".join(current_lines).strip("\n")
        if not content and not current_heading:
            return
        sections.append(
            {
                "heading": current_heading,
                "level": current_level,
                "section_path": current_section_path,
                "content": content,
            }
        )

    for line in lines:
        if _RE_CODE_FENCE.match(line):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        if in_code_block:
            current_lines.append(line)
            continue

        m = _RE_HEADING.match(line)
        if m:
            # 이전 섹션 flush
            _flush()
            current_lines = []
            current_level = len(m.group(1))
            current_heading = m.group(2).strip()
            while stack and stack[-1][0] >= current_level:
                stack.pop()
            stack.append((current_level, current_heading))
            current_section_path = " > ".join(t for _, t in stack)
            current_lines.append(line)
            continue

        current_lines.append(line)

    _flush()
    return sections


__all__ = ["normalize_markdown", "extract_headings", "extract_sections"]
