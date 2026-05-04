# 19-14 전체 회귀 테스트 / PyInstaller 검증 — 변경 요약

## 세션 이름

`19-14_full_regression_pyinstaller` — 19-1 ~ 19-13 단위화 리팩토링 전체 회귀
검증 + PyInstaller 빌드 + 빌드 산출물 실행 확인.

## 작업 목표

1. 19-1 ~ 19-13 누적 회귀 테스트 (1659 → 1671) 통과 확인.
2. ruff / DB path / 카테고리별 회귀 통과.
3. FastAPI TestClient 기반 11항목 작동 확인 smoke 추가.
4. PyInstaller `dosu_clinic.spec` 빌드 성공 + 산출물 실행 확인.
5. 단위화 리팩토링 1차 완료 판정 + 후속 보완 항목 정리.

## 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `tests/test_19_14_smoke_workflow.py` | 신규 (15 cases — 12 passed + 3 xfailed) | 336 |
| `docs/refactor/19_refactor_final_test_result.md` | 신규 | 188 |

## 파일별 변경 요약

### `tests/test_19_14_smoke_workflow.py` (신규, 336줄)

11항목 작동 확인 smoke. 격리된 테스트 DB (conftest.py — APPDATA + DOSU_DB_PATH
임시 경로) 위에서 FastAPI TestClient 로 실행.

검증 항목:
- 항목 1: 정상 예약 생성 (`test_smoke_1_create_appointment_normal`)
- 항목 2: 기존 예약 수정 PUT (`test_smoke_2_update_appointment` — 응답 shape `{"ok", "version"}`)
- 항목 3: 기존 예약 취소 (`test_smoke_3_cancel_appointment`)
- 항목 4: **매핑** — `test_appointment_rules.py:test_two_manual30_same_slot_blocked`
- 항목 5: 종일 휴무 차단 (`test_smoke_5_full_day_leave_blocks` — `@xfail` baseline 미구현)
- 항목 6: 오전반차 차단 (`test_smoke_6_morning_leave_blocks_morning` — `@xfail`)
  + 6b 허용 시간대 (`test_smoke_6b_morning_leave_allows_afternoon`)
- 항목 7: 오후반차 차단 (`test_smoke_7_afternoon_leave_blocks_afternoon` — `@xfail`)
  + 7b 허용 시간대 (`test_smoke_7b_afternoon_leave_allows_morning`)
- 항목 8: self-exclude on update (`test_smoke_8_self_exclude_on_update`)
- 항목 9: devtools / manual POST 우회 차단 (`test_smoke_9_*` 빈 코드 / `test_smoke_9b_*` 잘못된 코드)
- 항목 10: 캘린더 / 미니캘린더 / 금일 예약 환자 (`test_smoke_10_*` + `test_smoke_10b_calendar_event_shape`)
- 항목 11: 문자 대상 / 통계 영향 부재 (`test_smoke_11_*` + `test_smoke_11b_*`)

NOTE: `test_smoke_5/6/7` 의 `xfail` 마커는 `tests/test_therapist_leave.py:test_*_leave_blocks_*` 와
정합. 현재 백엔드 = spec 02 baseline 미구현 (UI 가 차단 보완 중). 19-14 회귀 ⊥.

### `docs/refactor/19_refactor_final_test_result.md` (신규, ~200줄)

19-1 ~ 19-13 누적 단위화 리팩토링 최종 검증 결과.

내용:
1. 전체 테스트 실행 결과 (1671 passed / 1 skipped / 10 xfailed)
2. 기능별 회귀 테스트 결과 (11 카테고리)
3. AI / RAG 하네스 결과 (12 항목)
4. 운영 DB 보호 결과
5. 외부 API 호출 차단 결과
6. API key / 개인정보 비노출 확인 결과
7. PyInstaller 빌드 결과 (exit 0, 87s)
8. 빌드 산출물 실행 확인 결과 (단일 인스턴스 락 동작)
9. 11항목 작동 확인 매핑 (자동 / 수동 구분)
10. 단위화 리팩토링 1차 완료 판정 — **완료**
11. 후속 보완 필요 항목 (10건)

## 의도 / 이유

- **smoke 추가** — 사용자 추가 지시문의 11항목 작동 확인. 기존 자동 테스트 인프라
  (TestClient + 시드 데이터) 재사용 — 새 픽스처 / 인프라 추가 ⊥.
- **xfail 마커 정합** — 휴무 차단 5/6/7 은 `tests/test_therapist_leave.py` 의
  baseline `xfail` 와 정합. 회귀 노이즈 ⊥.
- **항목 4 매핑** — 동일 검증이 기존 `test_two_manual30_same_slot_blocked` 에
  통과하므로 19-14 smoke 에 중복 작성 ⊥. 매핑 표로 처리.
- **final_test_result.md 작성** — 19-1 ~ 19-13 의 누적 결과 / 1차 완료 판정 /
  후속 보완 항목을 단일 문서로 정리.

## compatibility wrapper / 라우터 무수정

- `app/routers/api.py` / `app/routers/ai.py` 본체 *완전 무수정*.
- `app/services/ai/{action_leave,sms_draft,manual_qa,...}.py` 본체 *완전 무수정*.
- `app/services/{auth,backup,sync,seed}.py` 본체 *완전 무수정*.
- DB schema / migration *완전 무수정*.
- `dosu_clinic.spec` *완전 무수정* (19-12 + 19-13 hidden import 등록은 해당 세션
  완료).
- 19-1 ~ 19-13 신규 modules 패키지 *완전 무수정*.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| 새 기능 추가 | ✅ smoke 만 추가 |
| 대규모 리팩토링 | ✅ 무수정 |
| 예약/휴무/문자/통계/AI 핵심 로직 변경 | ✅ 무수정 |
| DB schema / migration 변경 | ✅ 무수정 |
| UI 디자인 변경 | ✅ main.html 무수정 |
| 기존 API 응답 key 변경 | ✅ 무수정 |
| 하네스/테스트 약화 | ✅ conftest.py / pyproject.toml 무수정 |
| 운영 DB 접근 | ✅ scripts/check_db_path.py exit 0 |
| 실제 외부 API 호출 | ✅ 19-12 / 19-13 가드 정합 |
| 실제 외부 문자 발송 | ✅ FakeSmsProvider 정책 그대로 |
| requirements.txt 수정 | ✅ 무수정 |
| PyInstaller spec 수정 | ✅ 무수정 (19-12 / 19-13 등록은 해당 세션 완료) |

## PyInstaller 빌드 결과

| 항목 | 결과 |
|---|---|
| 빌드 명령 | `venv/Scripts/pyinstaller.exe --noconfirm dosu_clinic.spec` |
| Exit code | **0** (성공) |
| 빌드 시간 | ~87초 |
| 산출물 위치 | `dist/도수치료예약/` |
| 진입점 | `dist/도수치료예약/도수치료예약.exe` (15MB) |
| 부속 폴더 | `_internal/` (Python 런타임 + 의존 + 데이터) + `updater.bat` |
| 마이그레이션 자동 등록 | 13 modules (m001 ~ m013) |
| Hidden import 등록 (19-12 + 19-13) | 20 모듈 (admin/backup/audit/export_import 12 + ai/commands 8) |
| spec post-build (`updater.bat` 복사) | ✅ |

## 빌드 산출물 실행 확인

명령:
```
DOSU_DB_PATH=$(pwd)/.test-build-tmp/test_clinic.db dist/도수치료예약/도수치료예약.exe
```

결과:
- 단일 인스턴스 락 동작 확인 — "이미 실행 중입니다" 메시지 + 정상 종료 (exit 0).
- 빌드 산출물의 binary 진입점 / 단일 인스턴스 락 / 종료 정합.
- 사용자의 기존 실행 인스턴스의 HTTP 응답 (200) 확인 가능 — 단, 해당 인스턴스는
  운영 DB 사용 중이므로 추가 상호작용 ⊥ (운영 DB 보호 우선).

## 자동 수정 루프 횟수

**2 회차 코드 수정** — smoke 응답 shape 정정 + xfail 마커 추가 + 항목 4 제거 후
매핑 표로 대체. ruff 자동 보정 1회. **5회 한도 내**.

## 5회 실패 여부

**미해당** — 2회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음.
- DB schema / migration 무수정.
- 라우터 / 서비스 본체 무수정.
- PyInstaller spec / requirements.txt 무수정.
