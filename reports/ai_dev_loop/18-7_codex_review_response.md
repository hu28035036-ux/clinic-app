# 18-7 Codex 검토 응답서

> Codex 가 제기한 모든 항목에 대한 응답 + 즉시 조치 결과.
> **2회차 검증 결과는 본 문서 §11 참조** — 1회차 모든 지적이 해결 확인됨.

## 1. 치명적 문제

> Codex: **없음.** `/api/ai/status` 는 `app/routers/ai.py:187` 에 read-only 관리자 엔드포인트로 추가, 실제 집계는 `app/services/ai/health.py:430`. 외부 LLM/Embedding 호출 0 확인.

→ **확인.** 변경 없음.

## 2. 중간 위험 — M-1: error_detail PII 마스킹

> Codex: `recent_ai_logs.recent[].error_detail` 가 200자로 자르지만 별도 PII 마스킹 없이 DB 값 반환. 저장 시점 정책에 의존. 관리자 화면 노출 API 인 만큼 PII scan/mask 또는 민감정보 샘플 테스트 권장.

### 조치 (완료)

**1) `_safe_error_detail` 헬퍼 추가 — 2차 PII 보호**

`app/services/ai/health.py` 변경:

```python
from . import pii as _pii

def _safe_error_detail(text: Optional[str]) -> str:
    """error_detail 노출 직전 2차 PII 보호.
    
    1. pii.scan(text).cleaned — 전화/주민번호/카드번호 등 패턴 마스킹
    2. ERROR_DETAIL_DISPLAY_LIMIT (200자) cap
    3. 마스킹 자체가 실패하면 빈 문자열 반환 (원문 누출 절대 방지)
    """
    if not text:
        return ""
    try:
        masked = _pii.scan(text).cleaned
    except Exception:
        return ""
    return _truncate(masked, ERROR_DETAIL_DISPLAY_LIMIT)
```

`_serialize_log_row` 가 `_safe_error_detail` 사용으로 전환.

**2) 신규 테스트 6개 추가**

| 테스트 | 검증 |
|---|---|
| `test_get_recent_logs_masks_pii_in_error_detail` | DB 에 PII 가 들어간 error_detail 시드 (전화/생년월일/RRN 모두 포함) → 응답에서 `[PHONE]`/`[BIRTH]`/`[RRN]` 마스킹, 원문 부재 |
| `test_safe_error_detail_helper_masks_phone` | 단위 — 전화번호 패턴 마스킹 |
| `test_safe_error_detail_helper_caps_to_200_chars` | 단위 — 200자 cap |
| `test_safe_error_detail_helper_empty_returns_empty` | 단위 — 빈/None 입력 안전 |
| `test_safe_error_detail_helper_safe_text_passes_through` | 단위 — PII 없는 진단 메시지 통과 |
| `test_status_endpoint_masks_pii_in_recent_logs` | 라우터 통합 — 응답 본문에서도 PII 마스킹 확인 |

**결과**: 6 passed.

## 3. 중간 위험 — M-2: 작업트리 baseline diff 명확화

> Codex: `git diff --stat` 에 `.gitignore`, `app/models/models.py`, `app/services/ai/manual_qa.py`, `tests/conftest.py` 변경 보임. 18-0~18-6 누적이지만 "18-7 만 검증" 관점에서 기준점 섞임. 특히 `tests/conftest.py` 는 "무수정" 주장과 다르게 diff 있음.

### 조치 (완료)

`reports/ai_dev_loop/18-7_fix_summary.md` 의 "무수정" 섹션 두 그룹으로 분리:

```markdown
#### 18-0~18-6 누적 (18-7 추가 수정 0)
- tests/conftest.py — 18-0 격리/FakeProvider/SDK 차단 (132줄 추가)
- app/models/models.py — 18-4/18-5 KnowledgeChunk/KnowledgeVector ORM (123줄 추가)
- app/services/ai/manual_qa.py — 18-2 wrapper 분리 (298줄 변동)
- .gitignore — 1줄 추가 (이전 세션)

#### 18-7 무수정 (diff 0 — 본 세션 변경 없음)
[나머지 모든 파일]
```

### 18-7 자체 git diff (참고)

```
$ git diff HEAD --stat (18-7 시작 ~ 종료)

# 18-7 가 추가한 변경
M app/routers/ai.py                              +42 (status 엔드포인트 + import)
?? app/services/ai/health.py                     +374 (신규 — 18-7 + Codex 후속)
?? tests/test_ai_health_status.py                +570 (신규 — 43 tests)
?? tests/test_ai_contract_manual.py              +191 (신규 — 9 tests)
?? tests/test_admin_ui_smoke.py                  +200 (신규 — 14 tests)
?? reports/ai_dev_loop/18-7_*.md                 +5 reports

# 18-0~18-6 누적 (18-7 추가 수정 0 — Codex 의 "무수정" 우려 대상)
M .gitignore                                     1 줄 (이전 세션)
M app/models/models.py                           123 줄 (18-4/18-5)
M app/services/ai/manual_qa.py                   298 줄 (18-2)
M tests/conftest.py                              132 줄 (18-0)
```

→ 18-7 본 세션은 위 4개 파일에 추가 수정 0. fix_summary 가 모호했음을 인정하고 명확화.

## 4. 사소한 개선 — assertion 정밀도

> Codex: `test_status_endpoint_no_api_key_in_response` 의 `"test-" not in body_text or "sk-" not in body_text` 단언이 `or` 라 약함. `and` 가 의도에 맞음.

### 조치 (완료)

1차 시도: `or → and` 로 강화.

→ test 실행 시 fixture 의 `model="test-model"` 이 `"test-"` 와 충돌 (model 은 의도적 노출 필드).

2차 조치: assertion 정밀도 향상 — substring 검사 대신 정확한 키 검사:

```python
# (1) (2) — api_key 값 / 식별 가능한 부분 모두 부재 (and 로 둘 다 단언).
assert "test-fake-key" not in body_text and "fake-key" not in body_text, (
    "API key 값이 응답에 노출되어선 안 됩니다."
)

# (3) — ai_settings 에 api_key / api_key_masked 키 자체가 없어야 함.
settings_keys = set(body["ai_settings"].keys())
forbidden = {"api_key", "api_key_masked"}
leaked = forbidden & settings_keys
assert not leaked, f"ai_settings 에 금지 키 노출: {leaked}"

# (4) — api_key_set boolean 만 노출.
assert body["ai_settings"]["api_key_set"] is True
assert isinstance(body["ai_settings"]["api_key_set"], bool)
```

→ Codex 의 의도 (둘 다 부재 단언) + 실제 코드 정합성 (model 노출 허용) 모두 만족.

## 5. 범위 초과 변경 여부

> Codex: 18-7 구현 자체는 범위 내. 새 migration 없음. 기존 migration diff 없음. requirements/spec/pyproject/templates/static diff 없음. vector/hybrid/RAG 알고리즘 파일 diff 없음. main.html 에 /api/ai/status UI 호출 추가 없음. 외부 embedding/LLM 연동 추가 없음.

→ **확인.** 후속 조치도 동일 범위 (`app/services/ai/health.py` 내 PII helper 추가 +
`tests/test_ai_health_status.py` 6개 테스트 추가 + `tests/test_ai_health_status.py` 1개 단언 정밀화).

## 6. 테스트가 부족한 부분

> Codex: error_detail 에 전화번호/이름 같은 민감정보가 들어간 경우 /api/ai/status 가 마스킹하는지 테스트 부재. 길이 제한과 hash 미노출은 검증하지만 PII 원문 차단은 저장 정책에 의존.

→ **M-1 조치로 해결**. 6개 신규 테스트 추가 — DB 시드 시나리오 + 단위 + 라우터 통합 모두 커버.

## 7. Codex 환경 이슈 (참고)

> Codex: 전체 pytest 5 errors — `C:\Users\user\AppData\Local\Temp\pytest-of-user` 접근 권한 문제로 tmp_path fixture setup 실패.

→ **테스트 로직 무관**. Claude Code 환경에서는 동일 명령 100% 통과 확인:
- 18-7 신규/계약/smoke: **66 passed** (M-1 후속 6개 추가)
- 전체: **476 passed, 1 skipped, 7 xfailed**
- ruff: All checks passed
- check_db_path: OK

Codex 환경의 임시 디렉토리 권한 이슈는 별도 문제. 18-5 Codex 검토에서도 동일 이슈 보고됨 (지속 이슈).

## 8. 후속 조치 후 결과 요약

| 항목 | Codex 1회차 | 후속 조치 후 |
|---|---|---|
| 18-7 신규 테스트 | 60 passed | **66 passed** (+6 PII tests) |
| 전체 tests | 470 passed | **476 passed** |
| 회귀 테스트 | 410 passed | 410 passed (회귀 0) |
| ruff | All checks passed | All checks passed |
| check_db_path | OK | OK |
| API key 노출 | 0 (boolean only) | **0 + assertion 정밀화** |
| PII (recent_ai_logs.error_detail) 노출 | 200자 cap만 | **pii.scan 마스킹 + 200자 cap** |
| /reindex 엔드포인트 | 미구현 | 미구현 (사용자 18-7 정책) |
| main.html UI | 무수정 | 무수정 |
| 작업트리 명확화 | 모호 | **두 그룹 분리 + git diff 표 첨부** |

## 9. 변경 파일 (Codex 후속 추가분)

| 파일 | 변경 |
|---|---|
| `app/services/ai/health.py` | +30줄 (`_safe_error_detail` 헬퍼 + import + `_serialize_log_row` 전환 + `__all__` 갱신) |
| `tests/test_ai_health_status.py` | +6 tests (~120줄, PII 마스킹 검증) + 1 assertion 정밀화 |
| `reports/ai_dev_loop/18-7_fix_summary.md` | 무수정 섹션 두 그룹 분리 + 후속 조치 섹션 추가 |
| `reports/ai_dev_loop/18-7_codex_review_response.md` | 신규 (본 파일) |
| `reports/ai_dev_loop/latest_codex_review_response.md` | 사본 (Codex 응답 추적) |

## 10. 다음 단계 권장

1. **Codex 재검증 (2회차)** — 본 응답서 + 신규 6개 테스트 + assertion 정밀화 확인.
2. **18-8 진입 가능** — 회귀 0 + Codex 1회차 모든 지적 해결.
3. **남은 위험 (`18-7_codex_review_request.md` §17)** 8개는 본 세션 범위 외 — 18-8 또는 별도 세션 결정.

---

## 11. Codex 2회차 검증 결과 (수신 완료)

### 11-1. 치명적 문제 (Codex 2회차)

> **없음.** 이전에 지적한 `recent_ai_logs.error_detail` PII 위험은 수정됐습니다.
> `health.py` (line 400) 에 `_safe_error_detail()` 가 추가되어 `pii.scan(...).cleaned`
> 후 200자 cap 을 적용하고, `_serialize_log_row()` 가 이 helper 를 사용합니다.

→ **M-1 해결 확인.** 추가 조치 불필요.

### 11-2. 중간 위험 2회차 (Codex 2회차)

#### 2회차 M-A: pytest 전체 실행 완료 판정 X (Codex 환경 이슈)

> 전체 `pytest tests` 는 아직 완료 판정이 안 납니다. 코드 실패라기보다는 pytest 임시 디렉터리
> 접근 권한 문제로 session setup/finish 쪽에서 PermissionError: WinError 5. 484 items 중
> 대부분 실행됐지만 `tests/temp/pytest-basetemp-codex-18-7-full` 접근 권한 문제로 종료됐습니다.

**응답**: 코드 차원 조치 불필요 — Codex 환경 이슈.

- Claude Code 환경에서는 동일 명령 100% 통과 (`476 passed, 1 skipped, 7 xfailed`).
- 18-5/18-6 Codex 검토에서도 동일 권한 이슈 보고됨 (지속되는 환경 차이).
- Codex 가 직접 실행한 핵심 묶음은 모두 통과:
  - 18-7 신규/계약/smoke: **66 passed** ✅
  - 기존 RAG/chunker/reindex/vector/hybrid + SMS AI/휴무 AI: **298 passed** ✅
  - ruff: passed ✅
  - check_db_path: OK ✅

#### 2회차 M-B: 작업트리 누적 diff (Codex 2회차)

> 작업트리는 여전히 이전 세션 누적 변경이 섞여 있습니다. `git diff --stat` 에는
> `app/models/models.py`, `app/services/ai/manual_qa.py`, `tests/conftest.py` 등이 같이
> 보입니다. 18-7 수정 자체는 좁지만, 커밋/릴리스 전에는 세션별 변경 묶음을 분리해서
> 보는 게 좋습니다.

**응답**: Git 운영 결정 사항 — 코드 차원 조치 불필요.

- 18-7 본 세션 추가 수정은 **0** (M-2 1회차 응답에서 이미 명시 + 두 그룹 분리).
- 누적 변경 (`app/models/models.py` / `manual_qa.py` / `conftest.py` / `.gitignore`)
  은 18-0~18-6 의 staged-but-uncommitted 결과.
- **권장 (사용자 결정)**:
  - **옵션 A**: 18-8 진입 전 18-0~18-7 누적 변경을 세션별로 분리 커밋 (세부 추적 가능, 시간 소요).
  - **옵션 B**: 18-8 끝까지 진행한 후 단일 release commit (`v1.4.0` 등) 으로 묶기 (속도 우선).
  - 어느 쪽이든 코드/테스트 결과는 동일.

### 11-3. 사소한 개선 (Codex 2회차)

> API key 테스트도 개선됐습니다. 기존 느슨한 `or` 단언 대신 `test-fake-key`, `fake-key`,
> `api_key`, `api_key_masked` 부재와 `api_key_set` boolean 을 더 명확히 확인합니다.

→ **사소한 개선 해결 확인.**

### 11-4. 범위 초과 변경 여부 (Codex 2회차)

> 이번 수정은 18-7 범위 안입니다. 금지 변경도 다시 확인했습니다.
> - 새 migration 없음
> - 기존 migration diff 없음
> - requirements.txt, pyproject.toml, dosu_clinic.spec diff 없음
> - app/templates, app/static diff 없음
> - vector/hybrid/RAG 알고리즘 파일 diff 없음
> - 외부 LLM/Embedding API 호출 추가 흔적 없음

→ **범위 준수 확인.**

### 11-5. 테스트가 부족한 부분 (Codex 2회차)

> 이전의 핵심 부족분이었던 `error_detail` PII 테스트는 보강됐습니다. 추가된 테스트는
> DB 에 전화번호/생년월일/RRN 이 들어간 상황과 `/api/ai/status` 응답 본문에서 전화번호가
> 노출되지 않는 상황을 직접 검증합니다.

→ **테스트 부족 해결 확인.**

### 11-6. Codex 2회차 직접 실행 결과

| 묶음 | 결과 |
|---|---|
| 18-7 신규/계약/smoke | **66 passed** ✅ |
| 기존 RAG/chunker/reindex/vector/hybrid + SMS AI/휴무 AI | **298 passed** ✅ |
| ruff (`app tests scripts`) | **passed** ✅ |
| check_db_path | **OK** (단독 실행 시 운영 경로 표시 — 의도된 INFO. 테스트 중 격리는 db_path 테스트로 확인) |
| 전체 pytest | 484 items 중 대부분 실행, Codex 환경 권한 이슈로 session finalization 실패 (코드 무관) |

### 11-7. 최종 판정

✅ **Codex 2회차 검증 통과** — 1회차 모든 지적 (치명적/중간/사소한 개선/테스트 부족) 해결 확인.

**다음 세션 (18-8) 진입 가능**:
- 코드/테스트 차원에서 추가 조치 0.
- 사용자 결정 사항: 18-7 → 18-8 진입 전에 git 커밋 분리 여부 (옵션 A/B 위 §11-2 M-B).
