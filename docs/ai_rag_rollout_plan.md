# AI/RAG Rollout 계획 (ai_rag_rollout_plan)

> 18-P 이후 전체 구현 순서·세션별 완료 조건·Codex 검증 게이트·관리자 화면·권한.
> 본 문서는 **언제 무엇을 한다**를 정의한다.
> 무엇을 만드는지는 `ai_rag_architecture_plan.md`,
> DB 변경은 `ai_rag_migration_plan.md`,
> 테스트는 `ai_rag_test_plan.md`,
> 절차는 `ai_code_session_protocol.md` 참조.

---

## 0. 핵심 원칙

1. 하네스를 먼저 작성한 뒤 구조 변경.
2. 구조 변경 후 기존 테스트 전체 통과.
3. chunker 이후에도 기존 keyword RAG 유지.
4. vector 실패 시 keyword fallback.
5. hybrid는 feature flag로 켠다.
6. 기본 모드는 `local_first`.
7. `local_only` 모드 지원.
8. 외부 AI 보조 기능은 feature flag로 단계적 활성화.
9. 최종 배포 전 PyInstaller 검증.
10. 각 코드 세션은 Claude Code 자체 테스트 루프 통과 후 **Codex 검증으로 넘김**.

---

## 1. 전체 구현 순서

| 세션 | 이름 | 주요 산출물 | DB | 의존성 추가 | UI |
|---|---|---|---|---|---|
| **18-P** | 전체 구조계획 수립 | docs/* (1단계 + 2단계) | ❌ | ❌ | ❌ |
| **18-P 검증** | Codex 구조계획 검증 | Codex 보고서 | ❌ | ❌ | ❌ |
| **18-0** | RAG 하네스 + Safety 하네스 + 전체 하네스 최소 버전 | tests/harness/* 신규 + minimal tests | ❌ | ❌ | ❌ |
| **18-1** | RAG / Knowledge / Vector 폴더 구조 생성 | `app/services/ai/{rag,knowledge,vector}/` 빈 골격 + schemas | ❌ | ❌ | ❌ |
| **18-2** | 기존 keyword RAG 구조 분리 | search.py 분해 → keyword_index/retriever/confidence/composer/validator | ❌ | ❌ | ❌ |
| **18-3** | chunker 구현 | knowledge/{loader,normalizer,chunker} | ❌ | ❌ | ❌ |
| **18-4** | knowledge_chunks DB / reindex 구현 | indexer + m012 마이그레이션 + reindex API | **m012** | ❌ | (관리자 화면 일부) |
| **18-5** | vector store / embedding 구현 | vector/{embeddings,store,similarity} + m013 | **m013** | requirements.txt (옵션) | ❌ |
| **18-6** | hybrid retriever 구현 | retriever 확장 + 가중 + cache + reranker | (m014?) | ❌ | ❌ |
| **18-7** | UI / 관리자 상태 화면 구현 | main.html, admin 화면, reindex 버튼 | ❌ | ❌ | ✅ |
| **18-8** | 전체 회귀 테스트 / PyInstaller 검증 | hidden import 검증, 빌드 확인 | ❌ | ❌ | ❌ |

각 세션 완료 조건:
- `run_check.bat` 통과
- 신규/관련 하네스 통과
- API 계약 회귀 0
- `latest_codex_review_request.md` 작성
- **Codex 검증 통과**

---

## 2. 단계별 릴리스 매핑 (앱 버전)

| 앱 버전 | 포함 세션 | 사용자에게 노출되는 변화 |
|---|---|---|
| v1.3.3 (현행) | — | 매뉴얼 Q&A (키워드+LLM 옵션) |
| v1.3.4 (patch, 내부) | 18-0~18-2 | 변화 없음 (내부 리팩토링) |
| v1.3.5 (patch, 내부) | 18-3~18-4 | 변화 없음 (chunker 도입, 검색 품질 개선) + 관리자 화면 일부 |
| v1.4.0 (minor) | 18-5~18-7 | Vector/Hybrid 옵션 (관리자 활성화 시), local_only 모드 노출 |
| v1.4.1 (patch) | 18-8 잔여 | 안정성 |

각 패치는 사용자 승인 후 빌드 (CLAUDE.md 배포 규칙).

---

## 3. Feature Flag 활성화 단계

| 플래그 | 18-1 기본 | 18-4 후 | 18-5 후 | 18-6 후 | 18-7 후 |
|---|:---:|:---:|:---:|:---:|:---:|
| `AI_RAG_ENABLED` | true | true | true | true | true |
| `AI_LOCAL_RULES_ENABLED` | true | true | true | true | true |
| `AI_LOCAL_MANUAL_SEARCH_ENABLED` | true | true | true | true | true |
| `AI_LOCAL_DB_QUERY_ENABLED` | true | true | true | true | true |
| `AI_RAG_LOGGING_ENABLED` | true | true | true | true | true |
| `AI_RAG_STRICT_SAFETY` | true | true | true | true | true |
| `AI_LOCAL_ONLY_MODE` | false | false | false | false | (사용자 선택) |
| `AI_EXTERNAL_LLM_ENABLED` | (현행) | (현행) | (현행) | (현행) | (사용자 선택) |
| `AI_EXTERNAL_EMBEDDING_ENABLED` | false | false | **true (관리자 옵션)** | true | true |
| `AI_RAG_VECTOR_ENABLED` | false | false | **true (관리자 옵션)** | true | true |
| `AI_RAG_HYBRID_ENABLED` | false | false | false | **true (관리자 옵션)** | true |

원칙: 새 기능은 모두 OFF로 출시 → 관리자가 활성화.

---

## 4. 사용자 안내

### 4-1. CHANGELOG.txt
각 패치마다 다음 형식 추가:
```
v1.X.Y (YYYY-MM-DD) — 한 줄 요약
- 사용자 영향:
- 관리자 영향:
- 데이터 마이그레이션:
- 새로 추가된 옵션:
- 호환성:
```

### 4-2. README / 안내txt
- v1.4.0에서 "AI 모드(local_only/local_first/ai_assist)" 섹션 추가
- "Vector 검색" / "Reindex" 가이드 추가
- API key 미설정 시 동작 명시 (keyword RAG는 정상)

### 4-3. 관리자 페이지 안내 배너
- 새 플래그가 켜질 때 짧은 안내문 (예: "Vector 검색이 활성화되었습니다. API key가 필요합니다.")

---

## 5. 배포 순서 (사용자 승인 받은 후)

1. Claude Code 자체 테스트 통과
2. **Codex 검증 통과** (필수 게이트)
3. 사용자 명시 승인 ("배포할까요?" → "네")
4. `app/config.py` APP_VERSION 갱신
5. `CHANGELOG.txt`, `VERSION.txt`, `versions/INDEX.txt` 갱신
6. 빌드: `pyinstaller --noconfirm dosu_clinic.spec`
7. ZIP 패키징 (CHANGELOG/VERSION/도구/안내txt 동봉)
8. `gh release create vX.Y.Z`
9. `clinic-updates/manifest.json` + `README.md` 푸시 (sha256, notes)
10. `versions/v1.X.Y/` 백업 폴더 생성

규칙(CLAUDE.md 재명시):
- 사용자 승인 없이 빌드/배포 금지.
- 여러 fix 모아서 한 번에 배포.

---

## 6. 모니터링 / 회수

### 6-1. 모니터링 (사용자 환경)
- `AiUsageLog` 누적 — 차단/실패/timeout 비율
- 관리자 화면 "최근 AI 질의 로그" 노출
- reindex 결과 (`knowledge_index_runs`) 확인

### 6-2. 회수(rollback)
사용자 환경에서 문제 발생 시:
- **즉시 회수**: 관리자가 해당 flag OFF (예: `AI_RAG_VECTOR_ENABLED=false`) → keyword 단독 동작
- **버전 회수**: `clinic-updates/manifest.json`에서 안정 버전으로 되돌림. 사용자 다음 실행 시 자동 다운그레이드(앱이 지원할 경우).
- **데이터 회수**: 신규 테이블은 그대로 두되 사용 안 함. 필요 시 `migrations_rollback/` SQL을 사용자에게 안내(자동 실행 금지).

### 6-3. 비상 절차
- 운영 DB 손상 의심 → `backups/` 자동 백업 사용 가이드 안내
- 신규 기능 무한 루프/호출 폭주 → flag OFF 또는 mode `local_only`로 즉시 차단

---

## 7. 관리자 화면 표시 항목 (18-7)

- Knowledge 문서 수
- Chunk 수
- Vector 생성 수
- 마지막 index 시간
- 마지막 index 결과 (status, succeeded/total, failed_paths)
- Vector 사용 가능 여부 (api_key 존재 + flag on)
- 검색 모드 (keyword | hybrid)
- AI 모드 (local_only | local_first | ai_assist)
- 외부 API 사용 가능 여부
- 최근 AI 질의 로그 (마지막 N건)
- LLM 호출 수 (오늘/주간)
- Embedding 생성 수
- 차단된 질문 수
- prompt_version
- **Reindex 실행 버튼**

표시 데이터 출처:
- chunk/vector 수: `COUNT(*) FROM knowledge_chunks/_vectors`
- 마지막 reindex: `knowledge_index_runs` MAX
- 호출 수: `AiUsageLog` 집계
- 모드/flag: `AiSetting`

---

## 8. 권한 설계

### 8-1. 일반 직원 가능
- AI 매뉴얼 질문 (`/api/ai/manual/{search,ask}`)
- 예약문자 초안 생성
- 안전한 안내 답변 확인 (할루시네이션 가드 결과 포함)

### 8-2. 관리자만 가능
- Reindex 실행
- Vector 기능 ON/OFF
- AI provider 설정 (provider/model/base_url/temperature/max_tokens)
- API key 등록 / 상태 확인 (값은 안 보임)
- AI 로그 확인 (마스킹된 prompt/response, reason_code)
- prompt_version 확인
- chunk/vector 상태 확인 (관리자 화면)
- AI 모드 변경 (local_only/local_first/ai_assist)
- Feature flag 토글

권한 체크 위치:
- `/api/ai/health` — admin (현행)
- `/api/ai/health/public` — 일반 (현행)
- `/api/ai/settings` GET/PUT — admin (현행)
- 신규 `/api/ai/reindex` — admin
- 신규 `/api/ai/status` — admin (chunk/vector 카운트 포함) / 일반은 최소 정보만

---

## 9. 각 세션 완료 조건 체크리스트 (요약)

각 세션 끝에서:
- [ ] 사용자 지시 범위 외 파일 수정 없음
- [ ] `run_check.bat` 통과
- [ ] 신규 하네스 테스트 통과
- [ ] 기존 SMS AI / 휴무 AI 테스트 통과
- [ ] `/api/ai/manual/{search,ask}` 응답 키 회귀 0
- [ ] provider/embedding call count 단언 통과 (`len(provider.calls)` / `len(embedding_provider.calls)`)
- [ ] PyInstaller hidden import 갱신 (해당 세션이 신규 모듈/마이그레이션 추가 시)
- [ ] `latest_test_report.md` / `latest_fix_summary.md` 작성
- [ ] `latest_codex_review_request.md` 작성
- [ ] 세션별 영구 보존본 복사
- [ ] **Codex 검증 통과 후 다음 세션 진입**

5회 실패 시:
- [ ] `latest_failure_report.md` 작성
- [ ] 사용자에게 코드 재작성/설계 재검토 보고
- [ ] Codex 검증 (실패 진단)

---

## 10. Codex 검증 게이트 (재명시)

- Claude Code 자체 테스트 통과는 최종 완료가 아니다.
- Codex가 `latest_codex_review_request.md`를 시작점으로 하되, 실제 diff·변경 파일·테스트 결과·로그를 **독립적으로** 검증.
- Codex 검증 종료 전 다음 세션 진입 금지.
- 자세한 절차: `docs/ai_codex_review_protocol.md`.

---

## 11. 의존성 추가 시점

- v1.3.3 → 18-4까지: 추가 0
- 18-5 (vector): 옵션
  - 후보 1: 외부 lib 없이 SQLite + numpy로 구현 (numpy는 이미 PyInstaller 환경에 있을 가능성, 확인 필요)
  - 후보 2: `sentence-transformers` 추가 (로컬 임베딩) — 빌드 크기 증가 큼
  - 후보 3: `openai` SDK의 embedding API만 사용 (의존성 추가 0, 외부 호출 필요)
  - **권장**: 후보 3을 우선, 후보 2는 보류
- 18-6 (hybrid): 추가 0 (가중 합산만)

---

## 12. 위험과 완화

| 위험 | 완화 |
|---|---|
| LLM 응답 폭주로 비용 폭증 | 모드 기본 `local_first` + 게이트 다층 + 캐시 + max_tokens 제한 |
| 임베딩 reindex 실패로 검색 멈춤 | 부분 실패 + keyword fallback + 기존 인덱스 보존 |
| 응답 스키마 변경으로 프론트 깨짐 | 계약 테스트 + 후방호환 약속 (필드 추가만) |
| PII 노출 | 입력/출력 양방향 마스킹 + 로그 sha256 + 외부 전송 직전 1회 더 검사 |
| 빌드 누락(hidden import) | spec 동기화 체크리스트 + 18-8 PyInstaller 검증 테스트 |
| 사용자 환경 DB 손상 | 자동 백업 유지 + 마이그레이션 idempotent + 운영 DB 직접 접근 금지 |

---

## 13. 다음 세션 진입 조건

- 1단계+2단계 문서 머지 완료
- **Codex가 18-P 구조계획을 검증** ("18-P 검증" 단계)
- 사용자가 18-0 시작 지시 발화
