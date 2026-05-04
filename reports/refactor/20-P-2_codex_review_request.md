# 20-P-2 Codex 검증 요청서

## 1. 세션 이름

`20-P-2_post_19p_group_c_detail_plan` — 그룹 C (F-10 / F-11 / F-1 / F-2 / F-3) 5개 항목 상세 기획.

## 2. 이번 세션 목표

20-P-1 마스터 플랜 Codex 검증 caveat 정합:
> "그룹 C/D 는 마이그레이션과 UI/외부 연동 위험이 커서, 20-P-1 문서만으로 바로 코드 작업을 시작하기보다는 그룹별 상세 기획을 한 번 더 두는 편이 안전하다."

본 20-P-2 = 그룹 C 5개 항목 (F-10 노쇼 / F-11 권한 / F-1 doctors / F-2 반복 / F-3 자원) 상세 기획. 마이그레이션 / 응답 키 / UI / 사용자 결정 필요 항목 / 위험도 / 진입 순서 정리.

## 3. 작성 / 수정한 문서

| 문서 | 변경 종류 | 핵심 |
|---|---|---|
| `docs/refactor/20_post_19p_group_c_detail_plan.md` | **신규** | 14개 섹션 (그룹 C 개요 / 공통 원칙 GC-1~10 / F-10·F-11·F-1·F-2·F-3 상세 / 진입 순서 / 응답 key·API URL / UI / 위험도 / 검증 / 종합) |
| `reports/refactor/20-P-2_codex_review_request.md` | **신규** (본 문서) | |
| `reports/refactor/latest_codex_review_request.md` | 덮어쓰기 | 20-P-2 본문 |

## 4. 수정 금지였던 범위 (20-P-2 세션 범위)

| 금지 항목 | 20-P-2 변경 |
|---|---|
| `app/**` 코드 | 변경 0 |
| `tests/**` 코드 | 변경 0 |
| `app/migrations/m001~m013.py` | 변경 0 |
| `requirements*.txt` | 변경 0 |
| `dosu_clinic.spec` | 변경 0 |
| `app/templates/**` | 변경 0 |
| `app/static/**` | 변경 0 |
| `pyproject.toml` | 변경 0 |
| 운영 DB 접근 | 없음 |
| 실제 외부 API 호출 | 없음 |
| 실제 문자 발송 | 없음 |

## 5. 실제 수정한 파일 목록

```
docs/refactor/20_post_19p_group_c_detail_plan.md  (신규, untracked)
reports/refactor/20-P-2_codex_review_request.md    (신규, untracked)
reports/refactor/latest_codex_review_request.md    (덮어쓰기)
```

전부 `docs/refactor/` + `reports/refactor/` 만.

## 6. Codex 가 검증해야 할 항목

| # | 항목 | 명령 / 위치 |
|---|---|---|
| C-1 | `app/`, `tests/`, migrations, spec, requirements, UI 변경 0 | `git diff --stat HEAD~0 -- app tests app/migrations dosu_clinic.spec requirements*.txt app/templates app/static pyproject.toml` 변경 0 |
| C-2 | `docs/refactor/20_post_19p_group_c_detail_plan.md` 신규 작성 + 14개 섹션 포함 | grep "^## " 결과 §0 ~ §14 |
| C-3 | 그룹 C 5개 항목 (F-10 / F-11 / F-1 / F-2 / F-3) 모두 상세 기획되었는가 | F-10 / F-11 / F-1 / F-2 / F-3 grep — 각 §3 / §4 / §5 / §6 / §7 |
| C-4 | 마이그레이션 m014 ~ m023 가 m001~m013 침범 ⊥ | m014+ 만 신설 명시 |
| C-5 | 그룹 C 내부 의존성 (F-1 → F-15 / F-3 → F-2 / F-10 → F-11 등) 명시 | §1-1 의존성 표 |
| C-6 | 진입 순서 (20-3-1 ~ 20-3-5) + F-1 EMR 결정 분기 (a 패스 / b 풀 / c 가벼움) 명시 | §8 |
| C-7 | 응답 key / API URL 영향이 기존 33+ 셋 + 16 extendedProps 키 보존 정합 | §9 / §10 — "기존 키 보존" 명시 |
| C-8 | 위험도 평가 (F-10 / F-11 중간, F-1 / F-2 / F-3 높음) 정합 | §11 |
| C-9 | 검증 패턴 (19-C 14 영역 + 신규 O 영역) 명시 | §12 |
| C-10 | 사용자 결정 필요 항목이 *후보* 만이고 실제 결정은 사용자가 답하도록 명시 | "사용자가 답" / "결정 후" 표현 |
| C-11 | F-1 EMR 도입 범위 (도수치료 전문 vs 일반 진료) 가 *시스템 정체성 결정* 임을 명시 | §5-3 / §5-7 |
| C-12 | 본 20-P-2 가 read-only 문서 세션 임을 명시 + 코드/마이그레이션/테스트 미생성 | §0 메타 / §0-1 / §0-2 |

## 7. 잔여 Caveat / 후속 검토

- F-1 EMR 결정 = 본 시스템 정체성 결정. 사용자 답 없으면 20-3-3 진입 ⊥.
- F-3 자원의 Room 과 F-1 EMR 의 Room 통합 vs 별개 = 사용자 결정 필요.
- 그룹 D (F-4 / F-5 / F-6 / F-9) 상세 기획 = 별도 문서 (`20-P-3`) — 본 20-P-2 범위 외.

## 8. 다음 세션 진행 조건

- 20-P-2 Codex 검증 통과.
- 사용자 §3-7 (F-10 결정) 답 받음 — 권장값으로 진행 가능.
- 20-3-1 F-10 노쇼 진입 (m014 + boolean 컬럼).

## 9. Codex 검증 결과 기록 위치

- [reports/refactor/20-P-2_codex_review.md](20-P-2_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 10. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 20-P-2 그룹 C 상세 기획 검증 시작해줘. Claude Code 요약만 믿지 말고 docs/refactor/20_post_19p_group_c_detail_plan.md 를 직접 읽어서 5개 항목 상세 / 의존성 / 마이그레이션 m014~m023 / 응답 키·API URL 보존 / 위험도 / 진입 순서 정합성을 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-P-2_codex_review.md 에 남겨줘."
