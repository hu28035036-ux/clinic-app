# 20-P-3 Codex 검증 결과

## 1. 검증 대상
- 요청 문서: `reports/refactor/latest_codex_review_request.md`
- 세션 요청 문서: `reports/refactor/20-P-3_codex_review_request.md`
- 계획 문서: `docs/refactor/20_post_19p_group_d_detail_plan.md`
- 세션명: `20-P-3_post_19p_group_d_detail_plan`
- 검증 일시: 2026-05-04

## 2. 결론

**통과.**

Claude Code 요약만 믿지 않고 실제 요청 문서, 신규 계획 문서, 파일 구조, git 상태, scoped diff를 직접 대조했다. 이번 20-P-3은 Group D(F-5 출력물, F-6 가져오기/내보내기, F-4 알림, F-9 EMR 연동) 상세 계획을 정리하는 read-only 문서 세션이며, `app/**`, `tests/**`, migrations, spec, requirements, templates/static 구현 변경은 없다.

20-P-3 검증 통과 후 다음 단계는 사용자 §3-4 F-5 출력물 범위 결정이며, 권장 진입은 `20-4-1 F-5 출력물`이다.

## 3. 실제 파일 구조 확인

확인된 변경/신규 파일:

```text
docs/refactor/20_post_19p_group_d_detail_plan.md   신규, untracked
reports/refactor/20-P-3_codex_review_request.md    신규, untracked
reports/refactor/latest_codex_review_request.md     수정
```

`reports/refactor/latest_codex_review_request.md`와 `reports/refactor/20-P-3_codex_review_request.md`는 `Compare-Object` 기준 차이가 없었다.

`git status --short --branch` 기준 현재 브랜치는 `ai-rag-v1-integration`이고, 구현 파일 변경은 확인되지 않았다. `C:\Users\user/.config/git/ignore` permission warning은 기존 환경 경고로 보이며 이번 검증 판단에는 영향을 주지 않는다.

## 4. 문서 내용 대조 결과

`docs/refactor/20_post_19p_group_d_detail_plan.md`에서 직접 확인한 항목:

- 문서가 read-only 계획 세션임을 명시한다.
- Group D 대상 4개 항목 F-5, F-6, F-4, F-9가 모두 상세화되어 있다.
- F-5 출력물은 PDF/HTML/XLSX/all 선택지를 제시하고, PDF+HTML을 권장한다.
- F-6은 CSV/HL7-FHIR/vendor/all 선택지를 제시하고, CSV import v1을 권장한다.
- F-4는 내부 알림/email/Slack/Kakao/SMS/multiple 선택지를 제시하고, internal-only v1을 권장한다.
- F-9는 pass/BitU chart/Doctorang/FHIR/custom 선택지를 제시하고, pass를 권장한다.
- 마이그레이션은 F-4 `m019`, F-9 `m020+`로 m001~m018 이후만 사용하도록 정리되어 있다.
- 의존성은 F-5 -> F-4, F-6 -> F-9, F-4 -> 외부 인증, F-9 -> F-1/F-3로 정리되어 있다.
- 진입 순서는 `20-4-1 F-5` -> `20-4-2 F-6` -> `20-4-3 F-4 internal-only` -> `20-4-4 F-9 pass 권장`이다.
- 기존 응답 key 33+ 보존, 기존 API URL 보존, 신규 key만 추가한다는 원칙이 있다.
- UI 영향은 main.html JS 무수술 원칙과 출력 버튼, CSV import, 알림 UI, EMR mapping UI 추가로 정리되어 있다.
- 검증 패턴은 19-C 14개 영역 + P 영역(출력물/import/알림/EMR)로 정리되어 있다.

요청 문서에는 "13개 섹션"이라고 되어 있으나 실제 계획 문서는 `## 0`부터 `## 13`까지 14개 top-level heading을 가진다. 이는 메타 섹션 포함 여부 차이로 보이며, 필수 계획 항목 누락은 아니다.

## 5. Diff / 테스트 / 로그 확인

scoped diff stat에서 구현 파일 변경은 확인되지 않았다. 신규 계획 문서와 세션 요청 문서는 untracked라 diff stat에는 나타나지 않으며, `latest_codex_review_request.md`만 수정 파일로 표시된다.

이번 세션은 문서-only/read-only 계획 검증이므로 다음은 실행하지 않았다.

```text
ruff
pytest
PyInstaller exe build
```

테스트 미실행은 결함이 아니라 세션 범위에 따른 판단이다. 실제 구현 진입 세션인 20-4-1 이후에는 대상 기능별 ruff, pytest, PyInstaller hidden import/spec discovery 검증이 필요하다.

## 6. Caveat

- F-5 PDF 경로는 구현 전에 PDF 라이브러리, 한글 폰트, PyInstaller 포함 정책을 확정해야 한다.
- F-6은 CSV import v1이 가장 안전하며 HL7/FHIR/vendor EMR 연동은 F-9 결정 이후로 미루는 것이 맞다.
- F-4 외부 채널(email/Slack/Kakao/SMS)은 인증정보 저장/마스킹/테스트 외부 호출 차단 정책 없이는 진입하면 안 된다.
- F-9 EMR은 병원별 시스템 결정이 없으므로 pass 권장이 타당하다. 실제 벤더 연동은 별도 결정 이후 진행해야 한다.
- 신규 문서와 세션 요청 문서는 untracked 상태이므로 저장/커밋 단계에서 함께 포함해야 한다.

## 7. 최종 판정

**20-P-3 검증 통과.**

Group D 상세 계획 문서는 요청 범위와 일치하며, 구현 파일 변경 없이 다음 Group D 구현 진입을 위한 결정 지점을 명확히 정리했다. 다음 권장 액션은 사용자 §3-4 F-5 출력물 결정 후 `20-4-1 F-5 출력물` 세션 진입이다.
