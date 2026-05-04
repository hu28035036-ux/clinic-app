# AI_COMMAND_ARCHITECTURE.md

> AI 명령 모듈 구조 / API 설계 / 상태값 / DB 로그 설계
> Phase 0 단계의 설계 문서이며, 실제 구현은 Phase 1부터 시작합니다.

---

## 1. 전체 구조

```
사용자 자연어 명령
   │
   ▼
┌──────────────────────┐
│ ai_parser            │ ← AI provider (외부 API)
└──────────┬───────────┘
           │ (구조화 JSON)
           ▼
┌──────────────────────┐
│ ai_resolver          │ ← DB (환자/치료사/치료항목/alias)
└──────────┬───────────┘
           │ (resolved 구조)
           ▼
┌──────────────────────┐
│ ai_validator         │ ← DB (예약/휴무)
└──────────┬───────────┘
           │ (validation 결과)
           ▼
┌──────────────────────┐
│ ai_preview           │
└──────────┬───────────┘
           │ (사용자 승인)
           ▼
┌──────────────────────┐
│ ai_safety            │ ← 최종 재검증
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ai_executor          │ ← 기존 서비스 로직 호출
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ai_audit             │ ← ai_command_logs
└──────────────────────┘
```

---

## 2. 추천 모듈 구조 (`app/ai/`)

| 파일 | 역할 |
|---|---|
| `ai_command_schema.py` | AI 명령 스키마 정의 (intent, 입력 필드, 상태값) |
| `ai_provider.py` | 외부 AI API 호출부 (provider 추상화, 교체 가능) |
| `ai_parser.py` | 사용자 자연어 명령 → 구조화 JSON |
| `ai_resolver.py` | AI 추출 텍스트 → DB 실제 값 매칭 |
| `ai_validator.py` | 예약 가능 여부 검증 (휴무/반차/중복/시간겹침/권한) |
| `ai_preview.py` | 사용자 승인 화면 데이터 생성 |
| `ai_executor.py` | 승인된 작업만 실행, 기존 서비스 로직 호출 |
| `ai_audit.py` | AI 명령 로그 저장 (`ai_command_logs`) |
| `ai_safety.py` | 금지 intent 차단, 승인 필요 여부 판단, 민감정보 필터, 할루시네이션 방지 |
| `ai_harness.py` | AI 명령 테스트 하네스 진입점 |

### 2.1 `ai_command_schema.py`

- intent, patient_name, chart_number, date_text, time_text, therapist_name, treatment_text, treatment_items, memo 정의
- 상태값(아래 § 3) 정의
- `treatment_items` 배열 구조 (§ 11)

### 2.2 `ai_provider.py`

- 외부 AI API 호출부 (예: Anthropic / OpenAI / 로컬 LLM)
- **로컬 LLM 없이도 외부 AI API로 동작 가능**
- 나중에 provider 교체 가능 (interface 추상화)
- API 키는 **환경변수 또는 관리자 설정**에서 읽음
- 실패 시 안전한 에러 반환 (기존 프로그램이 죽으면 안 됨)

### 2.3 `ai_parser.py`

- 자연어 → 구조화 JSON
- AI에게 **최소 정보**만 전달
- 환자 전체 목록 / 생년월일 전체 / 전화번호 전체 전달 금지
- 전달 가능한 컨텍스트:
  - 사용자 명령 원문
  - 현재 선택된 캘린더 월
  - 사용 가능한 intent 목록
  - 치료항목 이름 목록 (필요한 범위에서 최소화)

### 2.4 `ai_resolver.py`

- 환자명, 차트번호, 치료사명, 치료항목명, 치료항목 alias, 날짜, 시간 처리
- 환자 후보가 여러 명이면 **차트번호/이름/생년월일/연락처 후보 목록 생성**
- 모든 매칭은 **DB 기준**

### 2.5 `ai_validator.py`

- 휴무 / 반차 / 중복 / 시간겹침 / 권한 검증
- 신환 등록 중복 검사 설계 포함 (차트번호, 이름+생년월일, 이름+연락처, 연락처)
- 치료항목 다중 선택 / alias 충돌 검증 포함

### 2.6 `ai_preview.py`

- 사용자 승인 화면 데이터 생성
- 예약 후보, 변경 전·후 비교, 경고 메시지
- 환자 정보에 차트번호·이름·생년월일·연락처 포함
- "해당 날짜에 예약 등록할까요?" 메시지 포함

### 2.7 `ai_executor.py`

- 승인된 작업만 실행
- **DB 직접 조작 금지**
- 기존 예약/환자/휴무 서비스 로직 호출
- 승인 직전 최종 재검증 통과 후에만 실행

### 2.8 `ai_audit.py`

- `ai_command_logs` 저장
- 다음 항목을 모두 기록: **원본 명령 / AI 파싱 결과 / DB 매칭 결과 / 검증 결과 / 사용자 선택 (환자·치료항목) / 승인 여부 / 실행 결과 / 오류 메시지**
- 신환 등록과 예약 등록은 **각각 별도 로그**로 남김
- 상세 필드 정의는 § 5.1 (`ai_command_logs` 17필드) 참조

### 2.9 `ai_safety.py`

- 금지 intent 차단
- 승인 필요 여부 판단
- 민감정보 필터링 (외부 AI API에 PII 미전송)
- 할루시네이션 방지 규칙 적용

### 2.10 `ai_harness.py`

- AI 명령 테스트 하네스 실행 진입점
- 다음 10종 하네스 테스트와 연결 (상세는 `AI_HARNESS_PLAN.md` § 1):
  - parser / resolver / patient-candidate / validator / approval / executor / privacy / hallucination / regression / runtime
- 운영 환경에서는 권한 제한 (관리자 전용 / `POST /api/ai/harness/run`)

---

## 3. AI 명령 상태값

### 3.1 기본 상태

| 상태 | 설명 |
|---|---|
| `received` | 명령 수신 |
| `parsed` | AI 구조화 완료 |
| `needs_clarification` | 입력 부족, 사용자 확인 필요 |
| `validation_failed` | 검증 실패 |
| `needs_approval` | 사용자 승인 대기 |
| `approved` | 사용자 승인 완료 |
| `executed` | 실행 완료 |
| `rejected` | 사용자 거부 |
| `failed` | 실행 실패 |

### 3.2 환자 후보 관련 상태

| 상태 | 설명 |
|---|---|
| `patient_candidates_found` | 환자 후보 다수 검색됨 |
| `patient_selection_required` | 사용자 선택 필요 |
| `patient_selected` | 사용자 환자 선택 완료 |
| `patient_mismatch` | 차트번호와 이름이 서로 다른 환자를 가리킴 |

### 3.3 신환 흐름 상태

| 상태 | 설명 |
|---|---|
| `patient_not_found` | 환자 검색 결과 없음 |
| `patient_registration_proposed` | 신환 등록 제안 |
| `patient_registration_needs_approval` | 신환 등록 승인 대기 |
| `patient_registration_failed` | 신환 등록 실패 (중복 등) |
| `patient_registered` | 신환 등록 완료 |
| `appointment_needs_revalidation` | 신환 등록 후 예약 재검증 필요 |

### 3.4 치료항목 관련 상태

| 상태 | 설명 |
|---|---|
| `treatment_resolved` | 치료항목 매칭 완료 |
| `treatment_selection_required` | 사용자 선택 필요 |
| `treatment_alias_conflict` | alias가 여러 치료항목과 충돌 |
| `treatment_not_found` | 치료항목 매칭 실패 |

---

## 4. API 설계

### 4.1 `POST /api/ai/commands/parse`

- 사용자 명령 수신
- AI 파싱 + DB 매칭 + 검증
- 승인용 미리보기 반환
- **실제 실행 금지**

요청:
```json
{
  "raw_text": "박환자 4월30일 9시 도수30 주 충 예약해줘",
  "current_calendar_year": 2026,
  "current_calendar_month": 4
}
```

응답 예시:
```json
{
  "command_id": "cmd_xxx",
  "status": "needs_approval",
  "intent": "create_appointment",
  "preview": { ... },
  "candidates": { "patients": [...], "treatments": [...] },
  "validation": { ... }
}
```

### 4.2 `POST /api/ai/commands/{command_id}/select-patient`

- 환자 후보가 여러 명일 때 사용자가 선택
- 선택 후 해당 환자 기준으로 예약 후보 재검증
- **실제 예약 저장 금지**

### 4.3 `POST /api/ai/commands/{command_id}/select-treatment`

- 치료항목 후보가 여러 개일 때 사용자가 선택
- 선택 후 예약 후보 재검증
- **실제 예약 저장 금지**

### 4.4 `POST /api/ai/commands/{command_id}/approve`

- 사용자가 승인했을 때 호출
- **승인 직전 최종 재검증**
- 기존 서비스 로직으로 실행
- 로그 기록

### 4.5 `POST /api/ai/commands/{command_id}/reject`

- 사용자가 취소했을 때 호출
- `rejected` 상태 기록

### 4.6 `GET /api/ai/commands/{command_id}`

- 특정 AI 명령 상태/로그 조회

### 4.7 `GET /api/ai/commands/logs`

- 관리자용 AI 명령 로그 조회

### 4.8 `POST /api/ai/harness/run`

- 개발/관리자용 하네스 실행
- 운영 환경에서는 제한 권한 필요

### 4.9 신환 등록 관련 API (Phase 4에서 상세화)

- `POST /api/ai/commands/{command_id}/propose-new-patient`
- `POST /api/ai/commands/{command_id}/approve-new-patient`
- 신환 등록 후 예약은 별도 `/approve` 단계 필요

---

## 5. DB 로그 설계 — `ai_command_logs`

### 5.1 필드

| 필드 | 설명 |
|---|---|
| id | PK |
| user_id | 명령을 입력한 사용자 |
| raw_text | 원본 명령 |
| intent | 추출된 intent |
| status | 현재 상태값 (§ 3) |
| parsed_json | AI 파싱 결과 |
| resolved_json | DB 매칭 결과 |
| validation_result | 검증 결과 |
| preview_json | 미리보기 화면 데이터 |
| selected_patient_id | 사용자가 선택한 환자 |
| selected_treatment_items_json | 사용자가 선택한 치료항목 |
| approved_by | 승인자 (사용자 ID) |
| executed_result | 실행 결과 (예약 ID 등) |
| error_message | 실패 사유 |
| created_at | |
| updated_at | |
| executed_at | |

### 5.2 로그에 남길 것

- 원본 명령
- AI 파싱 결과
- DB 매칭 결과
- 환자 후보 목록 발생 여부
- 사용자가 선택한 환자
- 치료항목 alias 매칭 결과
- 사용자가 선택한 치료항목
- 검증 결과
- 사용자 승인 여부
- 실제 실행 여부
- 실패 사유

> **신환 등록과 예약 등록은 각각 별도 로그로 남깁니다.**

### 5.3 추천 보조 테이블 — `treatment_aliases`

| 필드 | 설명 |
|---|---|
| id | PK |
| treatment_id | 치료항목 FK |
| alias_name | 별칭 |
| created_at | |
| updated_at | |

---

## 6. AI Provider 추상화

### 6.1 인터페이스 (의사코드)

```python
class AIProvider(Protocol):
    def parse_command(
        self,
        raw_text: str,
        context: ParserContext,
    ) -> ParsedCommand: ...
```

### 6.2 구현체 후보

- `AnthropicProvider`
- `OpenAIProvider`
- `LocalLLMProvider` (옵션)
- `MockProvider` (테스트/하네스 전용)

### 6.3 운영 정책

- API 키는 환경변수 또는 관리자 설정에서 읽음 (코드 직접 저장 금지)
- API 호출 실패 시 기존 프로그램은 정상 동작해야 함
- timeout / retry 정책은 별도 문서 (`AI_SAFETY_POLICY.md`) 참조

---

## 7. 데이터 출처 상태 (할루시네이션 방지)

각 필드는 출처 상태를 가집니다.

| 상태 | 설명 |
|---|---|
| `ai_extracted` | AI가 사용자 문장에서 추출한 값 |
| `db_verified` | DB에서 확인된 값 |
| `user_confirmed` | 사용자가 직접 선택/확인한 값 |
| `system_resolved` | 시스템이 날짜/시간/치료항목 alias를 해석한 값 |
| `system_executed` | 실제 기존 서비스 로직으로 실행된 값 |

승인 화면에는 가능한 한 `db_verified` / `user_confirmed` / `system_resolved` 상태를 우선 표시합니다.

---

## 8. 호출해야 할 기존 서비스 로직 (재사용 원칙)

| AI intent | 호출 대상 |
|---|---|
| `create_appointment` | 기존 예약 생성 서비스 (직접 SQL 금지) |
| `update_appointment` | 기존 예약 수정 서비스 |
| `cancel_appointment` | 기존 예약 취소 상태 처리 로직 |
| `create_leave` | 기존 휴무/반차 등록 서비스 |
| `prepare_sms` | 기존 다음날 예약자 + 문자 내용 생성 로직 (발송 금지) |
| 신환 등록 | 기존 환자 등록 서비스 + 중복 검사 |

> **AI executor는 절대 직접 DB를 수정하지 않습니다.**

---

## 9. 외부 AI API에 보내는 정보 정책

(상세는 `AI_SAFETY_POLICY.md` 참조)

**전송 가능:**
- 사용자 명령 원문
- 현재 선택된 캘린더 월
- 사용 가능한 intent 목록
- 치료항목 이름 목록 (필요 범위 최소화)
- 치료항목 alias 목록 (필요 범위 최소화)

**전송 금지:**
- 환자 전체 목록
- 전화번호 전체 목록
- 생년월일 전체 목록
- 환자 상세 메모
- 민감한 진료 내용
- 전체 예약 데이터
- 전체 통계 원본

---

## 10. 기존 도메인 모듈 분리 (단위화 / 모듈화 원칙, 2026-05-03 추가수정사항 1)

AI 기능 추가 과정에서 기존 도메인 기능도 **역할별 분리**를 유지합니다.

### 10.1 권장 구조 (예시)

```
app/appointments/
├─ appointment_service.py       # 비즈니스 로직 (예약 생성/변경/취소)
├─ appointment_validator.py     # 휴무/중복/시간 겹침 검증
└─ appointment_repository.py    # DB 접근 (CRUD)

app/patients/
├─ patient_service.py           # 환자 등록/검색/수정
├─ patient_validator.py         # 차트번호/연락처/생년월일 중복 검사
└─ patient_repository.py        # DB 접근

app/treatments/
├─ treatment_service.py
├─ treatment_alias_service.py   # 치료항목 alias 관리
├─ treatment_validator.py
└─ treatment_repository.py

app/therapists/
├─ therapist_service.py
├─ leave_service.py             # 휴무/반차 등록
├─ leave_validator.py
└─ therapist_repository.py

app/messages/
├─ message_template_service.py
└─ reservation_message_service.py   # 예약문자 준비 (자동 발송 금지)

app/stats/
├─ stats_service.py
└─ stats_repository.py
```

### 10.2 적용 규칙

- 위 구조는 **권장 예시**입니다. 실제 파일 구조는 현재 프로젝트 구조에 맞게 조정해도 됩니다.
- 단, **역할별 분리 원칙은 반드시** 지킵니다.
- 기존 파일과 충돌이 있으면 무리하게 갈아엎지 말고, **안전한 범위에서 단계적으로 분리**합니다.
- 거대한 단일 파일 (`api.py` 등)이 있는 경우, AI 기능 도입과 함께 우선순위 모듈부터 점진적으로 분해 (refactor 19 시리즈와 정합).

### 10.3 AI 와의 관계

- AI 모듈(`app/ai/...`) 은 **위 도메인 service 를 호출**해 작업을 수행합니다.
- AI 모듈은 직접 repository / SQL / DB 를 호출하지 않습니다.
- 도메인 service / validator / repository 는 AI 도입 전에도 일관되게 유지됩니다.

---

## 11. 함수 단위화 원칙 (2026-05-03 추가수정사항 1)

각 함수는 **하나의 역할만** 합니다.

### 11.1 금지 (나쁜 예)

- `parse_and_resolve_and_validate_and_save()`
- `handle_ai_appointment_everything()`
- `process_all_ai_logic()`

→ 여러 단계를 한 함수에 몰아넣지 않습니다.

### 11.2 권장 (좋은 예)

- `parse_ai_command(raw_text, context) -> ParsedCommand`
- `resolve_patient(parsed) -> PatientResolution`
- `resolve_treatment_items(parsed) -> TreatmentResolution`
- `validate_appointment_candidate(resolved) -> ValidationResult`
- `build_appointment_preview(resolved, validation) -> Preview`
- `execute_approved_appointment(command_id, user) -> ExecutionResult`
- `write_ai_audit_log(command_id, payload) -> None`

### 11.3 작성 기준

1. 함수 하나가 너무 많은 일을 하지 않게 합니다.
2. DB 조회 / 검증 / 미리보기 생성 / 실행 / 로그 기록을 분리합니다.
3. 가능한 **순수 함수** (입력만으로 결과 결정) 와 DB 의존 함수를 구분합니다.
4. 오류 처리도 기능별로 분리합니다.
5. 주요 함수에는 **역할 주석**을 작성합니다 (§ 13).

---

## 12. UI 단위화 원칙 (2026-05-03 추가수정사항 1)

> 본 Phase 0 에서는 디자인 / UI 구현은 다루지 않습니다. 향후 UI 구현 시 단위화 원칙을 적용해야 함을 미리 명시합니다.

### 12.1 권장 컴포넌트 분리 (예시)

| 컴포넌트 | 역할 |
|---|---|
| `AiCommandInput` | 사용자 자연어 명령 입력창 |
| `AiResultPanel` | AI 처리 결과 / 상태 표시 영역 |
| `AiStatusBadge` | `received` / `parsed` / `needs_approval` 등 상태 뱃지 |
| `PatientCandidateList` | 동명이인 등 환자 후보 목록 (차트번호/이름/생년월일/연락처) |
| `TreatmentCandidateList` | 치료항목 후보 / alias 충돌 목록 |
| `NewPatientRegistrationPanel` | 신환 등록 입력·승인 패널 |
| `AppointmentPreviewCard` | 예약 후보 카드 (환자 정보 + 예약 정보 + 검증 결과) |
| `LeavePreviewCard` | 휴무 / 반차 후보 카드 |
| `AiValidationMessages` | 검증 결과 / 경고 메시지 |
| `AiActionButtons` | [취소] / [예약 등록] / [선택] 등 액션 버튼 묶음 |
| `AiAuditLogView` | 관리자용 AI 명령 로그 화면 |

### 12.2 적용 규칙

- 입력창 / 결과 영역 / 환자 후보 / 치료항목 후보 / 신환 등록 / 승인 카드 / 로그 화면을 **한 파일에 몰아넣기 금지**.
- 컴포넌트 이름은 실제 프론트엔드 구조에 맞게 조정 가능.
- 컴포넌트는 가능한 한 **읽기 전용 props** 를 받고, 상태 변경은 상위에서 관리 (Alpine.js / 서버 사이드 + 부분 client-side 구조와 정합).

---

## 13. 주석 작성 원칙 (2026-05-03 추가수정사항 1)

새로 추가하거나 크게 수정하는 파일·함수에는 **역할 주석**을 작성합니다.

### 13.1 주석 항목

1. 이 파일 / 함수가 담당하는 역할
2. 직접 DB 를 수정하는지 여부
3. 기존 service 를 호출하는지 여부
4. 승인 전 실행 금지와 관련된 안전 규칙
5. 개인정보 / API 전송 관련 주의사항
6. 테스트 또는 하네스 연결 지점

### 13.2 예시

```python
# ai_executor.py
# 사용자가 승인한 AI 명령만 실제 기존 서비스 로직으로 실행하는 모듈입니다.
# 이 모듈은 DB를 직접 수정하지 않고 appointment_service, patient_service, leave_service를 호출해야 합니다.
# 승인 직전 최종 재검증을 반드시 수행합니다.
# 외부 AI API에 환자 전체 / 생년월일 / 연락처 / 메모를 전달하지 않습니다.
# 하네스: tests/test_ai_executor.py, app/ai/ai_harness.py 의 Approval/Executor 시나리오.
```

### 13.3 과도한 주석 방지

- 코드를 그대로 풀어쓰는 주석은 작성하지 않습니다.
- "왜 이 방식인지", "안전 규칙", "재사용 대상" 처럼 **읽는 사람이 코드만 보고는 알 수 없는 정보**를 주로 기록합니다.

---

## 14. 기존 로직 재사용 원칙 (2026-05-03 추가수정사항 1)

AI 기능은 기존 로직을 **우회 금지**.

| AI intent | 재사용 대상 (기존 service / API) |
|---|---|
| `create_appointment` | 기존 예약 생성 service / API |
| `update_appointment` | 기존 예약 변경 service / API |
| `cancel_appointment` | 기존 예약 취소 상태 처리 로직 |
| `create_leave` | 기존 휴무 / 반차 등록 service / API |
| 신환 등록 | 기존 환자 등록 service / API |
| `analyze_stats` | 기존 통계 service / API 조회 결과 |
| `prepare_sms` | 기존 문자 생성 흐름 (자동 발송 금지) |

> AI 전용으로 DB 를 직접 insert / update / delete 하는 코드는 작성하지 않습니다.
