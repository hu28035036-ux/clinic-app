# 19-C Codex 검증 요청서 (r2 보정본)

> **r1 → r2 보정 이력** (Codex r1 = 조건부 통과 / "다음 리팩토링 세션부터 참조 기준으로 사용할 수 있다"):
> - **caveat 1 (워크트리 vs 19-C 세션 구분)**: §4 / §5 / §6 표현 정밀화 + **§6-A 신설** — 워크트리 전체 잔여물 (19-12 ~ 19-14 산출) 을 19-C 범위 밖으로 명시 분리.
> - **caveat 2 (§2-2 fenced 안 `## 1`~`## 7` heading 중복)**: 19-C 신설 문서의 §2-2 코드 블록 예시를 numbered list 로 변환 — 본문 heading 중복 0 (`grep -nE "^## " ...` 결과 §0 ~ §19 단조).
> - **caveat 3 (`latest_test_report.md` / `latest_fix_summary.md` 미언급)**: §6-A 표에 19-14 잔여 + 19-C 가 덮어쓰지 않음 명시.
> - **caveat 4 (`.codex-pyinstaller-build/dist-19-14/` untracked)**: 본 19-C r2 시점에 정리 완료 (재생성 가능 빌드 산출물 / git 비추적 / 합계 123MB / `rm -rf`).

## 1. 세션 이름

`19-C_function_verification_docs` — 19-x 단위화 리팩토링 실제 기능 작동확인 / 순차 진행 / 검증 공통 문서화.

## 2. 이번 세션 목표

1. 실제 기능 작동확인 기준을 문서로 분리한다.
2. 각 19-x 리팩토링 세션에서 자동 테스트 + 실제 기능 작동확인 + 수동 확인 필요 항목 기록을 의무화한다.
3. 각 세션을 순서대로 진행하고, 세션마다 Claude Code 자체 검증 → Codex 검증 → 다음 단계 진행 구조를 문서화한다.
4. Codex 검증 요청 문서에 실제 기능 작동확인 결과를 반드시 포함하도록 공통 규칙을 만든다.
5. 앞으로 긴 작동확인 항목을 매번 복사하지 않고 문서를 참조하게 한다.

## 3. 작성 / 수정한 문서

| 문서 | 변경 종류 | 핵심 변경 |
|---|---|---|
| `docs/refactor/19_refactor_function_verification_checklist.md` | **신규** | 19개 섹션 (메타 / 공통 원칙 V-1~V-10 / 보고 형식 R-1~R-7 / 공통 필수 확인 C-1~C-12 / 14 영역 A~N / 세션별 영향 범위 매핑 / 종합) |
| `docs/refactor/19_refactor_checklists.md` | 수정 (섹션 추가) | §9-A 실제 기능 작동확인 체크리스트 (19-C 연결) — 적용 원칙 / 보고서 기록 형식 / 다음 세션 진행 게이트 3 항목 추가 |
| `docs/refactor/19_refactor_test_strategy.md` | 수정 (섹션 추가) | §7-A 자동 테스트와 실제 기능 작동확인 (19-C 연결) — 차이 표 / 한계 / API 호출 기준 / 수동 확인 기준 / 다음 세션 게이트 5 항목 추가 |
| `docs/refactor/19_refactor_rollout_plan.md` | 수정 (섹션 추가) | §8-A 각 19-x 세션 공통 완료 조건 (19-C 연결) — G-1~G-10 완료 조건 / Codex 검증 요청 22 항목 / 세션별 확인 범위 / 진행 순서 15단계 / 필수 원칙 |
| `reports/refactor/19-C_codex_review_request.md` | **신규** (본 문서) | Codex 검증 요청 — 영구 보존본 |
| `reports/refactor/latest_codex_review_request.md` | 덮어쓰기 | 본 문서와 동일 — Codex 진입점 |

## 4. 수정 금지였던 범위 (19-C 세션 범위)

> **본 §4 는 *19-C 세션 자체* 의 변경 기준** — 워크트리 전체 변경 (이전 19-12 ~ 19-14 잔여물 포함) 과는 별개로 판정. 워크트리 전체 차이는 §6-A 별도 표기.

| 금지 항목 | 19-C 세션 변경 |
|---|---|
| `app/**` 코드 | 19-C 세션 변경 0 |
| `tests/**` 코드 | 19-C 세션 변경 0 |
| `app/migrations/m001~m013.py` | 19-C 세션 변경 0 |
| `requirements*.txt` | 19-C 세션 변경 0 |
| `dosu_clinic.spec` | 19-C 세션 변경 0 (워크트리에는 19-14 잔여 +29줄 — §6-A 참조) |
| `app/templates/**` | 19-C 세션 변경 0 |
| `app/static/**` | 19-C 세션 변경 0 |
| `pyproject.toml` per-file-ignores | 19-C 세션 변경 0 |
| 기존 API 응답 구조 | 변경 X (코드 무수정) |
| 하네스 / 테스트 약화 | 19-C 세션 변경 0 (워크트리에는 19-14 잔여 `tests/test_pyinstaller_hidden_imports.py` +22줄 — §6-A 참조) |
| 운영 DB 접근 | 없음 (문서 세션) |
| 실제 외부 API 호출 | 없음 (문서 세션) |
| 실제 문자 발송 | 없음 (문서 세션) |
| UI 수정 | 19-C 세션 변경 0 |

## 5. 19-C 세션이 실제 수정 / 작성한 파일 목록

```
docs/refactor/19_refactor_function_verification_checklist.md  (신규, untracked)
docs/refactor/19_refactor_checklists.md                       (§9-A 추가)
docs/refactor/19_refactor_test_strategy.md                    (§7-A 추가)
docs/refactor/19_refactor_rollout_plan.md                     (§8-A 추가)
reports/refactor/19-C_codex_review_request.md                 (신규, untracked)
reports/refactor/latest_codex_review_request.md               (덮어쓰기)
```

전부 `docs/refactor/` + `reports/refactor/` 만 — 19-C 세션이 직접 작성한 파일 안에 `app/` / `tests/` / migration / spec / requirements / UI 변경 0.

## 6. 코드 수정 없이 docs/refactor 와 reports/refactor 문서만 작성했는지 확인 (19-C 세션 범위)

- ✅ 본 19-C 는 **read-only 문서 세션** — 19-C 세션이 *직접 작성한 파일* 안에 코드 / 테스트 / fixture / 마이그레이션 / spec / requirements 1바이트도 수정 ⊥.
- ✅ 19-C 세션이 직접 작성한 파일은 모두 `docs/refactor/` 또는 `reports/refactor/` 안.

## 6-A. 워크트리 전체 차이 (19-C 범위 밖 잔여물 — Codex r1 caveat 1·3 정합)

> Codex r1 검증 (조건부 통과) 의 caveat 1 — 워크트리 전체 기준으로 보면 `git diff --stat -- app tests dosu_clinic.spec` 결과가 0 이 아님 — 정합 표기.

워크트리에 남아 있는 *19-C 범위 밖 잔여물*:

| 파일 / 폴더 | 상태 | 출처 | 19-C 처리 |
|---|---|---|---|
| `dosu_clinic.spec` | M (+29줄) | 19-12 ~ 19-14 신설 모듈 hidden imports 갱신 | 19-C 범위 밖 — 19-14 commit 시점에 처리 |
| `tests/test_pyinstaller_hidden_imports.py` | M (+22줄) | 19-12 ~ 19-14 모듈 검증 | 19-C 범위 밖 — 19-14 commit 시점에 처리 |
| `app/modules/admin/` | untracked | 19-12 신설 | 19-C 범위 밖 |
| `app/modules/ai/` | untracked | 19-13 신설 | 19-C 범위 밖 |
| `app/modules/audit/` | untracked | 19-12 신설 | 19-C 범위 밖 |
| `app/modules/backup/` | untracked | 19-12 신설 | 19-C 범위 밖 |
| `app/modules/export_import/` | untracked | 19-7 / 19-12 신설 | 19-C 범위 밖 |
| `tests/test_19_12_admin.py` | untracked | 19-12 신설 | 19-C 범위 밖 |
| `tests/test_19_13_ai_commands.py` | untracked | 19-13 신설 | 19-C 범위 밖 |
| `tests/test_19_14_smoke_workflow.py` | untracked | 19-14 신설 | 19-C 범위 밖 |
| `reports/refactor/19-12_*.md`, `19-13_*.md`, `19-14_*.md` | untracked | 19-12 ~ 19-14 산출물 | 19-C 범위 밖 |
| `docs/refactor/19_refactor_final_test_result.md` | untracked | 19-14 산출물 | 19-C 범위 밖 |
| `reports/refactor/latest_test_report.md` | M | 19-14 잔여 | 19-C 범위 밖 — 19-C 가 덮어쓰지 않음 |
| `reports/refactor/latest_fix_summary.md` | M | 19-14 잔여 | 19-C 범위 밖 — 19-C 가 덮어쓰지 않음 |
| `.codex-pyinstaller-build-19-14/` | untracked | 19-14 PyInstaller 빌드 산출물 | **본 19-C r2 시점에 정리 (재생성 가능 디렉토리)** |
| `.codex-pyinstaller-dist-19-14/` | untracked | 19-14 PyInstaller 배포 산출물 | **본 19-C r2 시점에 정리 (재생성 가능 디렉토리)** |

해석:
- "19-C 세션에서 *기능 코드를 새로 수정하지 않았다*" 는 **참** — 19-C 세션이 직접 작성한 파일 모두 `docs/refactor/` + `reports/refactor/` 안.
- "현재 워크트리 전체가 docs/refactor + reports/refactor 만 변경됐다" 는 **거짓** — 19-12 ~ 19-14 잔여 (modified + untracked) 가 남아 있음.
- 위 잔여물 중 빌드 산출물 디렉토리 2개 (`.codex-pyinstaller-build-19-14/`, `.codex-pyinstaller-dist-19-14/`) 는 본 19-C r2 시점에 정리 — 재생성 가능 + 코드 / 문서 영향 0.
- 나머지 잔여물 (modules / tests / spec diff / 19-12~14 reports / latest_test_report·fix_summary modified) 은 19-12 ~ 19-14 commit / merge 시점에 별도 처리 — 19-C 범위 밖.

## 7. Codex 가 검증해야 할 문서

| # | 문서 | 검증 포인트 |
|---|---|---|
| 1 | `docs/refactor/19_refactor_function_verification_checklist.md` | 신규 문서 — 14 영역 (A 예약 / B 휴무 / C 치료항목·완료체크 / D 환자·메모 / E 치료사·의사 / F 캘린더 / G SMS / H 통계 / I 관리자·백업 / J AI·RAG·commands / K Health / L API·프론트 / M 보안 / N PyInstaller) 각 항목이 충분한지. |
| 2 | `docs/refactor/19_refactor_checklists.md` §9-A | 실제 기능 작동확인 기준이 19-C 신설 문서와 정합하는지. |
| 3 | `docs/refactor/19_refactor_test_strategy.md` §7-A | 자동 테스트 + 기능 작동확인 기준이 반영되었는지. |
| 4 | `docs/refactor/19_refactor_rollout_plan.md` §8-A | 세션별 기능 확인 / 검증 게이트가 반영되었는지 (G-1~G-10 / 22 항목 / 15단계 진행 순서 / 필수 원칙). |
| 5 | 본 검증 요청 문서 | §3 / §4 / §5 / §6 가 실제 변경과 일치하는지. |

## 8. 실제 기능 작동확인 체크리스트가 충분한지 확인할 항목

Codex 가 [19_refactor_function_verification_checklist.md](../../docs/refactor/19_refactor_function_verification_checklist.md) 를 직접 열어서 다음을 확인:

- [ ] §4 A 예약 = 생성 / 수정 / 삭제 / 조회 / 충돌·차단 / 호환성 6 분류 모두 포함하는가.
- [ ] §5 B 휴무 = 등록 / 조회·삭제 / 예약차단 / UI 표시 / 호환성 5 분류 모두 포함하는가.
- [ ] §6 C 치료항목·완료체크 = 치료항목 / 예약 연결 / 완료체크 / 통계 연결 / 호환성 5 분류 + `manual60=1` 명시 (CLAUDE.md 정합) 포함하는가.
- [ ] §7 D 환자·메모 = 검색 / 정보 / 예약연결 / 메모 / 개인정보 보호 5 분류 + 당일 vs 지속 메모 분리 포함하는가.
- [ ] §8 E 치료사·의사 = 치료사 / 의사·진료진 / 호환성 + **F-1 부재 항목 단정 ⊥** 명시 포함하는가.
- [ ] §9 F 캘린더 = 메인 / 미니 / 금일예약환자 / view-model 4 분류 포함하는가.
- [ ] §10 G SMS = 대상추출 / 내용 / 외부발송 / AI 문자 / 호환성 5 분류 + **실제 외부 발송 ⊥** 명시 포함하는가.
- [ ] §11 H 통계 = 기본 / 치료사별 / 치료항목별 / 시간·요일 / 신환 / 호환성 6 분류 + read-only 정책 포함하는가.
- [ ] §12 I 관리자·설정·백업 = 관리자 / API key / 백업 / audit·export_import 4 분류 + API key 비노출 명시 포함하는가.
- [ ] §13 J AI·RAG·commands = RAG / Safety / local-first / Vector·Hybrid / AI commands 5 분류 + provider 호출 0 / 승인 없는 실행 ⊥ 명시 포함하는가.
- [ ] §14 K Health·진단·네트워크 = Health / 네트워크 / 보안 3 분류 포함하는가.
- [ ] §15 L API·프론트 = API / 프론트 2 분류 포함하는가.
- [ ] §16 M 보안 = 운영 DB / 개인정보 / API key·계정 / 외부 호출 4 분류 포함하는가.
- [ ] §17 N PyInstaller = 빌드 / 실행 / 주의 3 분류 포함하는가.
- [ ] §18 세션별 영향 범위 매핑 = 19-0 ~ 19-14 모든 세션의 영향 영역 인덱스 포함하는가.

## 9. 기존 19-x 롤아웃 / 테스트 / 체크리스트 문서에 잘 연결되었는지 확인할 항목

- [ ] [19_refactor_checklists.md §9-A](../../docs/refactor/19_refactor_checklists.md) 가 신규 19-C 문서를 명확히 참조하는가 (마크다운 링크).
- [ ] [19_refactor_test_strategy.md §7-A](../../docs/refactor/19_refactor_test_strategy.md) 의 자동 테스트 vs 실제 기능 작동확인 차이 표가 정합한가.
- [ ] [19_refactor_rollout_plan.md §8-A](../../docs/refactor/19_refactor_rollout_plan.md) 의 G-1 ~ G-10 완료 조건이 19-C §1 ~ §3 원칙과 정합하는가.
- [ ] §8-A-2 의 22 항목 Codex 검증 요청 표가 19-P-9 §9-2 의 14 항목 + 19-C 추가 8 항목으로 합쳐졌는가.
- [ ] §8-A-3 의 세션별 확인 범위가 19-C §18 매핑과 정합하는가.
- [ ] §8-A-4 의 진행 순서 15단계가 [docs/ai_code_session_protocol.md](../../docs/ai_code_session_protocol.md) 14단계 + 작동확인 추가와 정합하는가.

## 10. 각 세션이 순서대로 진행되고 Codex 검증 후 다음 단계로 넘어가도록 문서화되었는지 확인할 항목

- [ ] [19_refactor_rollout_plan.md §8-A-4](../../docs/refactor/19_refactor_rollout_plan.md) 의 진행 순서 15단계가 명확한가.
- [ ] [19_refactor_rollout_plan.md §8-A-5](../../docs/refactor/19_refactor_rollout_plan.md) 의 필수 원칙 — Codex 검증 전 다음 세션 진행 ⊥ / 기능 작동확인 누락 시 보류 / 자동 테스트만 통과 시 완료 X — 가 명시되었는가.
- [ ] [19_refactor_checklists.md §9-A-3](../../docs/refactor/19_refactor_checklists.md) 의 다음 세션 진행 게이트가 정합한가.
- [ ] [19_refactor_test_strategy.md §7-A-5](../../docs/refactor/19_refactor_test_strategy.md) 의 다음 세션 게이트가 정합한가.

## 11. 다음 19-x 리팩토링 세션부터 이 기준을 적용해도 되는지 판단 기준

- [ ] 14 영역 (A~N) 이 모든 19-x 세션의 영향 범위를 충분히 다루는가.
- [ ] 부재 항목 (doctors / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 등 [19_refactor_rollout_plan.md §9 F-1 ~ F-15](../../docs/refactor/19_refactor_rollout_plan.md)) 이 실제 구현된 것처럼 단정되지 않았는가 (V-10 정합).
- [ ] 운영 DB / 외부 API / 실제 문자 발송 / 개인정보·API key 원문 노출 4가지 보안 항목이 모든 영역에 일관되게 적용되었는가.
- [ ] 자동 / API 호출 / 수동 / 영향 없음 / 확인 못함 5분류가 모든 세션에 적용 가능한가.
- [ ] 보고서 형식 (§2-2) 이 기존 [reports/refactor/19-x_test_report.md](../../reports/refactor/) 형식과 호환되는가.

## 12. Codex 가 반드시 확인할 항목

| # | 항목 | 명령 / 위치 |
|---|---|---|
| C-1 | `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 파일이 수정되지 않았는가 | `git diff --stat -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 변경 0 |
| C-2 | `docs/refactor/19_refactor_function_verification_checklist.md` 가 작성되었는가 | 파일 존재 + 14 영역 (A~N) 포함 |
| C-3 | `docs/refactor/19_refactor_checklists.md` §9-A 에 실제 기능 작동확인 기준이 연결되었는가 | grep "## 9-A" + 19-C 링크 |
| C-4 | `docs/refactor/19_refactor_test_strategy.md` §7-A 에 자동 테스트 + 기능 작동확인 기준이 반영되었는가 | grep "## 7-A" + 19-C 링크 |
| C-5 | `docs/refactor/19_refactor_rollout_plan.md` §8-A 에 세션별 기능 확인 / 검증 게이트가 반영되었는가 | grep "## 8-A" + G-1~G-10 + 22 항목 + 15단계 |
| C-6 | 실제 기능 작동확인 항목이 예약 / 휴무 / 치료항목 / 환자 / 치료사 / 문자 / 통계 / 관리자 / AI·RAG / 보안 / PyInstaller 를 충분히 포함하는가 | 19-C §4 ~ §17 14 영역 카운트 |
| C-7 | 현재 기능이 없는 항목 (doctors / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 등) 을 실제 구현처럼 단정하지 않았는가 | 19-C §1 V-10 + §8 E-2 의사 후속 검토 / §12-4 audit / export_import 후속 검토 |
| C-8 | 기능 작동확인 누락 시 다음 세션 보류 기준이 있는가 | rollout §8-A-5 / checklists §9-A-3 / test_strategy §7-A-5 |
| C-9 | Codex 검증 전 다음 세션 진행 금지 원칙이 유지되는가 | rollout R-10 / DEC-T / §8-A-5 |

## 13. Codex 검증 결과가 기록될 위치

- [reports/refactor/19-C_codex_review.md](19-C_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기 — 다음 세션 진입점)

> **인용 시 영구 보존본 (`19-C_codex_review.md`) 사용** — `latest_codex_review.md` 는 진행 중 진입점이라 다음 세션 검증으로 덮어쓰여짐 (19-P-8 caveat 1 정합).

## 14. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 문서와 변경 파일을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 15. r2 재검증 시 Codex 추가 확인 항목

| # | 항목 | 명령 / 위치 |
|---|---|---|
| R2-1 | §2-2 heading 중복 해소 | `grep -nE "^## " docs/refactor/19_refactor_function_verification_checklist.md` 결과 §0 ~ §19 단조, 예시 안의 `## 1` ~ `## 7` 매치 0 |
| R2-2 | §6-A 워크트리 잔여물 표 = git status 정합 | `git status --short` 결과와 §6-A 표 정합 (modules / tests / spec / 19-12~14 reports / latest_test_report·fix_summary modified) |
| R2-3 | `.codex-pyinstaller-build/dist-19-14/` 정리 완료 | `ls -d .codex-pyinstaller-* 2>&1` 결과 "No such file or directory" |
| R2-4 | r1 caveat 1·2·3·4 모두 r2 본문에 반영 | 본 문서 메타 박스 + §6-A + §6 표현 + 19-C 신설 문서 §2-2 |
| R2-5 | 19-C 세션 *직접 작성* 파일은 여전히 `docs/refactor/` + `reports/refactor/` 안 만 | r2 추가 변경분도 동일 범위 |
