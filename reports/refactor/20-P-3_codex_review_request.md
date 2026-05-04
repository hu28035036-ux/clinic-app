# 20-P-3 Codex 검증 요청서

## 1. 세션 이름

`20-P-3_post_19p_group_d_detail_plan` — 그룹 D (F-4 / F-5 / F-6 / F-9) 4개 항목 상세 기획.

## 2. 이번 세션 목표

20-P-1 마스터 플랜 Codex caveat ("그룹 C/D 진입 전 별도 상세 기획 권장") 정합 — 그룹 C 5/5 완료 후 그룹 D 상세 기획.

본 20-P-3 = 그룹 D 4개 항목 상세 기획. 외부 채널 / EMR 결정 / 마이그레이션 / 응답 키 / UI / 위험도 / 진입 순서 정리.

## 3. 작성 / 수정한 문서

| 문서 | 변경 종류 | 핵심 |
|---|---|---|
| `docs/refactor/20_post_19p_group_d_detail_plan.md` | **신규** | 13개 섹션 (그룹 D 개요 / 공통 원칙 GD-1~10 / F-5·F-6·F-4·F-9 상세 / 진입 순서 / 응답 key·API URL·UI / 위험도 / 검증 / 종합) |
| `reports/refactor/20-P-3_codex_review_request.md` | **신규** (본 문서) | |
| `reports/refactor/latest_codex_review_request.md` | 덮어쓰기 | 20-P-3 본문 |

## 4. 수정 금지였던 범위 (20-P-3 세션 범위)

| 금지 항목 | 변경 |
|---|---|
| `app/**` 코드 | 0 |
| `tests/**` 코드 | 0 |
| `app/migrations/m001~m018.py` | 0 |
| `requirements*.txt` | 0 |
| `dosu_clinic.spec` | 0 |
| `app/templates/**` | 0 |
| `app/static/**` | 0 |
| `pyproject.toml` | 0 |
| 운영 DB 접근 | 없음 |
| 외부 API 호출 | 없음 |
| 실제 문자 발송 | 없음 |

## 5. 실제 수정한 파일 목록

```
docs/refactor/20_post_19p_group_d_detail_plan.md  (신규, untracked)
reports/refactor/20-P-3_codex_review_request.md    (신규, untracked)
reports/refactor/latest_codex_review_request.md    (덮어쓰기)
```

## 6. Codex 가 검증해야 할 항목

| # | 항목 | 명령 / 위치 |
|---|---|---|
| C-1 | `app/`, `tests/`, migrations, spec, requirements, UI 변경 0 | git diff 검사 |
| C-2 | docs/refactor/20_post_19p_group_d_detail_plan.md 13 섹션 포함 | grep "^## " |
| C-3 | 그룹 D 4개 항목 (F-4 / F-5 / F-6 / F-9) 모두 상세 기획되었는가 | F-4 §5 / F-5 §3 / F-6 §4 / F-9 §6 |
| C-4 | 마이그레이션 m019+ 가 m001~m018 침범 ⊥ | m019+ 신설 명시 |
| C-5 | 그룹 D 의존성 (F-5 → F-4 / F-6 → F-9 / F-4 → 외부 인증 / F-9 → F-1·F-3) | §1-1 |
| C-6 | 진입 순서 = 20-4-1 (F-5) → 20-4-2 (F-6) → 20-4-3 (F-4 v1 내부만) → 20-4-4 (F-9, (a) 패스 권장) | §7 |
| C-7 | 응답 key 33+ 보존 + 신설만 | §8 |
| C-8 | UI 변경 = 기존 main.html JS 무수정 + 추가만 | §9 |
| C-9 | 위험도 (F-5 / F-6 중간, F-4 높음, F-9 최대) | §10 |
| C-10 | 검증 = 19-C 14 영역 + P 영역 (출력물 / import / 알림 / EMR) | §11 |
| C-11 | 사용자 결정 필요 항목이 후보만 명시 + 실제 결정은 사용자 | "사용자 결정 필수" / "사용자 답" |
| C-12 | F-9 EMR = 본 시스템 정체성 결정 (도수치료 전문 vs EMR 연동) 명시 | §6-2 / §6-4 / §13 |
| C-13 | 본 20-P-3 = read-only 문서 세션 | §0 |

## 7. 잔여 Caveat / 후속 검토

- F-9 EMR 벤더 결정 = 본 시스템 정체성. 사용자 미결정 시 (a) 패스 우선 권장.
- F-4 외부 채널 (이메일 / Slack / 카톡 / SMS) 인증 정보 사용자 등록 필수.
- F-5 출력물 v1 = PDF + HTML 권장. PDF 라이브러리 (reportlab / weasyprint) 후속 결정.
- F-6 CSV import v1 = 환자만. 예약 / 치료사 import 는 후속.

## 8. 다음 세션 진행 조건

- 20-P-3 Codex 검증 통과.
- 사용자 §3-4 (F-5 출력물 결정) 답 받음 — 권장값 가능.
- 20-4-1 F-5 출력물 진입.

## 9. Codex 검증 결과 기록 위치

- [reports/refactor/20-P-3_codex_review.md](20-P-3_codex_review.md)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md)

## 10. 사용자 → Codex 전달 문구

> "reports/refactor/latest_codex_review_request.md 20-P-3 그룹 D 상세 기획 검증 시작해줘. Claude Code 요약만 믿지 말고 docs/refactor/20_post_19p_group_d_detail_plan.md 를 직접 읽어서 4개 항목 상세 / 의존성 / 마이그레이션 m019+ / 응답 키·API URL 보존 / UI 영향 / 위험도 / 진입 순서 / F-9 EMR 정체성 결정 정합성을 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-P-3_codex_review.md 에 남겨줘."
