"""pytest_loop_10.py — 전체 회귀 10회 반복 실행 + 결과 요약.

자동 모드:
- 매 회차마다 venv/Scripts/python.exe -m pytest tests -q 실행
- passed / failed / 시간 기록
- 변동 (회차간 결과 차이) 발생 시 즉시 표시
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    py = str(project_root / "venv" / "Scripts" / "python.exe")

    runs: list[dict] = []
    for i in range(1, 11):
        t0 = time.time()
        proc = subprocess.run(
            [py, "-m", "pytest", "tests", "-q", "--no-header"],
            cwd=str(project_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        elapsed = time.time() - t0
        # 마지막 줄에서 카운트 파싱
        tail = proc.stdout.strip().splitlines()[-3:] if proc.stdout else []
        last = "\n".join(tail)
        m = re.search(
            r"(\d+) passed(?:,\s*(\d+) skipped)?(?:,\s*(\d+) xfailed)?(?:,\s*(\d+) failed)?",
            last,
        )
        passed = int(m.group(1)) if m else 0
        skipped = int(m.group(2)) if m and m.group(2) else 0
        xfailed = int(m.group(3)) if m and m.group(3) else 0
        failed = int(m.group(4)) if m and m.group(4) else 0
        runs.append({
            "iteration": i,
            "passed": passed,
            "skipped": skipped,
            "xfailed": xfailed,
            "failed": failed,
            "exit_code": proc.returncode,
            "elapsed_sec": round(elapsed, 1),
        })
        print(f"[{i}/10] passed={passed} skipped={skipped} xfailed={xfailed} failed={failed} exit={proc.returncode} time={elapsed:.1f}s")

    # 변동 검사
    passed_set = {r["passed"] for r in runs}
    failed_set = {r["failed"] for r in runs}
    all_same = len(passed_set) == 1 and len(failed_set) == 1
    all_pass = all(r["failed"] == 0 and r["exit_code"] == 0 for r in runs)

    summary = {
        "total_iterations": len(runs),
        "all_same_passed_count": all_same,
        "all_pass": all_pass,
        "passed_set": sorted(passed_set),
        "failed_set": sorted(failed_set),
        "runs": runs,
    }
    Path(project_root / "docs" / "ai" / "verification" / "RUNTIME_PYTEST_LOOP_10.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
