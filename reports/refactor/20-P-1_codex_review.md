# 20-P-1 Codex 검증 결과

검증 시각: 2026-05-04, `latest_codex_review_request.md` 최신본 기준.

## 판정

**통과.** `20-P-1_post_19p_master_plan`은 19-P 이후 부재 항목 15개(F-1 ~ F-15)를 실제 구현 전 준비 단계 문서로 분류하고, 사용자 결정 항목과 위험도, 마이그레이션 영향, 응답 key/API URL 영향, 검증 패턴, 권장 진입 순서를 충분히 정리했다.

다음 단계는 문서가 제안한 대로 **사용자 §4-A 결정 후 20-1 그룹 A(F-15 + F-7 + F-8) 진입**이다.

## 직접 검증한 근거

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/20-P-1_codex_review_request.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, 파일 존재/줄 수, 문서 heading, F-1~F-15 항목, m014~m025+ 계획, 사용자 결정 후보, 응답 key/API URL 정책을 직접 확인했다.
- 이번 세션은 read-only 문서 계획 세션이므로 pytest/PyInstaller는 재실행하지 않았다.

## 요청 문서와 실제 파일 비교

| 파일 | 요청 문서 주장 | 실제 확인 |
|---|---|---|
| `docs/refactor/20_post_19p_master_plan.md` | 신규, 9개 섹션 | 존재, 309줄, `## 0` ~ `## 9` 확인 |
| `reports/refactor/20-P-1_codex_review_request.md` | 신규 | 존재, 86줄 |
| `reports/refactor/latest_codex_review_request.md` | 20-P-1로 덮어쓰기 | 20-P-1 요청 문서와 동일 |

20-P-1 직접 변경 범위는 `docs/refactor/`와 `reports/refactor/` 문서다. `git status --short -- docs/refactor/20_post_19p_master_plan.md reports/refactor/20-P-1_codex_review_request.md reports/refactor/latest_codex_review_request.md app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 기준으로 20-P-1 신규/수정 파일 외의 app/tests/spec/requirements/UI 직접 변경은 확인되지 않았다.

## 문서 내용 검증

`docs/refactor/20_post_19p_master_plan.md`에서 다음을 확인했다.

- F-1 ~ F-15 전체가 그룹 A/B/C/D로 분류됨
- 그룹 A: F-15, F-7, F-8
- 그룹 B: F-13, F-12, F-14
- 그룹 C: F-10, F-11, F-1, F-2, F-3
- 그룹 D: F-4, F-5, F-6, F-9
- 의존성 그래프 포함: F-1 → F-9, F-1 → F-15, F-3 → F-2, F-10 → F-8, F-11 → F-15, F-7 ← F-8 등
- 마이그레이션 계획 포함: m014 ~ m026+
- 사용자 결정 후보 포함: 그룹 A 3개, B 3개, C 5개, D 5개로 총 16개 후보
- 기존 33+ 응답 key는 삭제/rename 금지, 신규 API/응답 key는 추가만 허용한다고 명시
- 19-C 검증 영역 A~N에 신규 O/P/Q 영역을 추가해 20대 기능 검증 패턴으로 확장
- 권장 진행 순서 포함: 20-1 그룹 A → 20-2 그룹 B → 20-3 그룹 C 분할 → 20-4 그룹 D 분할

## 주요 Caveat

- 문서는 “준비 단계”이며 실제 구현 결정 문서가 아니다. 사용자 결정 후보는 잘 정리되어 있지만, 실제 진행 전에는 §4-A부터 명시 답변이 필요하다.
- F-9 EMR 연동은 EMR 벤더/API/인증/매핑 결정 전에는 구현 진입이 어렵다는 점이 문서에 적절히 남아 있다.
- 그룹 C/D는 마이그레이션과 UI/외부 연동 위험이 커서, 20-P-1 문서만으로 바로 코드 작업을 시작하기보다는 그룹별 상세 기획을 한 번 더 두는 편이 안전하다.

## 종합

20-P-1은 19-P/19-C 이후의 부재 항목 도입을 위한 마스터 플랜으로 충분히 기능한다. 특히 “기존 응답 key/API URL 삭제 금지, 추가만 허용”, “m014+부터 신규 migration”, “사용자 결정 전 구현 금지”, “20-1 그룹 A부터 낮은 위험으로 진입” 원칙이 명확하다.

결론: **20-P-1 통과, 사용자 §4-A 결정 후 20-1 그룹 A 진입 가능**.
