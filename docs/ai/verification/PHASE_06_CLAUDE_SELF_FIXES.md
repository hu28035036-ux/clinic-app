# PHASE_06_CLAUDE_SELF_FIXES.md

Phase 6 자체 10회 검증 중 Claude Code 가 발견 / 수정한 항목.

## 1. Phase 2 parser — `_extract_patient_name` false positive

### 발견 경로

Phase 6 통합 시나리오 테스트 (`test_pipeline_full_normal_path_single_patient`) 에서
"차트번호 12345 5월30일 9시 박치료사 도수30 예약" 같이 **환자명을 입력하지 않고 차트번호만**
사용한 명령에서 parser 가 `patient_name="도수"` 를 추출. resolver 가 chart=12345 →
박환자 (p1) 와 patient_name="도수" 를 비교해 `mismatch=True` 반환.

### 원인

`_extract_patient_name` 의 cleaning 단계는 치료사 / 의사 / 차트번호 / 시간 / 날짜
키워드만 제거. 치료항목 키워드 (`도수30`, `도30`, `체외`, `충격파`, `ESWT`,
`주사`, `주`, `충`, `운동`, `물리`, `도수치료\d+분`) 는 제거하지 않아
fallback 정규식 `re.search(r"([가-힣]{2,4})", clean)` 이 "도수" 매칭.

### 수정

`app/ai/ai_parser.py:_extract_patient_name` 의 cleaning 단계에 치료항목 / 메모 / "예약"
키워드 strip 추가.

```python
clean = re.sub(r"도수치료\s*\d*\s*분?", "", clean)
clean = re.sub(r"도수\s*\d+\s*분?", "", clean)
clean = re.sub(r"도\s*\d+", "", clean)
clean = re.sub(r"체외(?:충격파)?", "", clean)
clean = re.sub(r"충격파", "", clean)
clean = re.sub(r"(?i)eswt", "", clean)
clean = re.sub(r"운동", "", clean)
clean = re.sub(r"물리", "", clean)
clean = re.sub(r"주사", "", clean)
clean = re.sub(r"(?:^|\s)[주충](?=\s|$)", " ", clean)
clean = re.sub(r"\b예약\b", "", clean)
clean = re.sub(r"메모\s*[:：].*$", "", clean)
```

### 회귀 영향

- Phase 2 단위 테스트 49/49 통과 유지
- "박환자 4월30일 9시 도수30 예약" → patient_name="박환자" 그대로 동작
- "차트번호 12345 5월30일 9시 박치료사 도수30 예약" → patient_name=None 으로 정상 동작
  (resolver 가 chart 만으로 매칭 → match_rank=1)
- 기존 회귀 1955 + 신규 29 = 1984 passed / 0 failed

### 자만 없는 평가

- ❌ 다른 환자명 false positive 가능성 인정
  - 의사명 "박의사" 가 patient_name 으로 추출될 수 있는지 미검증 (의사 키워드 제거는 "치료사 / 의사" 둘 다 처리하지만 의사명 단독은 미검증)
  - 한자 / 영문 환자명 미지원 (현재 한글 2~4자만)
  - 메모에 한글 환자명 포함 시 충돌 가능 ("박환자 메모: 김민수 보호자 동행")
- ✅ Phase 6 통합 시나리오로 한 가지 false positive 는 잡음. 향후 Phase 에서 다른 사례 발견 시 동일 패턴으로 보강.

## 2. `check_hallucination` 의 `_FORBIDDEN_PHRASES` 단어 단위 정합

### 발견

초기에 `"환자입니다"` 를 금지 표현으로 추가했지만 일반 한국어 발화 ("박환자 환자입니다")
에 false positive 위험. AI_SAFETY_POLICY § 2.2 의 실제 금지 예시는
"예약 완료" / "환자 등록 완료" 같은 *완료 단정* 표현.

### 수정

```python
_FORBIDDEN_PHRASES = (
    "예약 완료했습니다",
    "예약 완료되었습니다",
    "예약 완료",       # AI_SAFETY_POLICY § 2.2 정합
    "환자 등록 완료",
)
```

### 회귀 영향

- Phase 6 hallucination 테스트 4/4 통과 유지
- "예약 후보를 만들었습니다. 승인하면 예약이 등록됩니다." → 위반 0
- "예약 완료했습니다." → 위반 1

### 자만 없는 평가

- ❌ AI_SAFETY_POLICY § 2.2 의 다른 표현 ("박치료사는 내일 가능합니다", "이분으로 보입니다") 은 미적용 — 향후 강화 가능
- ✅ Phase 6 범위에서는 가장 명확한 "완료 단정" 만 차단

## 3. `check_privacy_payload` 키 목록 결정

### 정합 확인

AI_SAFETY_POLICY § 3.2 의 외부 전송 금지 항목 7 종 (환자 전체 / 전화번호 / 생년월일 /
환자 메모 / 진료 내용 / 예약 데이터 / 통계 원본) → 12 키로 매핑:

| 정책 § 3.2 항목 | check_privacy_payload 차단 키 |
|---|---|
| 환자 전체 목록 | `patient_list`, `all_patients` |
| 전화번호 전체 | `all_phones`, `phone_list`, `patient_phone` |
| 생년월일 전체 | `all_birth_dates`, `birth_date_list`, `patient_birth_date` |
| 환자 상세 메모 | `patient_memo` |
| 민감한 진료 내용 | `appointment_memo` |
| 전체 예약 데이터 | `all_appointments` |
| 전체 통계 원본 | `all_stats` |

### 자만 없는 평가

- ❌ 키 이름 기반 검사 — 같은 의미를 다른 키로 보내면 우회 가능 (예: `all_patient_phones` → 차단되지만 `customer_phones` → 우회)
- ✅ 현재 ParserContext 구조는 본 키와 충돌 안 함. 향후 provider 가 전송하는 페이로드가 본 모듈을 통과해야 한다는 *런타임 강제* 는 미구현 (provider 구현체 수준에서 보장 필요)

## 종합

본 Phase 6 자체 검증은 다음 보완을 수행했습니다:

1. Phase 2 parser 의 환자명 false positive 1건 수정 (회귀 0)
2. `_FORBIDDEN_PHRASES` 단어 단위 정합 (false positive 위험 제거)
3. `check_privacy_payload` 키 목록 정책 매핑 검증

**현재까지 발견 1건 (parser false positive). 다른 false positive / 우회 가능성은 인정.**
