# 20-P-1 Codex 검증 요청서

## 1. 세션 이름

`20-P-1_post_19p_master_plan` — 19-P 사이클 종료 후 부재 항목 15개 (F-1 ~ F-15) 도입을 위한 *준비 단계* 마스터 플랜.

## 2. 이번 세션 목표

1. 부재 항목 15개를 그룹 A / B / C / D 로 분류 (가벼움 / 중간 / 큰 / 최대 위험도).
2. 그룹 간 의존성 그래프 정리 (F-1 → F-9 / F-3 → F-2 / F-10 → F-8 / F-11 → F-15 등).
3. 마이그레이션 영향 (m014 ~ m025+) 정리.
4. 사용자 결정 필요 항목 (그룹별 합계 16개 후보) 정리 — 실제 결정은 사용자가 그룹 진입 시 답.
5. 응답 key / API URL 변경 영향 정리 — 기존 33+ 셋 보존 + 추가만.
6. 위험도 평가 + 검증 패턴 (19-C 14 영역 + 신규 O/P/Q 3 영역).
7. 진입 순서 권장 (20-1 그룹 A → 20-2 그룹 B → 20-3 분할 → 20-4 분할).

## 3. 작성 / 수정한 문서

| 문서 | 변경 종류 |
|---|---|
| `docs/refactor/20_post_19p_master_plan.md` | **신규** (9개 섹션, 15 부재 항목 / 4 그룹 / 의존성 / 마이그레이션 / 사용자 결정 / 위험도 / 검증 / 진입 순서) |
| `reports/refactor/20-P-1_codex_review_request.md` | **신규** (본 문서) |
| `reports/refactor/latest_codex_review_request.md` | 덮어쓰기 (20-P-1 본문) |

## 4. 수정 금지였던 범위 (20-P-1 세션 범위)

| 금지 항목 | 20-P-1 세션 변경 |
|---|---|
| `app/**` 코드 | 변경 0 |
| `tests/**` 코드 | 변경 0 |
| `app/migrations/m001~m013.py` | 변경 0 |
| `requirements*.txt` | 변경 0 |
| `dosu_clinic.spec` | 변경 0 |
| `app/templates/**` | 변경 0 |
| `app/static/**` | 변경 0 |
| `pyproject.toml` | 변경 0 |
| 기존 API 응답 구조 | 변경 X (read-only 문서 세션) |
| 운영 DB 접근 | 없음 |
| 실제 외부 API 호출 | 없음 |
| 실제 문자 발송 | 없음 |

## 5. 실제 수정한 파일 목록

```
docs/refactor/20_post_19p_master_plan.md       (신규, untracked)
reports/refactor/20-P-1_codex_review_request.md (신규, untracked)
reports/refactor/latest_codex_review_request.md (덮어쓰기)
```

전부 `docs/refactor/` + `reports/refactor/` 만 — `app/` / `tests/` / migration / spec / requirements / UI 변경 0.

## 6. Codex 가 검증해야 할 항목

| # | 항목 | 명령 / 위치 |
|---|---|---|
| C-1 | `app/`, `tests/`, migrations, spec, requirements, UI 변경 0 | `git diff --stat HEAD~0 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 변경 0 |
| C-2 | `docs/refactor/20_post_19p_master_plan.md` 신규 작성 + 9개 섹션 포함 | grep "^## " 결과 §0 ~ §9 |
| C-3 | 부재 항목 15개 (F-1 ~ F-15) 모두 §1 그룹 A/B/C/D 에 분류되었는가 | F-1 / F-2 / ... / F-15 grep 결과 모두 매칭 |
| C-4 | §3 마이그레이션 (m014 ~ m025+) 가 19-P 의 m001~m013 를 침범하지 않는가 | m001~m013 미변경, m014+ 만 신설 |
| C-5 | §4 사용자 결정 필요 항목이 *후보* 만이고 실제 결정은 사용자가 답하도록 명시 | "사용자 답" / "사용자가 그룹 진입 시" 표현 확인 |
| C-6 | §5 응답 key / API URL 변경 영향이 19-P 의 33+ 셋 보존 + 추가만 인지 | "삭제 / rename ⊥" / "추가만" 명시 |
| C-7 | §7 검증 패턴이 19-C 14 영역 (A~N) + 신규 O/P/Q 3 영역으로 확장되었는가 | 19-C 영역 + O / P / Q 영역 명시 |
| C-8 | §8 진입 순서가 의존성 그래프 (§2) 와 정합하는가 | F-1 → F-9 / F-3 → F-2 / F-10 → F-8 / F-11 → F-15 등 |
| C-9 | 본 20-P-1 이 *준비 단계* (read-only 문서) 임을 명시 + 코드 / 마이그레이션 / 테스트 미생성 명시 | §0 메타 / §0-1 / §0-2 |
| C-10 | 19-P 사이클과의 차이 (기능 추가 / 응답 키 추가 / API 신설 / 마이그레이션 신설 허용) 표 정합 | §0-3 표 |

## 7. 잔여 Caveat / 후속 검토

- 본 20-P-1 은 *마스터 플랜* — 각 그룹 진입 시 추가 문서 (예: `20-P-2 그룹 A 상세 기획`) 가 필요할 수 있음. 사용자 결정 후 결정.
- F-9 EMR 연동은 사용자 EMR 벤더 / API / 인증 결정 필수 — 본 20-P-1 에서는 후보만.
- 사용자 결정 필요 항목 16개 중 일부 (F-7 / F-8 보존 기간 / F-15 차단 패턴) 는 권장값 명시 — 사용자 답 없으면 권장값 사용.

## 8. 다음 세션 진행 조건

- 20-P-1 Codex 검증 통과.
- 사용자 §4-A 결정 답 (F-15 차단 패턴 / F-7 보존 기간 / F-8 audit 보존 기간) 받음.
- 20-1 그룹 A 묶음 진입 (F-15 + F-7 + F-8 — 의존성 0, 정책 / 가드만).

## 9. Codex 검증 결과가 기록될 위치

- [reports/refactor/20-P-1_codex_review.md](20-P-1_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 10. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 20-P-1 마스터 플랜 검증 시작해줘. Claude Code 요약만 믿지 말고 docs/refactor/20_post_19p_master_plan.md 를 직접 읽어서 부재 항목 15개 분류 / 의존성 / 마이그레이션 / 사용자 결정 / 위험도 / 진입 순서 정합성을 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-P-1_codex_review.md 에 남겨줘."
