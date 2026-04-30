# 04. AI 자연어 휴무 등록 — 설계 확정

본 문서는 [docs/ai_action_leave_plan.md](../ai_action_leave_plan.md) 의 **세션 12 산출물**이다.
이 문서가 확정되면 13 세션부터는 이 spec 을 그대로 코드로 옮기기만 한다.

> ⚠️ **세션 13 적용 시 변경 사항** (사용자 결정으로 spec 과 다르게 구현됨):
> - 엔드포인트 **3 개** (`POST /api/ai/action/parse`, `POST /api/ai/action/preview`, `POST /api/ai/action/execute`).
>   본 spec § 1 의 "엔드포인트는 2 개" 와 다름. `parse` 는 LLM 추출만 하는 read-only 엔드포인트로 추가됨.
> - 경로 prefix **`/api/ai/action/*`** (본 spec § 8.1·8.2 의 `/api/ai/action/leave/*` 와 다름 — leave 세그먼트 없음).
> - intent 식별자 **`create_therapist_leave`** (본 spec § 2.2·7.1·8 의 `leave.create` 와 다름).
> - § 6.2 의 `Appointment.status != "cancelled"` (영국식 2L) 는 오타. 실제 DB 값은 **`"canceled"`** (미국식 1L) — [models.py:19](../../app/models/models.py:19) `APPT_STATUSES = ("reserved", "approved", "canceled")`.
>
> 그 외 모든 설계 (날짜 표 § 3, 매칭 § 5, 충돌 § 6, 토큰 § 7, 에러 코드 § 12, 할루시네이션 가드 § 11, 테스트 시나리오 § 13) 는 spec 그대로 적용.

> ⚠️ **세션 15 정정 사항** (DB 표준 정합화):
> - § 4.1 의 `leave_type` 값 표기 **`morning` / `afternoon`** 은 spec 작성 단계의 오해 — 실제 DB / 기존 API 표준은 **`am` / `pm`** (기존 캘린더 + `fetchLeavesOn()` 호환).
> - 15 세션에서 `_map_leave()` / `_VALID_LEAVE_TYPE` / `_leave_label()` / 시드 / 테스트 어서션 모두 **`am` / `pm` / `full`** 로 통일.
> - § 4.1·§ 7.1·§ 12 의 `morning` / `afternoon` 표기는 본 박스의 `am` / `pm` 으로 읽을 것.

상위 plan: [docs/ai_action_leave_plan.md](../ai_action_leave_plan.md)
관련 휴무 spec: [docs/specs/02_치료사_휴무_규칙.md](02_치료사_휴무_규칙.md)
관련 모델: [app/models/models.py](../../app/models/models.py) `Employee`, `EmployeeLeave`, `Appointment`, `AuditLog`, `AiUsageLog`
관련 라우터: [app/routers/ai.py](../../app/routers/ai.py), [app/routers/api.py](../../app/routers/api.py)

---

## 0. 한 줄 요약

자연어 → LLM 후보 추출 → 코드 결정론적 검증 → 미리보기 → 사용자 명시 클릭 → 기존 휴무 API 1 건 호출. **AI 는 DB 를 만지지 않는다.**

---

## 1. 자연어 명령 처리 흐름

엔드포인트는 **2 개** (plan 문서 기준): `preview` 와 `execute`. **`parse` 는 별도 엔드포인트가 아니라 `preview` 내부의 첫 번째 단계**다.

```
[사용자 입력]
"김테스트치료사 4월30일 종일 연차 등록해줘"
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ POST /api/ai/action/leave/preview                      │
│ ┌──────────────────────────────────────────────────┐   │
│ │ 1) 입력 사전 게이트 (코드)                         │   │
│ │   - 길이/문자 검증                                │   │
│ │   - 휴무 키워드 1개 이상 존재 ("휴무|연차|월차|   │   │
│ │     반차|휴가|쉼") — 없으면 LLM 호출 자체 안 함  │   │
│ │   - 다중 명령 차단 (",", "및", "와" 토큰 검출)   │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ 2) parse — LLM 1 회 호출                         │   │
│ │   - 시스템 프롬프트로 JSON 강제                  │   │
│ │   - Pydantic strict 검증 (extra=forbid)          │   │
│ │   - 후보 substring 검증 (입력에 없으면 차단)     │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ 3) 날짜 해석기 (코드 결정론, LLM 미사용)         │   │
│ │   - original_date_text → resolved_date           │   │
│ │   - assumption 한국어 안내 생성                  │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ 4) 치료사 매칭 (코드, DB read-only)              │   │
│ │   - 정규화 후 exact match 1 건만 통과            │   │
│ │   - 0 건/2 건↑ → 차단                            │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ 5) 휴무 유형 매핑 (코드)                         │   │
│ │   - 키워드 룰로 full/morning/afternoon 결정      │   │
│ │   - 모호 ("반차"만) → 차단                       │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ 6) 충돌/중복 체크 (코드, DB read-only)           │   │
│ │   - 같은 (employee_id, leave_date) 휴무 존재?    │   │
│ │   - 그 치료사의 그 날짜 예약 N 건?               │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ 7) preview_token 발급 (HMAC)                     │   │
│ │ 8) AiUsageLog 1 건 기록                          │   │
│ └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
       │
       ▼  candidate / warnings / safe_to_execute / preview_token
[UI 미리보기 카드]  ←  사용자가 읽고 확인
       │
       │  사용자 클릭 ("이대로 등록")
       ▼
┌────────────────────────────────────────────────────────┐
│ POST /api/ai/action/leave/execute                      │
│ - confirm=true 검증                                    │
│ - preview_token HMAC 재검증 + 만료 체크                │
│ - token payload 와 클라이언트 plan 일치 검증           │
│ - 트랜잭션 안에서 치료사/충돌 재조회 (TOCTOU 가드)     │
│ - 기존 함수 create_employee_leave() 직접 호출          │
│ - AuditLog (action="ai.leave.create") 기록             │
│ - AiUsageLog 1 건 기록 (feature="action_leave_execute")│
└────────────────────────────────────────────────────────┘
       │
       ▼
[성공 토스트] + 휴무 달력 reload
```

**핵심 원칙 재확인:**
- preview / execute 외 어떤 우회 경로도 두지 않는다.
- preview 만 단독 호출되어도 절대 DB write 일어나지 않음.
- execute 는 token 없이는 절대 동작하지 않음.

---

## 2. LLM 응답 JSON 스키마 (확정)

LLM 은 **분류·엔티티 추출만** 담당한다. 정규화·매칭은 코드.

### 2.1 시스템 프롬프트 (요지)

> 너는 한국 도수치료 클리닉의 휴무 등록 명령 분석기다.
> 입력은 한국어 한 문장이며, 한 명의 치료사에 대한 한 건의 휴무 등록 명령이다.
> 다음 JSON 스키마로만 응답하고 다른 텍스트는 출력하지 마라. 추가 필드 금지.
> 입력에 없는 정보를 만들어내지 마라. 모르면 `"unknown"` 으로 응답하라.

### 2.2 Pydantic 스키마 (서버 검증)

```python
class ParsedAction(BaseModel):
    model_config = {"extra": "forbid"}

    intent: Literal["leave.create"]
    employee_name_raw: str             # 입력에서 추출한 치료사 이름 토큰 그대로
    original_date_text: str            # 입력에서 추출한 날짜 표현 그대로
    leave_type_hint: Literal["full", "morning", "afternoon", "unknown"]
    leave_kind_hint: Literal["annual", "monthly", "unknown"]
    confidence: Literal["high", "low"]
```

### 2.3 LLM 출력 예시

입력: `"김테스트치료사 4월30일 종일 연차 등록해줘"`

```json
{
  "intent": "leave.create",
  "employee_name_raw": "김테스트치료사",
  "original_date_text": "4월30일",
  "leave_type_hint": "full",
  "leave_kind_hint": "annual",
  "confidence": "high"
}
```

### 2.4 LLM 결과 즉시 차단 조건

| 조건 | 차단 사유 | outcome |
|---|---|---|
| 응답이 JSON 파싱 실패 | LLM 출력 파괴 | `parse_fail` |
| Pydantic 검증 실패 (extra/missing/타입) | 스키마 위반 | `parse_fail` |
| `intent != "leave.create"` | 1차 범위 외 | `intent_mismatch` |
| `employee_name_raw` 가 입력 텍스트의 substring 이 아님 | 할루시네이션 (없는 이름 생성) | `hallucinated_name` |
| `original_date_text` 가 입력 텍스트의 substring 이 아님 | 할루시네이션 (날짜 변형) | `hallucinated_date` |
| `confidence == "low"` | 자체 신뢰도 낮음 | `low_confidence` |

차단 시 LLM 결과는 폐기하고 `safe_to_execute=false` 반환. **재시도 호출 금지** (비용·hallucination 누적 위험).

---

## 3. 날짜 해석 규칙 (확정, 코드 결정론)

해석기 위치: `app/services/ai/date_resolver.py` (13 세션 신설).
시간대: **`zoneinfo.ZoneInfo("Asia/Seoul")` 고정.** 서버 TZ 의존성 제거.

### 3.1 해석 표

| 입력 패턴 | 해석 | `assumption` 안내 (한국어) | `outcome` |
|---|---|---|---|
| `오늘` | today | 없음 | `ok` |
| `내일` | today + 1 | "내일 = 2026-05-01 로 해석했습니다" | `ok` |
| `모레` | today + 2 | "모레 = ..." | `ok` |
| `M월D일` (M ∈ 1~12) | (current_year, M, D) | M이 명시됐으므로 안내 없음 | `ok` |
| `D일` (월 생략) | (current_year, current_month, D) **단 D < today.day 면 차단** | "월이 생략되어 현재 월 기준 2026-04-30 로 해석했습니다" | `ok` 또는 `ambiguous_date` |
| `다음달 D일` | next month, D | "다음달 = 2026-05 기준 2026-05-30" | `ok` |
| `지난달 D일` | prev month, D | "지난달 = 2026-03 기준 2026-03-30" | `ok` |
| `이번주 X요일` | 이번주 해당 요일 (월=ISO weekday 1, 일=7) | "이번주 월요일 = 2026-04-27" | `ok` |
| `다음주 X요일` | 다음주 해당 요일 | "다음주 월요일 = 2026-05-04" | `ok` |
| `YYYY-MM-DD` (절대) | 그대로 | 없음 | `ok` |
| `말일쯤`, `이번주 중`, `다음에`, `곧`, `적당한 때`, `다음주`(요일 없음) | — | "날짜가 모호합니다" | `ambiguous_date` |
| 해당 월에 존재하지 않는 날짜 (`2월 30일`, `4월 31일`) | — | "해당 월에 없는 날짜입니다" | `invalid_date` |
| 윤년 위반 (`2026-02-29`, 비윤년) | — | "유효하지 않은 날짜입니다" | `invalid_date` |
| 과거 90 일 이전 | — | "과거 90 일 이전은 등록할 수 없습니다" | `out_of_range_date` |
| 미래 365 일 초과 | — | "미래 365 일을 넘는 날짜는 등록할 수 없습니다" | `out_of_range_date` |

### 3.2 응답 필드 (preview candidate 안)

| 키 | 예시 | 비고 |
|---|---|---|
| `original_date_text` | `"4월30일"` | 입력 그대로 |
| `resolved_date` | `"2026-04-30"` | YYYY-MM-DD |
| `date_basis` | `"explicit_md"` | 내부 분기용 (UI 표시 안 함) |
| `assumption` | `null` 또는 `"월이 생략되어 …"` | 일자만/상대/요일 케이스에서 **반드시** 채움. UI 강조 표시 |

### 3.3 설계 결정

- **"D일" + D < today.day 인 경우**: 다음달로 자동 보정하지 않고 모호 처리(차단). 사용자가 "다음달 D일"로 명시하도록 강제. 의도 추정 금지.
- **"M월D일" 의 연도 추론**: 항상 current_year. 90일 이상 과거가 되어도 자동으로 next_year 로 넘기지 않고 `out_of_range_date` 처리. 미래 일정만 등록 (사용자 정책).
- **"다음주 월요일"** 의 기준: ISO 주 (월요일 시작). 오늘이 일요일이라도 "다음주 월요일" = 내일이 아닌 8 일 후로 해석.

---

## 4. 휴무 유형 변환 규칙 (확정)

### 4.1 leave_type 매핑 ([spec 02 표준](02_치료사_휴무_규칙.md) 준수)

| 입력 한국어 키워드 | `leave_type` |
|---|---|
| `종일`, `하루`, `하루휴무`, `풀데이`, `연차`(타입 명시 없음), `월차`(타입 명시 없음), `휴무`(타입 명시 없음) | `full` |
| `오전반차`, `오전휴무`, `오전 반차` | `morning` |
| `오후반차`, `오후휴무`, `오후 반차` | `afternoon` |
| **`반차`** 만 있고 오전/오후 미지정 | **차단** (`ambiguous_half_day`) |

### 4.2 leave_kind 매핑

| 입력 한국어 키워드 | `leave_kind` |
|---|---|
| `연차`, `연차로`, 키워드 없음 (기본) | `annual` |
| `월차`, `월차로` | `monthly` |

### 4.3 결정 알고리즘 (의사코드)

```
def map_leave(text: str, llm_hint_type, llm_hint_kind) -> (leave_type, leave_kind, error):
    norm = lower_strip_spaces(text)

    # 1) leave_type — 코드 키워드 우선, hint 는 참고만
    if "오전반차" in norm or "오전휴무" in norm:
        leave_type = "morning"
    elif "오후반차" in norm or "오후휴무" in norm:
        leave_type = "afternoon"
    elif any(k in norm for k in ["종일", "하루", "풀데이", "하루휴무"]):
        leave_type = "full"
    elif "반차" in norm:
        return None, None, "ambiguous_half_day"
    elif any(k in norm for k in ["연차", "월차", "휴무", "휴가", "쉼"]):
        leave_type = "full"   # 타입 미지정 → 종일
    else:
        return None, None, "no_leave_keyword"

    # 2) leave_kind
    if "월차" in norm:
        leave_kind = "monthly"
    else:
        leave_kind = "annual"

    # 3) hint 와 코드 결과가 다르면 코드 결과 우선, AiUsageLog 에 mismatch 기록
    if llm_hint_type != "unknown" and llm_hint_type != leave_type:
        record_mismatch("leave_type", llm_hint_type, leave_type)

    return leave_type, leave_kind, None
```

---

## 5. 치료사명 매칭 규칙 (확정, 코드)

### 5.1 정규화 함수

```
def normalize_name(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "", s)            # 모든 공백 제거
    s = s.replace("선생님", "")
    s = s.replace("쌤", "")
    # 직책 접미사는 제거하지 않음 — '치료사' 자체가 이름의 일부일 수 있고,
    # 시드 데이터 (김테스트치료사 등) 가 그 형식이기 때문.
    return s
```

### 5.2 매칭 알고리즘

```
def match_therapist(db, raw_name: str) -> MatchResult:
    norm_input = normalize_name(raw_name)
    if len(norm_input) < 2 or len(norm_input) > 20:
        return MatchResult(status="invalid_name")

    # 1) 정확 일치 (active=True, role="therapist" 만)
    exact = db.query(Employee).filter(
        Employee.role == "therapist",
        Employee.active == True,
    ).all()
    matches = [e for e in exact if normalize_name(e.name) == norm_input]

    if len(matches) == 1:
        return MatchResult(status="ok", employee=matches[0])
    if len(matches) >= 2:
        return MatchResult(status="multi_match", candidates=matches)

    # 2) 정확 일치 0 건 — 비활성/다른 role 도 검색해서 사유 안내
    inactive = db.query(Employee).filter(
        Employee.role == "therapist",
        Employee.active == False,
    ).all()
    if any(normalize_name(e.name) == norm_input for e in inactive):
        return MatchResult(status="inactive_therapist")

    other_role = db.query(Employee).filter(Employee.role != "therapist").all()
    if any(normalize_name(e.name) == norm_input for e in other_role):
        return MatchResult(status="not_therapist")

    return MatchResult(status="no_match")
```

### 5.3 결정

- **부분/유사 매칭 절대 금지.** "박" 만 입력 → no_match.
- **동명이인 (active=True 정확 일치 ≥ 2)**: 1차에서는 차단. 후보 안내만 하고 사용자가 다시 입력 (구체적 식별자로). UI 라디오 선택 흐름은 1차 보류 (plan 문서의 "잘못 분석되면 취소→다시 입력" 흐름).
- **비활성/다른 role**: 명확한 한국어 사유 안내 ("퇴사한 치료사입니다" / "치료사가 아닙니다").
- LLM 의 `employee_name_raw` 가 정확히 입력의 substring 이므로, normalize 후 매칭 결과는 결정론적.

---

## 6. 중복 휴무 / 예약 충돌 검증 (확정)

### 6.1 동일 (employee_id, leave_date) 휴무 이미 존재

기존 `POST /api/employee-leaves` 는 같은 키면 **upsert** 동작 ([api.py:1098](../../app/routers/api.py)). AI 액션은 silent overwrite 를 막기 위해 다음을 수행:

| preview 단계 | 응답 |
|---|---|
| 기존 휴무 없음 | `mode: "create"`, `existing: null`, `safe_to_execute: true` |
| 기존 휴무 있음 (동일값) | `mode: "noop"`, `existing: {…}`, `safe_to_execute: true`, `warnings: ["이미 같은 내용으로 등록되어 있습니다"]` |
| 기존 휴무 있음 (다른값) | `mode: "overwrite"`, `existing: {…}`, `safe_to_execute: true`, `warnings: ["기존 휴무(오전반차/연차)를 종일/연차로 덮어씁니다"]` |

UI 는 `mode == "overwrite"` 일 때 **별도 체크박스** ("기존 휴무 덮어쓰기를 확인했습니다") 를 추가로 요구. 체크 전에는 "이대로 등록" 버튼 비활성.

### 6.2 해당 날짜 예약 충돌

같은 치료사가 그 날짜에 잡힌 예약이 있는지 조회:

```
appointments_count = db.query(Appointment).filter(
    Appointment.therapist_id == emp.id,
    func.date(Appointment.start_at) == resolved_date,
    Appointment.status != "cancelled",
).count()
```

- `appointments_count == 0` → 영향 없음.
- `appointments_count > 0` → `warnings: ["해당 날짜에 예약 N 건이 있습니다. 자동 이동/취소는 하지 않습니다 — 운영자가 별도 처리하세요"]`. **차단하지 않음** (warnings 만), 사용자가 인지하고 등록 진행 가능.

### 6.3 execute 시 재검증 (TOCTOU 가드)

execute 트랜잭션 진입 직후:

1. token 으로 복원한 `(employee_id, leave_date, leave_type, leave_kind, mode, existing_id_at_preview)` 와
2. 현재 DB 의 `(employee_id, leave_date)` 로 재조회한 결과를 비교.

| preview 시점 | execute 시점 | 처리 |
|---|---|---|
| `existing_id_at_preview == None` | 현재도 None | 정상 진행 (insert) |
| `existing_id_at_preview == None` | 현재 다른 휴무 발견 | 409 `conflict_changed` — 클라이언트는 preview 다시 호출 |
| `existing_id_at_preview == X` | 현재도 같은 X | 정상 진행 (upsert) |
| `existing_id_at_preview == X` | 다른 ID 또는 삭제됨 | 409 `conflict_changed` |

치료사 active 도 재조회. 사이에 비활성화되면 409 `therapist_changed`.

---

## 7. preview_token 포맷 / 서명 / 만료 (확정)

### 7.1 페이로드

```
payload_dict = {
    "v": 1,                           # 버전
    "intent": "leave.create",
    "employee_id": "emp_xxx",
    "leave_date": "2026-04-30",
    "leave_type": "full",
    "leave_kind": "annual",
    "mode": "create",                 # create | overwrite | noop
    "existing_id": null,              # overwrite/noop 시 기존 id
    "safe_to_execute": true,
    "exp": 1714500000                 # unix epoch (UTC)
}
payload_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
payload_b64  = base64.urlsafe_b64encode(payload_json.encode()).decode()
sig          = hmac_sha256(server_secret, payload_b64).hex()
preview_token = f"{payload_b64}.{sig}"
```

### 7.2 서명 키

- `server_secret`: 프로세스 시작 시 `secrets.token_bytes(32)` 로 생성, 메모리에만 보관.
- 재시작하면 모든 미완료 token 무효화 (안전한 기본값).
- DB / 환경변수에 저장하지 않음.

### 7.3 만료

- TTL **120 초.** preview 후 사용자가 2 분 안에 클릭하지 않으면 무효.
- execute 에서 `exp < now` 면 `token_expired` 반환, 클라이언트는 preview 재호출 필요.

### 7.4 검증 절차 (execute)

```
def verify_token(token: str, plan: dict) -> Payload:
    parts = token.split(".")
    if len(parts) != 2: raise InvalidToken("token_format")
    payload_b64, sig = parts
    expected_sig = hmac_sha256(server_secret, payload_b64).hex()
    if not hmac.compare_digest(sig, expected_sig): raise InvalidToken("token_signature")
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    if payload["exp"] < now_unix(): raise InvalidToken("token_expired")
    if not payload["safe_to_execute"]: raise InvalidToken("token_unsafe")
    # plan 변조 검증
    for k in ["employee_id", "leave_date", "leave_type", "leave_kind"]:
        if plan.get(k) != payload[k]:
            raise InvalidToken("token_mismatch")
    return payload
```

토큰 없는 execute / 변조된 토큰 / 만료된 토큰 / `safe_to_execute=false` 토큰 → 모두 400 (또는 401).

---

## 8. API 상세 설계

### 8.1 `POST /api/ai/action/leave/preview`

라우터: [app/routers/ai.py](../../app/routers/ai.py) 에 추가 (plan 문서 7.1 준수).
인증: 기존 ai 라우터의 `require_admin` 패턴 사용 (X-Admin-Token 헤더).
DB 수정: ❌ 없음.

**요청:**
```json
{ "text": "김테스트치료사 4월30일 종일 연차 등록해줘" }
```

**응답 (정상, mode=create):**
```json
{
  "ok": true,
  "outcome": "ok",
  "candidate": {
    "intent": "leave.create",
    "employee_name_raw": "김테스트치료사",
    "employee_id": "emp_abc",
    "employee_name": "김테스트치료사",
    "original_date_text": "4월30일",
    "resolved_date": "2026-04-30",
    "assumption": null,
    "leave_type": "full",
    "leave_kind": "annual",
    "memo": ""
  },
  "mode": "create",
  "existing": null,
  "appointments_count": 0,
  "warnings": [],
  "safe_to_execute": true,
  "preview_token": "eyJ2…==.a3b4…",
  "preview_token_exp": 1714500000
}
```

**응답 (모호 날짜):**
```json
{
  "ok": true,
  "outcome": "ambiguous_date",
  "candidate": null,
  "mode": null,
  "existing": null,
  "appointments_count": 0,
  "warnings": ["날짜가 모호합니다 — 구체적인 날짜를 입력해주세요"],
  "safe_to_execute": false,
  "preview_token": null,
  "preview_token_exp": null
}
```

**응답 (덮어쓰기):**
```json
{
  "ok": true,
  "outcome": "ok",
  "candidate": { "...": "..." },
  "mode": "overwrite",
  "existing": {
    "id": "lv_old",
    "leave_type": "morning",
    "leave_kind": "annual",
    "memo": ""
  },
  "appointments_count": 2,
  "warnings": [
    "기존 휴무(오전반차/연차)를 종일/연차로 덮어씁니다",
    "해당 날짜에 예약 2 건이 있습니다. 자동 이동/취소는 하지 않습니다"
  ],
  "safe_to_execute": true,
  "preview_token": "…",
  "preview_token_exp": 1714500000
}
```

### 8.2 `POST /api/ai/action/leave/execute`

라우터: 위와 동일.
인증: 동일.
DB 수정: ✅ EmployeeLeave 1 건.

**요청:**
```json
{
  "preview_token": "eyJ2…==.a3b4…",
  "confirm": true,
  "overwrite_acknowledged": false,
  "memo": ""
}
```

- `confirm` 가 `true` 가 아니면 즉시 400 `not_confirmed`.
- token 의 `mode == "overwrite"` 인데 `overwrite_acknowledged != true` 면 400 `overwrite_not_acknowledged` (UI 의 별도 체크박스 통과 강제).
- `memo` 는 사용자가 UI 에서 직접 입력한 값. AI 가 추출하지 않음 (PII 위험 회피).

**응답 (성공):**
```json
{
  "ok": true,
  "outcome": "ok",
  "leave_id": "lv_new123",
  "mode": "create",
  "message": "휴무가 등록되었습니다"
}
```

**응답 (실패):**
```json
{
  "ok": false,
  "outcome": "token_expired" | "token_mismatch" | "conflict_changed" | "therapist_changed" | "not_confirmed" | "overwrite_not_acknowledged",
  "message": "<한국어 한 줄>"
}
```

### 8.3 `GET /api/ai/action/leave/health` (14 세션, 선택)

기존 `GET /api/ai/health` 와 동일 구조 + 다음 추가 정보:
- `provider_ready`: bool (LLM 호출 가능)
- `therapist_count`: int (active 치료사 수, 0 이면 매칭 불가)
- `feature_enabled`: bool (AiSetting.enabled)

12 세션은 설계만, 13 세션 백엔드 작업 시 우선순위는 preview/execute. health 는 14 세션 또는 보류.

---

## 9. UI 위치와 미리보기 구조 (확정)

### 9.1 위치

[app/templates/main.html](../../app/templates/main.html) 의 **치료사 탭 → 휴무일 관리 서브탭** 영역에 "AI 휴무 등록" 카드 추가. (plan 문서 8.1 의 "메인 화면 AI 비서 박스" 와 위치 충돌 시, 휴무일 관리 영역이 컨텍스트상 가장 자연스럽다 — 14 세션에서 최종 결정. 12 세션은 둘 다 후보로 남김.)

대안 후보:
- A안: 치료사 탭 > 휴무일 관리 서브탭 안 (작업 컨텍스트와 가장 가까움) — 권장.
- B안: 메인 화면 우측 사이드 패널 (plan 문서 안) — 다른 AI 액션 추가 시 확장성 높음.

13 세션 백엔드 작업에는 영향 없음. 14 세션에서 확정.

### 9.2 와이어프레임

```
┌─────────────────────────────────────────────────────────┐
│ AI 휴무 등록                                          ▾ │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────┐     │
│ │ 예: 김치료사 4월30일 종일 연차                   │     │
│ │                                                 │     │
│ └─────────────────────────────────────────────────┘     │
│                                            [ 분석 ]     │
└─────────────────────────────────────────────────────────┘

분석 후:

┌─────────────────────────────────────────────────────────┐
│ 미리보기                                                │
├─────────────────────────────────────────────────────────┤
│  치료사 :  김테스트치료사                               │
│  날짜   :  2026-04-30  (원문: "4월30일")               │
│  유형   :  종일 (full)                                  │
│  종류   :  연차                                         │
│  메모   :  [ ____________________________ ]  (직접 입력)│
│                                                         │
│ ⚠ 월이 생략되어 현재 월 기준 2026-04-30 로 해석했습니다│  ← assumption
│ ⚠ 기존 휴무(오전반차/연차)를 종일/연차로 덮어씁니다   │  ← warning (overwrite)
│ ⚠ 해당 날짜에 예약 2 건이 있습니다 — 운영자가 처리 필요│  ← warning (예약)
│                                                         │
│  [ ] 기존 휴무 덮어쓰기를 확인했습니다  ← overwrite 시 │
│                                                         │
│            [ 취소 ]            [ 이대로 등록 ]          │
└─────────────────────────────────────────────────────────┘
```

### 9.3 안 만드는 것 (1 차)

- 채팅 UI / 멀티턴.
- 미리보기 결과 인라인 수정 (이름/날짜 직접 고치기) — 잘못 분석되면 취소→재입력만.
- 동명이인 라디오 선택 — 1차는 차단 + 사용자 재입력.
- preview 후 시간 카운터 — token 만료는 execute 시 처리.

### 9.4 Alpine.js 데이터 형태 (14 세션 참고)

```js
aiLeave: {
  text: "",
  loading: false,
  preview: null,        // preview 응답 객체
  memo: "",
  overwriteAck: false,
  async analyze() { /* POST preview, set preview */ },
  async submit()  { /* POST execute, reload calendar */ },
  reset()         { /* clear all */ }
}
```

---

## 10. AuditLog / AiUsageLog 기록 방식 (확정)

### 10.1 AiUsageLog (모든 시도)

[app/models/models.py:301](../../app/models/models.py:301) 그대로 사용.
프롬프트/응답 본문 저장 금지, 해시만.

| 호출 | feature | outcome 후보 | 비고 |
|---|---|---|---|
| `preview` 호출 | `action_leave_preview` | `ok` / `parse_fail` / `intent_mismatch` / `hallucinated_name` / `hallucinated_date` / `low_confidence` / `no_leave_keyword` / `multi_command` / `ambiguous_date` / `invalid_date` / `out_of_range_date` / `ambiguous_half_day` / `no_match` / `multi_match` / `inactive_therapist` / `not_therapist` / `provider_error` / `pii_blocked` | 매 호출 1 건 |
| `execute` 호출 | `action_leave_execute` | `ok` / `token_format` / `token_signature` / `token_expired` / `token_unsafe` / `token_mismatch` / `not_confirmed` / `overwrite_not_acknowledged` / `conflict_changed` / `therapist_changed` / `db_error` | 매 호출 1 건 |

기록 시:
- `prompt_hash` / `response_hash`: 입력 텍스트와 LLM 응답의 sha256 (preview 만).
- `prompt_chars` / `completion_chars`: 길이.
- `pii_filter_hits`: PII 가드 적중 수.
- `error_detail`: 짧은 한국어 (PII 미포함, 500 자 컷).
- 본문 평문 저장 절대 금지.

### 10.2 AuditLog (성공 실행만)

| 항목 | 값 |
|---|---|
| `action` | `"ai.leave.create"` |
| `entity_id` | 생성/갱신된 EmployeeLeave id |
| `actor` | 토큰에서 추출한 admin 식별자 (없으면 `"admin"`) |
| `detail` | `mode=create employee=김테스트치료사 date=2026-04-30 type=full kind=annual` 형식 (PII 미포함, 200 자 컷) |

execute 실패 (검증 차단) 는 AuditLog 안 남기고 AiUsageLog 의 outcome 으로 충분 (plan 문서 9.2).

### 10.3 로그 PII 정책

- 환자 이름·전화·생년월일·차트번호: AI 액션 흐름에 들어오지 않으므로 자연 제외.
- 직원 이름: AuditLog detail 에 포함 OK (이미 employee.upsert 등에서 동일하게 기록). AiUsageLog 평문 저장은 금지.
- 입력 텍스트: 해시만. error_detail 에 텍스트 일부 포함 시 길이 컷 + 정규식으로 숫자(전화번호 형) 마스킹.

---

## 11. 할루시네이션 차단 조건 (확정)

12 세션 합의:

| # | 가드 | 적용 시점 |
|---|---|---|
| 1 | 입력 길이 1~200 자, 휴무 키워드 1 개 이상 존재 | LLM 호출 전 |
| 2 | 다중 명령 토큰(`,`/`및`/`와/과` 사이 치료사 이름 둘 이상) | LLM 호출 전 |
| 3 | LLM 응답 JSON 파싱 + Pydantic strict (extra=forbid) | parse 직후 |
| 4 | `intent != "leave.create"` → 차단 | parse 직후 |
| 5 | `confidence == "low"` → 차단 | parse 직후 |
| 6 | `employee_name_raw` substring of input | parse 직후 |
| 7 | `original_date_text` substring of input | parse 직후 |
| 8 | LLM 의 날짜/타입 hint 는 무시, **코드가 다시 해석** | 4·5 단계 |
| 9 | 치료사 매칭 정확 일치 1 건만 통과 | 5 단계 |
| 10 | 모호 날짜·반차 미상·범위 초과는 무조건 차단 | 3·5 단계 |
| 11 | preview_token HMAC + 만료 + safe 플래그 + plan 일치 | execute |
| 12 | execute 트랜잭션 안 재조회 (TOCTOU) | execute |
| 13 | `confirm=true` + (mode=overwrite 시) `overwrite_acknowledged=true` | execute |

이 13 가드 중 **하나라도 실패하면 실행 안 됨.**

---

## 12. 에러 코드 ↔ 한국어 ↔ HTTP 일람

| `outcome` | HTTP | 한국어 사용자 메시지 |
|---|---|---|
| `ok` | 200 | (성공 — 메시지 없음 또는 "휴무가 등록되었습니다") |
| `no_leave_keyword` | 200 (preview) | "휴무 관련 키워드가 없습니다 (휴무·연차·월차·반차·휴가)" |
| `multi_command` | 200 (preview) | "한 번에 한 명, 한 건만 등록할 수 있습니다" |
| `parse_fail` | 200 (preview) | "AI 응답을 이해할 수 없습니다. 다시 시도해주세요" |
| `intent_mismatch` | 200 (preview) | "휴무 등록 명령이 아닌 것 같습니다" |
| `hallucinated_name` / `hallucinated_date` | 200 (preview) | "AI 응답이 입력과 일치하지 않아 거부되었습니다" |
| `low_confidence` | 200 (preview) | "AI 가 확신하지 못해 실행할 수 없습니다. 더 명확하게 입력해주세요" |
| `ambiguous_date` | 200 (preview) | "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요" |
| `invalid_date` | 200 (preview) | "유효하지 않은 날짜입니다" |
| `out_of_range_date` | 200 (preview) | "과거 90 일 ~ 미래 365 일 안의 날짜만 등록 가능합니다" |
| `ambiguous_half_day` | 200 (preview) | "오전/오후 반차 중 어느 것인지 명시해주세요" |
| `no_match` | 200 (preview) | "치료사를 찾을 수 없습니다" |
| `multi_match` | 200 (preview) | "동명이인이 있어 자동 등록할 수 없습니다 — 다른 식별자로 입력해주세요" |
| `inactive_therapist` | 200 (preview) | "퇴사/비활성 치료사입니다" |
| `not_therapist` | 200 (preview) | "치료사가 아닙니다" |
| `provider_error` | 503 | "AI 서비스에 일시적 문제가 있습니다" |
| `pii_blocked` | 200 (preview) | "입력에 개인정보로 보이는 내용이 있어 차단되었습니다" |
| `not_confirmed` | 400 (execute) | "확인이 필요합니다" |
| `overwrite_not_acknowledged` | 400 (execute) | "기존 휴무 덮어쓰기를 확인해주세요" |
| `token_format` / `token_signature` / `token_unsafe` / `token_mismatch` | 400 (execute) | "요청이 유효하지 않습니다 — 다시 분석해주세요" |
| `token_expired` | 400 (execute) | "분석 결과가 만료되었습니다 (2 분 초과) — 다시 분석해주세요" |
| `conflict_changed` / `therapist_changed` | 409 (execute) | "다른 사용자가 동시에 변경했습니다 — 다시 분석해주세요" |
| `db_error` | 500 (execute) | "저장 중 오류가 발생했습니다" |

> preview 의 비정상 outcome 은 **200 OK + safe_to_execute=false** 로 응답한다. 4xx 가 아니다 (분석 자체는 정상 동작이므로).

---

## 13. 테스트 시나리오 (확정)

15 세션 통합 테스트 + 13 세션 단위 테스트의 입력 시나리오:

### 13.1 정상 플로우
- T1: `"김테스트치료사 4월30일 종일 연차"` → preview ok create → execute ok → leave 1 건 생성, AuditLog 1 건, AiUsageLog 2 건.
- T2: `"이테스트치료사 내일 오전반차"` → resolved_date=내일, leave_type=morning.
- T3: `"박테스트치료사 다음주 월요일 오후반차"` → resolved_date=다음주 월요일, leave_type=afternoon.
- T4: `"김테스트치료사 30일 월차"` → assumption="월이 생략되어 …", leave_kind=monthly.

### 13.2 모호/차단
- T5: `"김치료사 말일쯤 휴무"` → ambiguous_date.
- T6: `"김테스트치료사 5월30일 반차"` → ambiguous_half_day.
- T7: `"김테스트치료사 2월30일 종일"` → invalid_date.
- T8: `"김테스트치료사 2024-01-01 종일"` → out_of_range_date (과거 90일↑).
- T9: `"김테스트치료사 2030-01-01 종일"` → out_of_range_date (미래 365일↑).
- T10: `"없는치료사 4월30일 종일"` → no_match.
- T11: `"퇴사한치료사 4월30일 종일"` (active=False seed) → inactive_therapist.
- T12: `"홍의사 4월30일 종일"` (role=doctor seed) → not_therapist.

### 13.3 충돌
- T13: 같은 (emp, date) 휴무 사전 존재 + 다른 type 입력 → mode=overwrite, warnings.
- T14: 같은 (emp, date) 같은 값 → mode=noop.
- T15: 그 날짜에 예약 2 건 → warnings 에 예약 알림.

### 13.4 보안/위조
- T16: token 없이 execute → 400 token_format.
- T17: 다른 페이로드로 위조한 token → 400 token_signature.
- T18: 만료된 token (exp 과거) → 400 token_expired.
- T19: preview 의 safe=false token 으로 execute → 400 token_unsafe.
- T20: token 의 employee_id 와 plan 의 employee_id 불일치 → 400 token_mismatch.
- T21: confirm=false → 400 not_confirmed.
- T22: mode=overwrite token + overwrite_acknowledged=false → 400 overwrite_not_acknowledged.
- T23: preview 후 다른 admin 이 같은 (emp, date) 변경 → execute 409 conflict_changed.
- T24: preview 후 치료사 비활성화 → execute 409 therapist_changed.

### 13.5 LLM 할루시네이션
- T25: mock LLM 이 입력에 없는 이름 반환 → hallucinated_name.
- T26: mock LLM 이 임의 날짜 텍스트 반환 → hallucinated_date.
- T27: mock LLM 이 intent="other" 반환 → intent_mismatch.
- T28: mock LLM 이 confidence="low" 반환 → low_confidence.
- T29: mock LLM 이 JSON 깨진 응답 → parse_fail.

### 13.6 회귀
- 기존 [tests/test_therapist_leave.py](../../tests/test_therapist_leave.py) 전부 PASS / XFAIL 유지.
- `run_check.bat` 통과 (pytest + ruff + DB 경로 안전검사).

### 13.7 LLM mock 정책

- 13 세션 단위 테스트 / 15 세션 통합 테스트에서 실제 OpenAI/Anthropic 호출 절대 금지.
- `app/services/ai/provider.py` 의 추상에 맞춰 `FakeProvider` 를 테스트에서 inject.
- 테스트 케이스별로 결정적 응답을 매핑.

---

## 14. 13 세션 진행 가능 여부

**가능.** 다음 사항이 확정되어 13 세션은 이 spec 을 그대로 코드로 옮기기만 하면 된다.

- LLM JSON 스키마 (§ 2)
- 날짜 해석 표 (§ 3)
- 휴무 유형/종류 매핑 (§ 4)
- 치료사 매칭 의사코드 (§ 5)
- 충돌·overwrite 정책 (§ 6)
- preview_token HMAC 포맷·만료 (§ 7)
- API 요청·응답 JSON (§ 8)
- 에러 코드 ↔ 한국어 ↔ HTTP (§ 12)
- 단위 테스트 시나리오 (§ 13)

13 세션 작업자가 추가로 결정해야 하는 사소한 항목:
- `app/services/ai/action_leave.py` 내부 함수 경계 (어디까지가 한 함수인지) — 자유.
- `FakeProvider` 의 구현 위치 — `tests/conftest.py` 또는 별도 fixture 파일.
- UI 위치 A/B 안 (§ 9.1) 은 14 세션에서 결정 — 백엔드 무관.

---

## 15. 변경되지 않은 plan 항목

본 spec 은 [plan 문서](../ai_action_leave_plan.md) 의 모든 핵심 안전 원칙과 보류 범위를 그대로 따른다. 변경 없음.

다만 다음은 plan 문서 본문에는 없었으나 본 spec 에서 새로 명시한 결정이다 (충돌 아님, 보강):

- preview_token 을 **HMAC-SHA256 + URL-safe base64 페이로드** 로 명시.
- `mode` (create/overwrite/noop) 개념 신설 — silent overwrite 차단.
- `overwrite_acknowledged` 별도 플래그 — UI 의 명시적 컨펌 강제.
- 할루시네이션 가드 13 항 명시.
- 에러 코드 일람 25+ 항 확정.
- 시간대 `Asia/Seoul` 고정.
- 동명이인은 1 차 보류 (plan 의 "0 명/2 명 이상 → 실행 불가" 와 동일하지만 UI 흐름까지 명시).
