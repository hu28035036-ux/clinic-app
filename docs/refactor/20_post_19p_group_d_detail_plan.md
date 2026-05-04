# 20-P-3 post-19-P 그룹 D 상세 기획 (20_post_19p_group_d_detail_plan)

> 20-P-1 [마스터 플랜](20_post_19p_master_plan.md) Codex 검증 caveat 정합 — "그룹 C/D 는 진입 전 별도 상세 기획 권장".
> 본 문서는 *그룹 D 4개 항목 (F-4 / F-5 / F-6 / F-9) 의 상세 기획* — read-only 문서 세션.
> 실제 코드 / 마이그레이션 / 테스트 / fixture / mock 미생성.

## 0. 메타

- 작성일: 2026-05-04
- 기준 브랜치: `ai-rag-v1-integration`
- 직전 commit: `6f152ac` (20-3-5 F-3 자원 — 그룹 C 5/5 완료)
- 20-3-5 baseline: **1825 passed / 1 skipped / 10 xfailed**
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.

### 0-1. 본 문서가 다루지 않는 범위

- 그룹 A/B/C 8개 항목 (이미 완료 또는 본 v1 비-도입).
- 그룹 C UI 후속 — 별도 문서 (`20_post_19p_group_c_ui_followup.md` 신설 후보).
- 실제 코드 / 마이그레이션 / 테스트 작성 — 20-4-1 ~ 20-4-4 분할 세션.
- 사용자 정책 결정 *최종 답* — 본 §3 ~ §6 에 후보만 정리.

### 0-2. 본 문서의 위치

- 20-P-1 = 부재 항목 15개 도입 마스터 플랜 (Codex 통과).
- 20-P-2 = 그룹 C 5개 상세 기획 (Codex 통과).
- **20-P-3 (본 문서) = 그룹 D 4개 상세 기획.**
- 20-4-1 ~ 20-4-4 = 그룹 D 분할 진입 (실제 코드 + 마이그레이션 + 테스트).

---

## 1. 그룹 D 4개 항목 개요 + 의존성

| 항목 | 마이그레이션 | UI | 외부 호출 | 위험 |
|---|---|---|---|---|
| F-5 출력물 (예약표 / 통계 / 환자안내) | ✗ (PDF 라이브러리 추가) | ✓ (출력 미리보기) | ✗ (내부 PDF 생성) | 중간 |
| F-6 export_import 확장 (CSV / EMR import) | ✗ | ✓ (import 화면) | ✗ | 중간 |
| F-4 알림 (내부 / 외부 채널) | m019 (Notification 테이블) | ✓ (알림 화면 / 설정) | **✓ (이메일 / Slack / 카카오 / SMS)** | **높음** |
| F-9 비트U차트 / EMR 연동 | m020 + 후속 (`EmrMapping`, `EmrSyncLog`) | ✓ | **✓ (EMR API)** | **최대** |

### 1-1. 의존성

| 의존 | 설명 |
|---|---|
| F-5 → F-4 (이메일 첨부) | 이메일 알림에 출력물 (PDF 예약확인서) 첨부 시 F-5 선행. 단순 알림은 F-5 없이 가능. |
| F-6 → F-9 | EMR import 는 기존 환자 데이터 변환이 필요 — EMR 연동 시 F-6 확장이 자연스러움. F-6 단독 도입 가능 (CSV 만). |
| F-4 (Slack/이메일) → 외부 인증 | API key / SMTP / Webhook URL 사용자 등록 필수. |
| F-9 → F-1 (doctors), F-3 (자원) | EMR 의사 / 진료실 매핑 필요. 본 시스템 F-1 (c) 가벼운 의사 + F-3 자원 v1 으로 *제한적 매핑* 만 가능. |

### 1-2. 진입 우선순위 (위험 / 외부 의존 / 가치)

1. **F-5 출력물** — 외부 호출 ⊥ + 내부 가치 高 (PDF 예약표 / 통계). 사용자 정책 (포맷) 결정만 필요.
2. **F-6 import 확장** — 외부 호출 ⊥. CSV 표준만 도입 시 빠름. EMR import 는 F-9 동반.
3. **F-4 알림** — 외부 채널 인증 필수. 단순 알림 (내부 큐 / 운영자 화면) 부터 단계적.
4. **F-9 EMR** — 가장 마지막. 사용자 EMR 벤더 결정 + API 인증 + F-1 + F-3 매핑 모두 필요.

---

## 2. 공통 원칙 (그룹 D 모든 항목)

| # | 원칙 | 본문 |
|---|---|---|
| GD-1 | 기존 33+ 응답 key 보존 | 신설만 허용. |
| GD-2 | 기존 API URL 보존 | 신설 endpoint (`/api/notifications`, `/api/reports/*`, `/api/import/*`, `/api/emr/*`). |
| GD-3 | 기존 m001~m018 변경 ⊥ | m019+ 만 신설. |
| GD-4 | 외부 인증 정보 비저장 (or 마스킹) | API key / SMTP password / OAuth token = `**` 마스킹 응답 + 평문 저장 ⊥ (암호화 또는 별도 secrets 파일). |
| GD-5 | 외부 호출 차단 (테스트) | `_block_sdk_modules` + provider mock 패턴 정합 (19-10 sms 정합). |
| GD-6 | 1825 baseline 회귀 ⊥ | |
| GD-7 | 운영 DB 보호 + PII 비노출 | |
| GD-8 | 19-C 14 영역 + 신규 P 영역 | 알림 / 출력물 / EMR import = P 영역 (20-P-1 §7-2). |
| GD-9 | Codex 검증 게이트 | 각 분할 (20-4-1 ~ 20-4-4) 마다 통과 후 다음. |
| GD-10 | 외부 채널 / EMR 결정 후 진입 | 사용자 인증 정보 / 벤더 결정 *전* 코드 진입 ⊥. |

---

## 3. F-5 출력물 — 20-4-1 상세

### 3-1. 현재 상태

- 엑셀 export 2개 존재 (`/api/export/manual-schedule.xlsx` / `/api/export/stats.xlsx`) — 19-11 stats 모듈에서 처리.
- PDF / HTML 출력 부재. 환자 안내문 / 예약확인서 / 통계 리포트 자동 생성 기능 부재.

### 3-2. 도입 후보

| 후보 | 포맷 | 라이브러리 | 시나리오 |
|---|---|---|---|
| (a) PDF | reportlab / weasyprint | requirements.txt 추가 | 환자 A 매뉴얼30 예약 → PDF 예약확인서 (병원명 / 날짜 / 환자명 / 치료사 / 시간) 자동 생성 → 환자 메일 첨부 또는 출력. |
| (b) Excel | openpyxl (이미 있음) | 추가 설치 ⊥ | 통계 리포트 Excel — 기존 export 와 통합 또는 확장. |
| (c) HTML | 내부 Jinja2 (이미 있음) | 추가 설치 ⊥ | 화면에 출력 미리보기 → 사용자가 인쇄 (Ctrl+P). 가장 간단. |
| (d) 모두 | (a) + (b) + (c) | 라이브러리 多 | 가장 풍부. 입력 UI 복잡. |

### 3-3. 출력 대상 후보

| 대상 | 시나리오 |
|---|---|
| 예약확인서 (1건) | 환자 A 예약 후 → PDF 발급 → 인쇄 또는 환자 메일 |
| 일자별 예약표 (전체) | 운영자 매일 아침 → "오늘 예약표" PDF 인쇄 |
| 주간 통계 리포트 | 매주 월요일 → 지난주 통계 PDF + 그래프 |
| 환자 안내문 (도수치료 주의사항) | 신환 등록 시 → PDF 안내문 발급 |
| 매출 리포트 | 월말 → 월간 매출 PDF |

### 3-4. 사용자 결정 필요 (20-4-1 진입 전)

| 결정 | 후보 | 권장 |
|---|---|---|
| 포맷 | (a) PDF (b) Excel (c) HTML (d) 모두 | **(a) + (c)** — PDF (예약확인서 / 안내문) + HTML 미리보기 (운영자) |
| 출력 대상 | 예약확인서 / 일자별 예약표 / 통계 리포트 / 안내문 / 매출 | 가장 자주 쓰는 것부터 — 권장 = **예약확인서 + 일자별 예약표** |
| PDF 라이브러리 | reportlab / weasyprint | reportlab (가벼움, 한글 폰트 임베드 가능) |
| 한글 폰트 | 시스템 기본 / 임베드 | 임베드 권장 (PyInstaller exe 호환) |

### 3-5. 마이그레이션

- 본 v1 = 마이그레이션 ⊥ (DB 변경 0). 출력물은 *예약 / 통계 데이터를 PDF 로 변환만*.

### 3-6. 응답 dict / API URL 영향

- 신설 endpoint:
  - `GET /api/reports/appointment/{aid}.pdf` — 예약확인서 PDF
  - `GET /api/reports/daily-schedule.pdf?date=YYYY-MM-DD` — 일자별 예약표
  - `GET /api/reports/stats.pdf?year=Y&month=M` — 통계 리포트 (HTML 미리보기와 동일 데이터)
- 응답 = `Content-Type: application/pdf` 바이너리 stream. JSON dict 아님.

### 3-7. 위험도

**중간**. PDF 라이브러리 추가 (requirements.txt 변경) + PyInstaller spec 갱신 (한글 폰트 데이터 파일 동봉) + 출력 템플릿 작성.

---

## 4. F-6 export_import 확장 — 20-4-2 상세

### 4-1. 현재 상태

- 엑셀 export 2개 + 환자 엑셀 import (`_dc_*` 약 600줄) 만 — 19-7 patients / export_import 분리됨.
- CSV import / 비트U차트 / EMR 표준 import 부재.

### 4-2. 도입 후보

| 후보 | import 포맷 | 시나리오 |
|---|---|---|
| (a) CSV import 추가 | 환자 CSV (이름 / 전화 / 생년월일 / 차트번호) | 사용자 → 엑셀 환자 명단을 CSV 저장 → 본 시스템 import → 자동 환자 등록. |
| (b) EMR 표준 (HL7 / FHIR) | HL7 v2 / FHIR R4 | 비트U차트 / 의사랑 EMR 의 표준 export 를 본 시스템에 import. |
| (c) 한국형 EMR (벤더 별) | 비트U차트 전용 / 의사랑 전용 | 사용자 EMR 벤더 결정 시 해당 포맷만 우선. |
| (d) 모두 | (a) + (b) + (c) | 매퍼 多 + 사용자 결정 多 |

### 4-3. 도수치료 실무 시나리오

> **상황**: 클리닉 신규 개원 시 기존 EMR 에 등록된 환자 100명을 본 시스템에 옮기고 싶음.

- (a) CSV — EMR 에서 CSV export → 본 시스템 import. **가장 단순**, EMR 무관.
- (b) EMR 표준 — EMR 가 HL7 / FHIR 지원해야 함. 한국 EMR 은 표준 지원 ⊥ 多.
- (c) 한국형 EMR — 벤더별 매퍼 작성. 비트U차트 등 *주요 EMR* 만.

### 4-4. 사용자 결정 필요 (20-4-2 진입 전)

| 결정 | 후보 | 권장 |
|---|---|---|
| import 포맷 | (a) CSV (b) HL7/FHIR (c) 벤더별 | **(a) CSV** — 가장 단순, EMR 무관 |
| import 항목 | 환자 / 예약 / 치료사 / 통계 | **환자만** v1 (예약은 후속) |
| 중복 검사 | (i) 차트번호 (ii) 이름+생년월일 (iii) 모두 | (iii) — patients.rules._check_patient_duplicate 재사용 |
| 실패 정책 | (i) 1건 실패 시 전체 rollback (ii) skip + 응답 안내 | (ii) — 사용자가 부분 import 후 수동 처리 |

### 4-5. 마이그레이션

- 본 v1 = 마이그레이션 ⊥ (기존 Patient 테이블 사용).

### 4-6. 응답 dict / API URL 영향

- 신설 endpoint:
  - `POST /api/import/patients-csv` (multipart/form-data) — CSV 파일 업로드 → 환자 import
  - 응답: `{created: [pid...], skipped: [{row, reason}...], errors: [...]}`

### 4-7. 위험도

**중간**. CSV 파싱 + 중복 검사 + 트랜잭션 안전성 (대량 import 시 5000건+ 가능). 19-7 export_import 모듈에 통합.

---

## 5. F-4 알림 — 20-4-3 상세

### 5-1. 현재 상태

- 알림 시스템 부재. 백업 실패 / reindex 실패 시 운영자가 *수동 확인* 필요.
- 환자에게는 SMS 만 (19-10 sms 모듈) — 외부 채널 다양화 ⊥.

### 5-2. 도입 후보 — **사용자 채널 결정 필수**

| 후보 | 채널 | 시나리오 |
|---|---|---|
| (a) 내부 알림만 | UI 알림 화면 | 백업 실패 → "알림" 화면에 빨간 점 → 운영자 클릭 → 처리. **외부 호출 ⊥**. |
| (b) 이메일 | SMTP (Gmail / 자체 서버) | 운영자 메일에 알림. SMTP 인증 정보 (host / port / user / password) 필수. |
| (c) Slack | Webhook URL | Slack 채널에 알림. Webhook URL 사용자 등록. |
| (d) 카카오톡 | 카카오 알림톡 API | 환자 / 운영자에게 카카오톡. 카카오 비즈 인증 필수. |
| (e) SMS | 기존 19-10 sms 재사용 | 운영자 휴대폰. 문자나라 비용 발생. |
| (f) 다중 | (a) + (b) + ... | 사용자 채널별 결정 |

### 5-3. 알림 이벤트 후보

| 이벤트 | 시나리오 |
|---|---|
| 백업 실패 | 자동 백업이 디스크 부족 / 권한 문제 → 운영자 즉시 알림 |
| reindex 실패 | RAG 매뉴얼 reindex 실패 → AI 검색 영향 → 알림 |
| 노쇼 발생 | 환자 A 노쇼 처리 → 운영자 알림 (다른 환자 슬롯 가능 등) |
| 매뉴얼 검색 부재 | AI 가 답을 못 찾은 질문이 N건 누적 → 매뉴얼 보강 알림 |
| 사용자 정의 | 시간대별 / 치료사별 등 |

### 5-4. 사용자 결정 필요 (20-4-3 진입 전 — 가장 큰 결정)

| 결정 | 후보 | 비고 |
|---|---|---|
| 채널 | (a) 내부만 (b) 이메일 (c) Slack (d) 카톡 (e) SMS (f) 다중 | **외부 채널 = 인증 정보 사용자 등록 필수**. v1 = (a) 내부만이 가장 안전. |
| 이벤트 | 백업 실패 / reindex 실패 / 노쇼 / 매뉴얼 부재 / 사용자 정의 | 단계별 — v1 = 백업 / reindex 부터 |
| 외부 호출 정책 | (i) provider mock fallback 보존 (ii) 실제 발송 가능 | 19-10 sms 정합 — provider mock 보존 |

### 5-5. 마이그레이션

```sql
CREATE TABLE notifications (
    id VARCHAR(32) PRIMARY KEY,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(10),  -- info / warning / error
    event_type VARCHAR(50), -- backup.failed / reindex.failed / patient.noshow ...
    message TEXT,
    channel VARCHAR(20),    -- internal / email / slack / kakao / sms
    sent INTEGER DEFAULT 0,
    sent_at DATETIME,
    read_at DATETIME
);
```

### 5-6. 응답 dict / API URL 영향

- 신설 endpoint:
  - `GET /api/notifications?unread_only={bool}` — 알림 목록
  - `POST /api/notifications/{nid}/read` — 읽음 표시
  - `POST /api/notifications/test` — 채널 테스트 (외부 채널 결정 시)

### 5-7. 위험도

**높음**. 외부 채널 = 인증 정보 + provider mock + 실제 발송 비용 + 운영 위험. v1 = (a) 내부만 권장.

---

## 6. F-9 EMR 연동 — 20-4-4 상세 (가장 마지막)

### 6-1. 현재 상태

- EMR 연동 부재. 본 시스템은 *도수치료 전문* — 일반 진료 EMR 와 분리.
- F-1 (c) 가벼운 의사 결정 → Doctor 별도 테이블만, Department / Room 부재.
- 환자 정보는 본 시스템 내부 (Patient 테이블) — EMR 와 매핑 부재.

### 6-2. 도입 후보 — **사용자 EMR 벤더 결정 필수**

| 후보 | EMR | 시나리오 |
|---|---|---|
| (a) 패스 | EMR 미연동 | **현재 도수치료 전문 유지**. EMR 도입 의도 없음. |
| (b) 비트U차트 | 비트U차트 API | 한국 1차 의원 EMR. API 표준 부재 — 벤더 협업 필요. |
| (c) 의사랑 | 의사랑 API | 한국 일반 의원. 동상. |
| (d) FHIR R4 | 표준 HL7 FHIR | 국제 표준. 한국 EMR 가 FHIR 지원해야 함. |
| (e) 사용자 정의 | 사용자가 EMR 벤더 명시 | 벤더별 매퍼 작성. |

### 6-3. 도수치료 실무 시나리오

> **상황**: 본 시스템 + 일반 EMR (비트U차트) 동시 운영. 환자 A 가 EMR 에서 진료 → 도수치료 처방 → 본 시스템 예약. 양쪽 환자 정보 동기화 필요.

- (a) 패스: 운영자가 양쪽 시스템 *수동 입력*. 본 v1.
- (b)~(e): EMR 와 본 시스템 환자 ID 매핑 + 진료 → 예약 자동 연동.

### 6-4. 사용자 결정 필요 (20-4-4 진입 전 — 가장 큰 결정)

| 결정 | 후보 | 비고 |
|---|---|---|
| EMR 도입 의도 | (a) 패스 (b) 비트U차트 (c) 의사랑 (d) FHIR (e) 사용자 정의 | **현재 도수치료 전문 — (a) 패스 우선 권장** |
| 동기화 방향 | EMR → 본 시스템 / 본 시스템 → EMR / 양방향 | (b)+ 도입 시 단방향 (EMR → 본) 우선 |
| 환자 ID 매핑 | (i) 새 EmrMapping 테이블 (ii) Patient.emr_id 추가 | (i) — 매핑 별도 도메인 |
| 예약 연동 | (i) EMR 진료 시 자동 예약 (ii) 수동 매핑 | (ii) — 안전 시작 |

### 6-5. 마이그레이션 (사용자 (b)+ 결정 시)

```sql
CREATE TABLE emr_mappings (
    id VARCHAR(32) PRIMARY KEY,
    vendor VARCHAR(20),
    emr_patient_id VARCHAR(50),
    patient_id VARCHAR(32),  -- FK
    created_at DATETIME
);
CREATE TABLE emr_sync_logs (
    id VARCHAR(32) PRIMARY KEY,
    ts DATETIME,
    direction VARCHAR(10),  -- import / export
    entity_type VARCHAR(20),
    entity_id VARCHAR(32),
    status VARCHAR(10),
    error TEXT
);
```

### 6-6. 응답 dict / API URL 영향 (사용자 (b)+ 결정 시)

- 신설 endpoint:
  - `POST /api/emr/sync` — EMR 동기화 트리거
  - `GET /api/emr/mapping/{patient_id}` — 매핑 조회
  - `GET /api/emr/sync/logs` — 동기화 로그

### 6-7. 위험도

**최대**. 외부 EMR 벤더 결정 + API 인증 + 매핑 정책 + F-1 / F-3 의존 + 양 시스템 데이터 정합성. 본 시스템이 *도수치료 전문* 유지하면 (a) 패스.

---

## 7. 진입 순서 권장

### 7-1. 표준 진입 순서

1. **20-4-1 F-5 출력물** — 외부 호출 ⊥, 내부 가치 高. PDF + HTML 권장. 사용자 §3-4 결정 후.
2. **20-4-2 F-6 import 확장** — CSV import (외부 호출 ⊥). 사용자 §4-4 결정 후.
3. **20-4-3 F-4 알림** — v1 = (a) 내부만 권장. 외부 채널 (이메일 / Slack / 카톡) 은 사용자 인증 정보 결정 후 단계적.
4. **20-4-4 F-9 EMR** — **(a) 패스 우선 권장**. 도수치료 전문 유지 시 진입 ⊥.

### 7-2. 분할 vs 묶음 진입

- 권장: **분할** (각 분할마다 Codex 검증 + commit). 4개 분할 = 4 commits.
- 묶음 진입 ⊥ — 외부 채널 + EMR 결정 다수 + 위험 가중.

---

## 8. 응답 key / API URL 요약

| 그룹 | 신설 응답 key | 신설 API URL |
|---|---|---|
| F-5 | (없음 — 바이너리 PDF stream) | `/api/reports/{type}.pdf` 등 |
| F-6 | `created` / `skipped` / `errors` | `POST /api/import/patients-csv` |
| F-4 | `Notification` 테이블 응답 | `/api/notifications` + `/api/notifications/{nid}/read` + `/api/notifications/test` |
| F-9 | `EmrMapping` / `EmrSyncLog` 응답 | `/api/emr/sync` + `/api/emr/mapping/{pid}` + `/api/emr/sync/logs` |

기존 33+ 응답 key: 모두 보존.

---

## 9. UI 영향

| 그룹 | UI 변경 |
|---|---|
| F-5 | 출력 버튼 (예약 카드 / 통계 / 환자 카드) + 미리보기 / PDF 다운로드 |
| F-6 | 환자관리 화면에 CSV import 버튼 + 결과 모달 |
| F-4 | 우측 상단 알림 종 아이콘 (뱃지) + 알림 드롭다운 / 알림 화면 |
| F-9 | 환자 카드에 EMR 매핑 표시 + 동기화 버튼 + 동기화 로그 화면 |

기존 main.html JS / FullCalendar 무수정 — *추가만*.

---

## 10. 위험도 종합

| 분할 | 위험 | 마이그레이션 | 외부 호출 | 사용자 결정 |
|---|---|---|---|---|
| 20-4-1 F-5 출력물 | 중간 | 0 (라이브러리 추가) | ⊥ | 포맷 / 대상 |
| 20-4-2 F-6 CSV import | 중간 | 0 | ⊥ | 포맷 / 중복 / 실패 |
| 20-4-3 F-4 알림 | **높음** | m019 | **사용자 채널 결정 시 ✓** | 채널 / 이벤트 / 인증 |
| 20-4-4 F-9 EMR | **최대** | m020+ | **EMR API ✓** | EMR 벤더 / 매핑 / 동기화 방향 |

---

## 11. 검증 패턴 (19-C 14 영역 + 신규 P 영역)

각 분할마다 19-C [§4 ~ §17 14 영역](19_refactor_function_verification_checklist.md) + 신규 P 영역.

| 분할 | 19-C 영향 영역 | 신규 P 영역 |
|---|---|---|
| 20-4-1 F-5 | A (예약) / D (환자) / H (통계) / L (API·프론트) | P-1 (출력물) |
| 20-4-2 F-6 | D (환자) / I (관리자) | P-2 (import 확장) |
| 20-4-3 F-4 | I (관리자) / J (AI — reindex 알림) | P-3 (알림 / 외부 채널) |
| 20-4-4 F-9 | A (예약) / D (환자) / E (의사) / I (관리자) | P-4 (EMR 연동) |

---

## 12. Codex 검증 요청 형식

각 분할마다 [reports/refactor/20-4-N_codex_review_request.md](../../reports/refactor/) 작성:
- 본 20-P-3 [§3 ~ §6 상세 기획](#) 정합 확인
- 외부 호출 차단 (테스트 mock + provider 정합)
- 응답 키 33+ 보존
- 1825 baseline 회귀 0
- 운영 DB / 외부 API / 실제 문자 발송 ⊥

---

## 13. 종합

- 본 20-P-3 = 그룹 D 4개 항목 (F-4 / F-5 / F-6 / F-9) 의 *상세 기획* — read-only 문서.
- §1 그룹 D 개요 + 의존성 (F-5 → F-4 / F-6 → F-9 / F-4 → 외부 인증 / F-9 → F-1·F-3).
- §2 공통 원칙 GD-1 ~ GD-10 = 응답 key 보존 / API URL 보존 / m019+ 신설 / 외부 인증 마스킹 / 외부 호출 차단 / 1825 baseline / 운영 DB 보호 / 19-C P 영역 / Codex 게이트 / 외부 결정 후 진입.
- §3 ~ §6 = 4개 항목 상세 (F-5 출력물 / F-6 import / F-4 알림 / F-9 EMR).
- §7 진입 순서 = 20-4-1 (F-5) → 20-4-2 (F-6) → 20-4-3 (F-4 v1=내부만) → 20-4-4 (F-9, **(a) 패스 권장**).
- §8 ~ §9 응답 key / API URL / UI 영향 — 기존 33+ 셋 보존 + 신설만, main.html JS 무수정.
- §10 위험도 종합 — F-5 / F-6 = 중간, F-4 = 높음, F-9 = 최대.
- §11 검증 = 19-C 14 영역 + 신규 P 영역 (출력물 / import / 알림 / EMR).
- 다음 단계 = **20-P-3 Codex 검증 통과** 후 → 사용자 §3-4 (F-5 결정) 답 → **20-4-1 F-5 출력물 진입**.
- F-9 EMR (가장 큰 결정) 은 20-4-4 진입 직전에 받음 — 본 시스템 정체성 (도수치료 전문 vs EMR 연동) 선택. **(a) 패스 우선 권장**.
