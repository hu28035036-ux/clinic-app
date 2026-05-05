# AI_CURRENT_DECISIONS.md

> **현재 기준으로 확정된 최신 의사결정**만 모아둔 단일 진실의 원천(Single Source of Truth).
> 과거 문서와 충돌이 있으면 본 문서를 우선합니다.
> 본 문서는 Phase가 진행되거나 추가수정사항이 들어올 때마다 갱신합니다.

---

## 1. 프로젝트 컨텍스트

- 본 프로그램은 **병원 예약관리 프로그램** (Windows 단독 실행, FastAPI + SQLAlchemy + SQLite + Jinja2 + Alpine.js).
- 도수치료 전용이 아니라 **치료항목 기반** 구조로 설계.
- AI 기능은 기존 기능을 깨지 않으며, 위험 작업은 전부 **승인형**으로만 동작.

---

## 2. 핵심 원칙 (확정)

1. AI는 **후보 생성**만 담당.
2. 프로그램이 **DB 기준 검증**을 담당.
3. 사용자가 **최종 승인**을 담당.
4. **기존 서비스 로직**이 실제 실행 담당 (AI executor는 직접 DB 수정 금지).
5. 모든 명령은 **로그 기록** (`ai_command_logs`).
6. 외부 AI API에는 **개인정보 최소화**, 환자 / 생년월일 / 연락처 / 메모 / 진료 내용 / 통계 원본 미전송.
7. API 키는 **환경변수 또는 관리자 설정**에서만 읽음 (코드 직접 저장 금지).
8. AI API 실패가 **기존 프로그램을 깨면 안 됨**.
9. AI는 **"예약 완료" 같은 단정 표현 금지**, "후보를 만들었습니다"로 표시.
10. **승인 직전 최종 재검증** 필수.

---

## 3. 환자 검색 / 식별 (확정)

- 검색 우선순위: 차트번호 → (차트+이름) → 이름 정확 → 이름 부분 → 동명이인 후보.
- 차트번호와 이름이 서로 다른 환자를 가리키면 `patient_mismatch`, 승인 불가.
- 동명이인이면 `patient_selection_required`, 사용자 선택 전 [예약 등록] **버튼 비활성화**.
- 환자 후보 / 승인 화면에는 **차트번호 / 이름 / 생년월일 / 연락처** 함께 표시.
- 생년월일·연락처는 **내부 DB에서만** 조회. AI에 전체 목록 미전송.

---

## 4. 신환 등록 (확정)

- 검색 결과 없음 → 신환 등록 제안.
- 사용자가 차트번호 / 이름 / 생년월일 / 연락처 입력.
- 중복 검사: 차트번호 / 이름+생년월일 / 이름+연락처 / 연락처.
- 중복 없으면 일반 직원 권한으로 등록 가능.
- 중복 무시 / 강제등록 / 환자 삭제 / 환자 병합 / 차트번호 변경은 **관리자 권한** 필요.
- 신환 등록 후 예약은 자동 저장 금지, **재검증 후** 별도 승인 필요.
- 신환 등록 / 예약 등록 **각각 별도 로그**.
- AI는 차트번호 / 생년월일 / 연락처를 **임의 생성 금지**.

---

## 5. 치료항목 / alias / 다중 입력 (확정)

- 예약은 **DB 등록 치료항목 기준**.
- 도수치료·체외충격파 등 특정 항목 **하드코딩 금지**.
- 약어 → DB / `treatment_aliases` 테이블 기준 매칭.
- 다중 치료항목은 `treatment_items` **배열 구조**로 처리.
- 명령 예시: "박환자 4월30일 9시 도수30 주 충 예약해줘" → 3개 치료항목 후보.
- 후보가 불명확하거나 alias 충돌이면 [예약 등록] **버튼 비활성화**.
- 매칭 우선순위: `treatment_id` → 정확 이름 → alias 정확 → 이름 부분 → 후보 다수 시 사용자 선택.

---

## 6. 날짜 해석 (확정)

- 오늘 / 내일 / 이번 주 X요일 / 다음 주 X요일 / 4월30일 / 5월10일 — 명시 기준.
- **"30일"** 같이 월이 빠진 경우 → **현재 선택된 캘린더 월** 기준으로 해석.
- 과거 날짜는 기본적으로 경고 또는 차단.
- 승인 화면에 **실제 해석된 날짜** 반드시 표시 ("30일을 2026년 5월 기준으로 해석했습니다").

---

## 7. 승인형 실행 게이트 (확정)

- Gate 1: 사용자 승인 (환자 1명 확정 + 치료항목 모두 확정 + 검증 통과).
- Gate 2: **승인 직전 최종 재검증** (시간 충돌 / 휴무 / 권한 재확인).
- 두 게이트 모두 통과해야 기존 서비스 로직 호출.

---

## 8. 절대 금지 (확정)

(상세는 `AI_SAFETY_POLICY.md` § 1)

- AI 직접 DB / SQL 수정.
- 승인 없는 예약 생성·변경·취소·휴무·신환 등록·문자 발송.
- 외부 AI API에 환자 전체 / 생년월일 / 연락처 / 메모 / 진료내용 전송.
- API 키 코드 직접 저장.
- 환자 / 예약 / 치료사 / 통계 임의 생성 (할루시네이션).
- AI API 실패 시 기존 프로그램 전체 오류.
- 기존 예약 / 통계 / 문자 / 완료체크 / 휴무 흐름 손상.
- `manual60` 카운트 정책 변경 (1카운트 유지).

---

## 9. 모듈 구조 (확정)

`app/ai/` 아래에 다음 모듈을 둡니다 (Phase 1부터 단계적으로 구현):

- `ai_command_schema.py`
- `ai_provider.py`
- `ai_parser.py`
- `ai_resolver.py`
- `ai_validator.py`
- `ai_preview.py`
- `ai_executor.py`
- `ai_audit.py`
- `ai_safety.py`
- `ai_harness.py`

기존 도메인(`app/appointments/`, `app/patients/`, `app/treatments/`, `app/therapists/`, `app/messages/`, `app/stats/`) 도 `service` / `validator` / `repository` 등 **역할별 분리**를 유지합니다.
실제 파일 구조는 현재 프로젝트 구조에 맞게 조정하되, **역할별 분리 원칙은 반드시** 지켜야 합니다.

상세는 `AI_COMMAND_ARCHITECTURE.md` § 2 (AI 모듈) / § 10 (기존 도메인 모듈) / § 11 (함수 단위화) / § 12 (UI 단위화) / § 13 (주석) / § 14 (기존 로직 재사용).

---

## 10. AI 명령 상태값 (확정)

기본 / 환자 후보 / 신환 / 치료항목 카테고리로 분리된 상태값.
상세는 `AI_COMMAND_ARCHITECTURE.md` § 3.

---

## 11. API 설계 (확정)

### 11.1 endpoint 목록

- `POST /api/ai/commands/parse`
- `POST /api/ai/commands/{id}/select-patient`
- `POST /api/ai/commands/{id}/select-treatment`
- `POST /api/ai/commands/{id}/approve`
- `POST /api/ai/commands/{id}/reject`
- `GET  /api/ai/commands/{id}`
- `GET  /api/ai/commands/logs`
- `POST /api/ai/harness/run`
- 신환 관련 API (Phase 4에서 상세화):
  - `POST /api/ai/commands/{id}/propose-new-patient`
  - `POST /api/ai/commands/{id}/approve-new-patient`

### 11.2 인증 정책 (v1.3.5+ 갱신)

| endpoint | 인증 정책 | actor_user_id |
|---|---|---|
| `POST /api/ai/commands/parse` | **선택적** — 일반 사용자 OK | 토큰 유효=admin / 미입력=anonymous / 무효=401 |
| `POST /api/ai/commands/{id}/select-patient` | 선택적 | 동일 |
| `POST /api/ai/commands/{id}/select-treatment` | 선택적 | 동일 |
| `POST /api/ai/commands/{id}/approve` | 선택적 | 동일 |
| `POST /api/ai/commands/{id}/reject` | 선택적 | 동일 |
| `GET  /api/ai/commands/{id}` | 선택적 | 동일 |
| `GET  /api/ai/commands/logs` | **관리자 엄격** | admin 만 |
| `POST /api/ai/harness/run` | 관리자 엄격 (진단용) | admin 만 |

- **선택적 인증** 의 의미: 토큰 *없으면* `anonymous` 로 진행 (일반 사용자도 AI 도우미 사용 가능). 토큰 *있는데 무효* 면 401 (silent ignore ❌, 보안).
- Gate 1 (사용자 승인) + Gate 2 (승인 직전 재검증) 은 그대로 보존 — 인증 정책 변경이 안전 정책 (`AI_SAFETY_POLICY` § 1.1.3~1.1.7) 에 영향 ⊥.
- 단일 원천: `app/routers/ai_commands_router.py:get_actor_user_id` (선택적) / `:require_admin` (엄격).
- audit log (`ai_command_logs.user_id`) 에 `admin` / `anonymous` 둘 다 저장되어 사후 추적 가능.

---

## 12. 검증 / 자동 진행 (확정)

- 각 Phase 종료 시: **Claude 자체 10회 검증** (2026-05-04 추가수정사항 4 — 5회 → 10회 확장) + **Runtime Test Report (실제 실행 기준)** + Codex 독립 검증 + Codex 독립 재검증 + **Codex Runtime 독립 재확인**.
- **Codex 최종 판단이 "통과"** 이고 **실제 작동테스트 정상 통과** 인 경우에만 다음 Phase 자동 진행.
- "조건부 통과" / "실패" 는 자동 진행 금지.
- 치명적 위험 항목이 있으면 조건부 통과여도 자동 진행 금지.
- **실제 작동테스트가 실패하면 다른 모든 항목과 무관하게 자동 진행 금지**.
- 사용자가 명시적으로 "중단 / 대기"를 요청하면 자동 진행 금지.
- **Codex 는 Claude Code 의 자체검증 결과 / Runtime Test Report / 수정 보고서를 모두 그대로 믿지 않고 독립적으로 확인** 합니다.
- **Claude Code 는 자만하지 않고 냉정하게 판단** 합니다 (2026-05-04 추가수정사항 4). 자체 검증 결과를 그대로 신뢰하지 않으며, "충분히 점검했다" 는 자기만족을 경계합니다.

---

## 13. 현재 Phase

- **Phase 0** (현재): 전체 설계 문서 작성 단계. 실제 구현 없음.
- 다음 단계: Phase 1 (스키마 + 로그 테이블 + provider 구조) — Phase 0 Codex 통과 후 자동 진행.

---

## 14. 갱신 정책

- 본 문서는 사용자의 추가수정사항이 들어올 때마다 갱신합니다.
- 갱신 이력은 `AI_REQUIREMENTS_OVERRIDES.md` 에 남깁니다.
- 본 문서가 다른 문서와 충돌하면 **본 문서를 우선**합니다.
- 다른 문서도 동일한 내용으로 함께 갱신해야 합니다.

---

## 15. 단위화 / 모듈화 원칙 (확정, 2026-05-03 추가수정사항 1)

AI 기능 전체 구조와 이후 코드 작성 / Phase 진행에 **공통**으로 강제됩니다.

### 15.1 기본 원칙

1. 한 파일에 기능을 몰아넣지 않습니다.
2. 역할별로 파일·함수·service·validator·resolver·repository·executor·harness 를 분리합니다.
3. 기존 기능을 대규모로 직접 수정하지 말고, 작은 단위로 확장합니다.
4. 기존 예약 / 환자 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크 로직을 **중복 구현 금지**.
5. AI 기능은 별도 모듈에서 **기존 service 로직을 호출**하는 방식으로 작성합니다.
6. AI executor 는 DB 직접 수정 금지, 기존 service 호출.
7. 각 모듈은 **단일 책임**을 가집니다.
8. 새 / 크게 수정한 파일·함수에 **역할 주석** 작성.
9. 각 모듈은 하네스 또는 테스트로 **독립 검증** 가능.
10. 기능 추가 후 기존 기능 회귀 검증 가능.

### 15.2 함수 단위화

- 거대 함수 금지: `parse_and_resolve_and_validate_and_save()` / `handle_ai_appointment_everything()` / `process_all_ai_logic()` 같은 통합 함수를 만들지 않습니다.
- 권장: `parse_ai_command()` / `resolve_patient()` / `resolve_treatment_items()` / `validate_appointment_candidate()` / `build_appointment_preview()` / `execute_approved_appointment()` / `write_ai_audit_log()` 처럼 **하나의 역할만**.
- DB 조회 / 검증 / 미리보기 생성 / 실행 / 로그 기록을 분리.
- 가능한 한 순수 함수(테스트 용이) 와 DB 의존 함수 구분.

### 15.3 UI 단위화 (디자인은 미실시, 향후 구현 시 권장)

- AiCommandInput / AiResultPanel / AiStatusBadge / PatientCandidateList / TreatmentCandidateList / NewPatientRegistrationPanel / AppointmentPreviewCard / LeavePreviewCard / AiValidationMessages / AiActionButtons / AiAuditLogView 같이 컴포넌트 단위로 분리.
- 입력창 / 결과 영역 / 환자 후보 / 치료항목 후보 / 신환 등록 / 승인 카드 / 로그 화면을 **한 파일에 몰아넣기 금지**.

### 15.4 Phase 단위화

- Phase 는 **작고 검증 가능한 단위**로 진행 (예: Phase 1 — 스키마 / 상태값 / 로그 / provider 까지만).
- 각 Phase 종료 시 하네스 / 런타임 / Codex 검증 통과 후 다음 Phase 진입.

### 15.5 단위화 완료 조건 (Phase 공통)

- 해당 Phase 기능이 역할별 모듈로 분리됨.
- 기존 기능을 우회하거나 중복 구현하지 않음.
- 새 함수·파일에 역할 주석 작성됨.
- 모듈은 하네스 또는 테스트로 검증 가능.
- 기존 기능 회귀 테스트 가능.
- Codex 단위화 검증 통과.

> 단위화가 부족해 한 파일 또는 한 함수에 로직이 과도하게 몰리면 해당 Phase 는 **완료로 보지 않습니다.**

---

## 16. 디자인 설계 / 적용 시점 원칙 (확정, 2026-05-03 추가수정사항 2)

### 16.1 디자인 적용 시점

- 현재 단계는 **디자인 설계 문서 작성만** 수행 (`AI_UI_UX_DESIGN_PLAN.md`, `AI_UI_STYLE_GUIDE.md`, `AI_DESIGN_TOKENS.md`).
- **실제 CSS / HTML / JS UI 코드는 수정하지 않습니다.**
- 실제 디자인 적용은 다음 조건이 **모두 충족된 뒤** 진행합니다.
  - AI 기능 전체 구조 설계 완료 (Phase 0)
  - AI 기능 Phase별 구현 완료 (Phase 1~5 최소)
  - AI 예약 도우미 / AI 휴무 도우미 / 환자 후보 선택 / 신환 등록 / 치료항목 후보 선택 / 최종 예약 승인 카드 / 관리자 AI 로그·하네스 구현 완료
  - 모든 Phase Runtime Test Report 작성 완료
  - Codex 재검증 통과
  - 기존 기능 회귀 검증 완료

### 16.2 디자인 변경 범위 (확정)

- 변경 대상: **시각 스타일** (색·여백·카드·표·버튼·입력·배지·폰트·여백) 만.
- 변경 금지: **탭 이름 / 메뉴 이름 / 기능 이름 / 필드 이름 / 화면 흐름 / 기능 위치 큰 구조**. 새 탭 추가 / 기능 삭제 금지.
- AI 도우미는 예약관리 / 휴무일관리 화면 **내부**에 카드 형태로 배치 (전용 탭 만들지 않음).
- 관리자 화면 **내부**에 AI 설정 / 로그 / 하네스 섹션 추가 가능 (관리자 탭 이름 변경 금지).

### 16.3 디자인 방향 (확정)

- 밝은 회색 배경 + 흰색 카드 + 진한 그린 / 차콜 그린 포인트.
- 깔끔한 SaaS / 관리자 대시보드 톤. 표 / 캘린더 가독성 최우선.
- 참고: [CompteExpress CRM Dashboard (Dribbble)](https://dribbble.com/shots/27338618-CompteExpress-CRM-Dashboard-Design) — **스타일 언어만 차용**, CRM 콘텐츠 / 용어 / 카드 구성은 차용하지 않음.

### 16.4 디자인 적용 우선순위 (확정)

| 순위 | 화면 |
|---|---|
| 1 | 예약관리 (AI 예약 도우미 포함) |
| 2 | 휴무일관리 (AI 휴무 도우미 포함) |
| 3 | 환자관리 |
| 4 | 통계 |
| 5 | 관리자 (AI 설정 / 로그 / 하네스 포함) |

### 16.5 우선순위 / 충돌

- 본 § 16 의 결정이 다른 디자인 문서와 충돌하면 **본 문서를 우선**합니다.
- 디자인 토큰 / 스타일 가이드 / 화면별 디자인 방향은 각각의 디자인 문서를 참조하되, 단일 진실의 원천은 본 문서.

---

## 17. 실제 작동테스트 / Runtime Test 강제 (확정, 2026-05-03 추가수정사항 3)

문서 검증·코드 검토와 **별개로**, 각 Phase 마다 실제 서버를 띄우고 클릭·API 호출까지 수행하여 다음을 확인합니다.

### 17.1 Runtime Test 점검 항목 (10개)

1. 서버가 정상 실행되는지
2. 화면이 정상 로딩되는지
3. 해당 Phase에서 추가한 기능이 실제 UI / API에서 동작하는지
4. 정상 케이스가 성공하는지
5. 실패 / 예외 케이스가 안전하게 처리되는지
6. **승인 전에는 DB가 변경되지 않는지** (parse / preview 단계 0건)
7. **승인 후에만 DB가 변경되는지** (approve 직후 정확한 row 변경)
8. 기존 예약 / 환자 / 치료사 / 의사 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크 기능이 깨지지 않았는지
9. AI API 실패 시 기존 프로그램이 정상 동작하는지
10. 결과를 `PHASE_XX_RUNTIME_TEST_REPORT.md` 로 기록했는지

### 17.2 Runtime Test 진행 금지 조건 (자동 진행 차단)

다음 중 하나라도 발생하면 다음 Phase 진행 금지:
- 실제 작동테스트 실패
- Runtime Test Report 누락
- 서버 실행 실패
- 화면 로딩 실패
- 승인 전 DB 변경 발생
- 승인 후 실행 실패
- 기존 핵심 기능 회귀 오류 발생

### 17.3 Codex 독립 재확인

- **Codex 는 Claude Code 의 Runtime Test Report 를 그대로 믿지 않고 독립적으로 동일 항목을 다시 확인**합니다.
- Codex Runtime 독립 재확인 결과가 Claude Code 의 보고서와 일치할 때만 다음 Phase 자동 진행 가능.
- 불일치 시 Claude Code 가 재테스트 / 재작성 후 Codex 재검증.

### 17.4 적용 시점

- Phase 0 은 코드 변경 없으므로 해당사항 없음.
- **Phase 1 부터 모든 Phase 에 강제** 적용.

> 상세는 `verification/AI_PHASE_VERIFICATION_SKILL.md` § 2.5.1 / § 4 / § 6.3 / § 7.1 참조.

---

## 18. 1~5차 AI 기능 13필드 정의 (확정, 2026-05-03 보강)

`AI_FEATURE_MASTER_PLAN.md` § 5 의 모든 AI intent 는 다음 **13개 필드**를 모두 정의합니다.

1. intent 이름
2. 사용자 명령 예시
3. 필수 입력값
4. 선택 입력값
5. DB 조회 필요 여부
6. 승인 필요 여부
7. 실행 가능 조건
8. 실행 금지 조건
9. 호출해야 할 기존 서비스 로직
10. 필요한 하네스 테스트 케이스
11. 실제 동작 확인 방법
12. 정상 케이스
13. 실패 / 예외 케이스

해당 intent (Phase 매핑):
- 1차 (Phase 2~5): `create_appointment`
- 2차 (Phase 7): `update_appointment` / `cancel_appointment`
- 3차 (Phase 8~9): `create_leave` / `prepare_sms`
- 4차 (Phase 10): `summarize_today` / `summarize_tomorrow` / `analyze_stats`
- 5차 (Phase 11): `data_quality_check` / `ops_assistant`

> 13필드가 누락된 intent 는 해당 Phase 진입 / 검증 통과 불가.

---

## 19. 검증 횟수 / 냉정한 판단 원칙 (확정, 2026-05-04 추가수정사항 4)

### 19.1 검증 횟수 조정

- **Claude Code 자체 검증 횟수: 5회 → 10회** 로 확장.
- 이유: Codex 사용량 제약 (사용량 한도 도달) 으로 Codex 가 모든 것을 잡아주지 못함을 전제. Claude Code 가 자체 검증의 최종 책임자가 됨.
- 적용: Phase 0 ~ Phase 11 모든 Phase 에 강제.

### 19.2 10회 검증 구성

| 회차 | 점검 영역 |
|---|---|
| 1 | 요구사항 + 단위화 (모듈 분리 / 거대 파일·함수 금지 / executor DB 조작 금지 / 도메인 중복 금지) |
| 2 | AI 안전정책 / 금지기능 |
| 3 | 개인정보 / API 키 / 외부 전송 |
| 4 | 기존 예약 / 통계 / 문자 / 완료체크 / 휴무 영향 |
| 5 | 하네스 / 로그 / 문서 / 주석 / 실제 작동테스트 (Runtime Test) |
| 6 | 단위화 / 모듈화 깊이 (단일 책임 / 우회 경로 / 독립 테스트) |
| 7 | Cross-doc 정합성 (4 진행 금지 조건 16셀 / 8 산출 / 10 모듈·하네스·API / 23 상태값 / 9 추출 필드) |
| 8 | 표현 / 명명 / 헤더 일관성 (백틱·볼드 / 추가수정사항 번호 / 도수치료 하드코딩 잔존) |
| 9 | 추가수정사항 반영 / SSOT 우선 (1·2·3·4 모두 반영 / 충돌 시 SSOT 우선 / 이력 기록) |
| 10 | **자만 없는 냉정한 최종 판단** |

### 19.3 자만 없는 냉정한 판단 원칙

Claude Code 는 다음 원칙을 따릅니다.

1. **자체 검증 결과를 그대로 신뢰하지 않습니다**. "검증 통과" 라고 판단했다고 해서 누락이 없다는 보장이 없습니다.
2. **"충분히 점검했다" 는 자기만족을 경계** 합니다. 추가 점검에서 새 누락이 발견될 가능성을 항상 인정합니다.
3. **미점검 영역을 적극 탐색** 합니다. 점검하지 않은 영역이 있는지 매 회차에 자문합니다.
4. **성과를 과장하지 않습니다**. "X 건 보완 완료" 가 아니라 "현재까지 X 건 발견 / 추가 누락 가능성 인정" 으로 표현합니다.
5. **Codex 사용량 제약을 인지** 합니다. Codex 가 모든 것을 잡아주지 못하므로 Claude Code 가 끝까지 책임 검증합니다.
6. **사용자가 검증 횟수를 늘린 의도** (자만 경계 / 끝까지 책임) 를 따릅니다.

### 19.4 적용 시점

- Phase 0 ~ Phase 11 모든 Phase 에 강제.
- 본 § 19 는 `verification/AI_PHASE_VERIFICATION_SKILL.md` § 2 (10회 검증) 와 `.claude/skills/ai-phase-verification/SKILL.md` § 2 와 정합되어야 합니다.

---

## 20. 현재 보류 / 미정 항목

- 사용할 외부 AI API provider (Anthropic / OpenAI / 기타) — Phase 1에서 결정.
- AI 응답 한국어 / 영어 — 한국어 응답 기본, Phase 2에서 검토.
- 하네스 데이터 fixture 형태 — Phase 6에서 결정.
- 추후 사용자 추가 지시에 따라 갱신.
