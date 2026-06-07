"""knowledge/ 디렉토리의 *.md 를 스캔해 _index.json 빌드.

실행:
    python tools/build_knowledge_index.py

산출:
    knowledge/_index.json — 결정론적 키워드 검색용 인덱스

PyInstaller 빌드 전에 한 번 실행해 두면, 배포된 exe 도 인덱스를 그대로 사용.
런타임에 인덱스 파일이 없으면 app/services/rag/search.py 가 *.md 를 직접 스캔.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path 에 (standalone 실행 호환)
_THIS = Path(__file__).resolve()
_ROOT = _THIS.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import resource_path  # noqa: E402

_TOKEN_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """어절 단위 토큰화 — 한국어 + 영문/숫자 모두 대응.

    구두점/공백/언더스코어로 split, 길이 2 이상만 채택.
    소문자 변환 (영문만 영향).
    """
    if not text:
        return []
    out = []
    for tok in _TOKEN_RE.split(text):
        if len(tok) >= 2:
            out.append(tok.lower())
    return out


def main() -> int:
    root = resource_path("knowledge")
    if not root.exists():
        print(f"[build_knowledge_index] knowledge/ 가 없습니다: {root}")
        return 1

    docs = []
    md_files = sorted(root.rglob("*.md"))
    for md in md_files:
        rel = md.relative_to(root).as_posix()
        text = md.read_text(encoding="utf-8")
        category = rel.split("/")[0] if "/" in rel else ""
        first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
        title = first_line.lstrip("#").strip() or md.stem
        tokens = tokenize(text)
        docs.append({
            "path": rel,
            "category": category,
            "name": md.stem,
            "title": title,
            "tokens": tokens[:300],   # 상위 300 토큰만 저장 (사이즈 제한)
            "full_text": text,
        })

    out = {
        "version": 1,
        "built_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "documents": docs,
    }
    index_path = root / "_index.json"
    index_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[build_knowledge_index] {len(docs)} 개 문서 → {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
