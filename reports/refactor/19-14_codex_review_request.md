# 19-14 Codex 검증 요청서

## 1. 세션 이름

`19-14_full_regression_pyinstaller` — 19-1 ~ 19-13 전체 회귀 + PyInstaller 빌드.

## 2. 이번 세션 목표

19-1 ~ 19-13 의 13개 단위화 리팩토링 세션 누적 결과가 깨지지 않았는지 전체 회귀
테스트 + PyInstaller 빌드 + 빌드 산출물 실행으로 검증. **단위화 리팩토링 1차
완료 판정**.

## 3. 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `tests/test_19_14_smoke_workflow.py` | 신규 (15 cases — 12 passed + 3 xfailed) | 336 |
| `docs/refactor/19_refactor_final_test_result.md` | 신규 | 188 |

(기능 변경 코드 / 라우터 / 서비스 / 모델 / 마이그레이션 / spec / requirements
무수정.)

## 4. 실행한 테스트 명령

```
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m pytest tests/test_19_14_smoke_workflow.py -v
venv\Scripts\python.exe -m pytest tests -k "appointment or appt or rules or availability" -q
venv\Scripts\python.exe -m pytest tests -k "leave" -q
venv\Scripts\python.exe -m pytest tests -k "treatment or completion" -q
venv\Scripts\python.exe -m pytest tests -k "patient or notes" -q
venv\Scripts\python.exe -m pytest tests -k "therapist" -q
venv\Scripts\python.exe -m pytest tests -k "sms" -q
venv\Scripts\python.exe -m pytest tests -k "stats" -q
venv\Scripts\python.exe -m pytest tests -k "admin or backup or audit" -q
venv\Scripts\python.exe -m pytest tests -k "rag or safety" -q
venv\Scripts\python.exe -m pytest tests -k "vector or hybrid or chunk or reindex or knowledge" -q
venv\Scripts\python.exe -m pytest tests -k "ai or contract or action_leave" -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
venv\Scripts\pyinstaller.exe --noconfirm dosu_clinic.spec
DOSU_DB_PATH=$(pwd)/.test-build-tmp/test_clinic.db dist/도수치료예약/도수치료예약.exe
```

## 5. 테스트 결과

| 검증 | 결과 |
|---|---|
| `pytest tests -q` (전체) | **1671 passed, 1 skipped, 10 xfailed, 27 warnings** |
| `pytest tests/test_19_14_smoke_workflow.py -v` | **12 passed, 3 xfailed** |
| 카테고리별 (예약/휴무/treatments/sms/stats/admin/AI/RAG/Safety) | 통과 |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | **exit 0** |
| PyInstaller 빌드 | **exit 0** (87s) |
| 빌드 산출물 단일 인스턴스 락 동작 | 확인 |

19-13 baseline 1659 → 19-14 1671 (smoke 12 + xfail 3 추가). 회귀 0건.

## 6. 실패한 테스트와 원인

자동 수정 루프 1회차에 7건 실패:

| 실패 케이스 | 원인 | 1회차 수정 |
|---|---|---|
| `test_smoke_2` | PUT 응답 shape 가정 오류 (`{"id"}` → 실제 `{"ok", "version"}`) | shape 정정 |
| `test_smoke_4` | 세션 공유 DB + 다른 테스트가 사용한 슬롯 충돌 | 항목 4 제거 + `test_appointment_rules.py:test_two_manual30_same_slot_blocked` 매핑 |
| `test_smoke_5/6/7/9c` | 휴무 차단 baseline 미구현 (spec 02) | `@pytest.mark.xfail` 정합 (기존 `test_therapist_leave.py` 와 동일 패턴) |
| `test_smoke_10b` | FullCalendar 응답 — `patient_id` 가 `extendedProps` 안 | `row['extendedProps']['patient_id']` 정정 |

2회차 정정으로 12 passed + 3 xfailed (휴무 차단 baseline 미구현 추적). ruff 자동
보정 1회.

## 7. 수정 금지 범위 준수 여부

| 금지 항목 | 준수 |
|---|---|
| 새 기능 추가 | ✅ smoke 만 |
| 대규모 리팩토링 | ✅ 무수정 |
| 예약/휴무/문자/통계/AI 핵심 로직 변경 | ✅ 무수정 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ main.html 무수정 |
| 기존 API 응답 key 변경 | ✅ 무수정 |
| 하네스/테스트 약화 | ✅ conftest.py / pyproject.toml 무수정 |
| 운영 DB 접근 | ✅ scripts/check_db_path.py exit 0 |
| 실제 외부 API 호출 | ✅ 19-12 / 19-13 가드 정합 |
| 실제 외부 문자 발송 | ✅ 무수정 |
| requirements.txt | ✅ 무수정 |
| PyInstaller spec | ✅ 본체 무수정 (19-12 / 19-13 등록은 해당 세션 완료) |

## 8. 기존 API URL / 응답 key 유지 여부

**유지**. 본 19-14 가 라우터 본체 / 응답 dict 변경 ⊥. 19-9 (예약) / 19-10 (sms) /
19-11 (stats) / 19-12 (admin/backup/audit) / 19-13 (AI commands) 모든 응답 key
contract 정합 검증 통과.

## 9. 기존 주요 기능 회귀 여부

**회귀 부재**. 1671 / 1 skipped / 10 xfailed (휴무 차단 7 + 19-14 신규 xfail 3).

| 기능 | 결과 |
|---|---|
| 예약 생성/수정/삭제/취소 | 통과 (smoke 1/2/3 + appointment_rules) |
| 예약 중복 차단 | 통과 (`test_two_manual30_same_slot_blocked`) |
| 휴무/반차 차단 | xfail (baseline 미구현, spec 02) |
| 반차 허용 시간대 | 통과 (smoke 6b/7b + therapist_leave 허용 케이스) |
| 치료항목별 완료체크 | 통과 |
| 시간 가중치 회귀 방지 | 통과 (19-11 RISK 가드) |
| 환자 검색 / 신환 체크 | 통과 |
| 치료사 활성/색상/치료 가능 항목 | 통과 |
| 통계 결과 | 통과 (19-11 contract) |
| 문자 대상 추출 / 문자 내용 | 통과 |
| 관리자 설정 / 백업 기능 | 통과 (19-12) |

## 10. AI / RAG 하네스 결과

| 하네스 | 결과 |
|---|---|
| RAG manual ask / search contract | 통과 |
| Safety harness (PII / hallucination / blocked) | 통과 |
| Full harness | 통과 |
| Chunker / Reindex / Vector / Hybrid 하네스 | 통과 |
| 관리자 상태 (health/public, status, providers, settings) | 통과 |
| local_only → LLM/Embedding 0 | 통과 |
| no_sources / low_confidence / PII / unknown_feature → provider 0 | 통과 |
| AI commands 승인 없이 DB 변경 ⊥ | 통과 (19-13 contract) |
| Safety → Preview → Approval → Execute 경계 | 통과 |

## 11. 운영 DB 보호 여부

**보호.**

- `scripts/check_db_path.py` exit 0.
- `tests/conftest.py` APPDATA + DOSU_DB_PATH 임시 경로 격리 활성.
- 19-12 backup 정책 (engine.dispose / atomic rename / safety backup) 본체 무수정.
- PyInstaller 빌드 산출물 실행 시 단일 인스턴스 락 검출 + 운영 DB 미접근 우선.

## 12. 외부 API 호출 여부

**호출 부재.**

- 19-12 / 19-13 신규 modules 가드 (urllib / requests / httpx / openai /
  anthropic import 부재) 통과.
- conftest.py 의 SDK 클래스 stub 활성.
- FakeProvider / FakeEmbeddingProvider — 모든 AI 테스트 사용.

## 13. 실제 문자 발송 여부

**발송 부재.**

- 19-10 sms FakeSmsProvider 정책 그대로.
- 19-13 sms_draft 본체 무수정 + needs_user_confirm 가드.

## 14. API key / 개인정보 원문 노출 여부

**노출 부재.**

- 19-12 `AI_SETTINGS_FORBIDDEN_KEYS = {"api_key"}` ∩ 응답 key = ∅ (cross-check 통과).
- 19-12 `PUBLIC_CONFIG_DROP_KEYS = {admin_password_hash, sync_secret}` 가드 통과.
- 19-12 `mask_api_key` / `mask_munjanara_*` byte-equivalent 통과.
- 19-12 `AUDIT_DETAIL_CAP = 500` PII 폭주 방지 통과.
- 19-12 `bulk_import` audit detail = 카운트만 통과.
- 19-13 `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS = {prompt_text, response_text}` ∩ 응답 = ∅ 통과.
- 19-13 `PII_FORBIDDEN_FIELDS` (10 필드) + `SECRET_KEYS_FORBIDDEN_IN_LOG` (8 키) 가드.

## 15. PyInstaller 빌드 결과

| 항목 | 결과 |
|---|---|
| 빌드 명령 | `venv/Scripts/pyinstaller.exe --noconfirm dosu_clinic.spec` |
| Exit code | **0** |
| 빌드 시간 | ~87s |
| 산출물 진입점 | `dist/도수치료예약/도수치료예약.exe` (15MB) |
| 부속 | `_internal/` (Python 런타임) + `updater.bat` |
| 마이그레이션 자동 등록 | 13 (m001 ~ m013) |
| 19-12 + 19-13 신규 hidden import 20 모듈 | 정합 |

## 16. 빌드 산출물 실행 확인 결과

```
DOSU_DB_PATH=$(pwd)/.test-build-tmp/test_clinic.db dist/도수치료예약/도수치료예약.exe
```

- **결과**: 단일 인스턴스 락 동작 확인 ("이미 실행 중입니다" 메시지 + 정상 종료
  exit 0). 빌드 산출물의 binary 진입점 / 단일 인스턴스 락 / 종료 정합.
- **운영 DB 보호**: 사용자의 기존 실행 인스턴스가 운영 DB 사용 중. 추가 상호작용 ⊥.

### Codex 재검증 시 발견 — 환경 잠금 (WinError 5) + 정정 검증

- Codex 재빌드 시 `dist/도수치료예약/_internal/anthropic/lib` 제거 단계에서
  `WinError 5 Access denied` (사용자의 기존 실행 인스턴스가 폴더 잠금). 격리
  경로 (`--distpath` / `--workpath`) 빌드는 exit 0.
- 본 19-14 세션 정정 검증: 사용자가 인스턴스 종료 후 기본 경로 재빌드
  (`rm -rf build dist/도수치료예약 && pyinstaller --noconfirm dosu_clinic.spec`)
  → **exit 0** + 산출물 정합 확인 (15MB + 루트 `updater.bat` + `_internal/`).
- 결론: 기능적 문제 ⊥, 환경 잠금 이슈. 권장 절차: 빌드 전 기존 실행 인스턴스
  종료 + `dist/도수치료예약` 정리 → 빌드.

## 17. 주석 / 문서화 기준 확인 결과

| 검증 | 결과 |
|---|---|
| 신규 / 분리 파일 docstring | 19-1 ~ 19-13 모두 적용 |
| 주요 service / rules / repository / schemas 함수 docstring | 적용 |
| COMPAT / SAFETY / NOTE / RISK / TODO 주석 | 적용 (19-1 ~ 19-13 일관) |
| 의미 없는 줄 주석 과도 추가 | 부재 |
| 주석 ↔ 실제 코드 동작 일치 | 검증 통과 (각 세션 contract 테스트) |

## 18. 실패 / 수정 루프 횟수

**2 회차 코드 수정** — smoke 응답 shape 정정 + xfail 마커 추가 + 항목 4 매핑 표로
처리. ruff 자동 보정 1회. **5회 한도 내**.

## 19. 단위화 리팩토링 1차 완료로 봐도 되는지 판단 기준

**Claude Code 자체 판단: yes — 1차 완료**.

근거:

1. **13개 세션 모두 Codex 검증 통과** (19-0 ~ 19-13).
2. **1671 / 1 skipped / 10 xfailed** — 19-13 baseline 1659 + smoke 12 + xfail 3.
   회귀 0건.
3. **ruff All checks passed** + DB 보호 검사 exit 0.
4. **PyInstaller 빌드 성공** + 산출물 단일 인스턴스 락 동작 확인 + hidden import
   20 모듈 정합.
5. **모든 신규 modules 본체 무수정 가드** — D-4 단방향 경계 + 외부/DB/LLM 의존
   부재 + 라우터/서비스 본체 byte-equivalent.
6. **API key / PII / 비밀 값 / 외부 SMS 발송 / 외부 LLM 호출 / 운영 DB 변경**
   모두 차단 정책 가드 통과.
7. **응답 key contract 33+ 키** (manual/search 3 + manual/ask 9 + sources 3 +
   health 9 + status 9 + sms/draft 7 + action/parse 6 + action/preview 11 +
   action/execute 5 + 19-9~19-12 추가 셋) 모두 보존.
8. **AI 가 사용자 승인 없이 DB 변경 ⊥** + Local-first / provider 호출 차단 가드
   통과.

**남은 위험 요소** (19-x 후속):

- 휴무 차단 백엔드 미구현 (spec 02) — UI 측 차단 보완 중. 후속 백엔드 강제 가드.
- AI 예약 / SMS 일괄 / 환자 등록 흐름 — 현재 미구현 (TODO 마커).
- export_import `_dc_*` 헬퍼 + Excel export 본체 분리 — 현재 helper 만, 본체 분리는
  19-x.
- about/check-update / download-update / apply-update 응답 빌더 — 19-x 검토.
- AuditLog retention 정책 — 미구현.
- 라우터 / 서비스 본체의 modules helper 채택 — 점진적, 19-x 진행.

## 18 (참고). Codex 가 집중 검토할 파일

1. `tests/test_19_14_smoke_workflow.py` (12 passed + 3 xfailed — 11 항목 매핑)
2. `docs/refactor/19_refactor_final_test_result.md` (1차 완료 판정)
3. `dist/도수치료예약/도수치료예약.exe` 산출물 정합 (15MB + `_internal/` + `updater.bat`)
4. 19-1 ~ 19-13 신규 modules + 라우터 / 서비스 본체 git diff = 0 확인

## 19 (참고). Codex 가 반드시 확인할 체크리스트

- [ ] `pytest tests -q` 재실행 — 1671 통과 / 1 skipped / 10 xfailed
- [ ] `ruff check app tests scripts` — clean
- [ ] `scripts/check_db_path.py` — exit 0
- [ ] PyInstaller 빌드 명령 재실행 — exit 0
- [ ] `dist/도수치료예약/도수치료예약.exe` 산출물 존재 + 15MB
- [ ] `_internal/` + `updater.bat` 존재
- [ ] 마이그레이션 13 (m001 ~ m013) 자동 등록 로그
- [ ] 라우터 / 서비스 본체 git diff = 0
- [ ] `dosu_clinic.spec` git diff = 0 (19-13 등록 외)
- [ ] 휴무 차단 5/6/7 xfail = baseline 미구현 정합
- [ ] 11항목 매핑 표 정합

## 20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes — 단위화 리팩토링 1차 완료**. 

다음 세션 후보:
- 19-x 휴무 차단 백엔드 구현 (spec 02)
- 19-x AI 예약 / SMS 일괄 / 환자 등록 흐름 구현
- 19-x export_import `_dc_*` / Excel export 본체 분리
- 19-x 라우터 / 서비스 본체의 modules helper 채택 (라우터 비대화 해결)
- 또는 1차 완료 후 별도 release / 배포 / 회귀 모니터링 단계.

사용자 결정 대기.
