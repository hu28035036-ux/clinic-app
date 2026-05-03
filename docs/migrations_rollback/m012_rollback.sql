-- m012 rollback (수동 실행 only) — knowledge_chunks / knowledge_index_runs 제거
--
-- ⚠ 자동 실행 절대 금지. 운영자 명시 승인 + clinic.db 백업 후에만 실행.
-- ⚠ 본 SQL 은 chunk 영속화 데이터 전체를 삭제한다 — 18-4 도입 후 reindex
--    결과가 모두 사라진다 (다음 reindex 가 다시 만들지만 시간/디스크 비용 발생).
--
-- 실행 후 schema_migrations 에서 id=12 행 제거 — 다음 부팅 시 m012 자동 재적용.
--
-- 의도된 사용 시나리오:
--   1. m012 가 운영 환경에서 예상치 못한 부작용 (인덱스 충돌 등) 을 일으킨 경우
--   2. v1.3.4 → v1.3.3 다운그레이드
--
-- 실행 전 체크리스트:
--   [ ] %APPDATA%\도수치료예약\clinic.db 를 별도 위치에 백업했는가?
--   [ ] backups\ 폴더의 자동 백업이 24h 이내 생성됐는가?
--   [ ] 사용자/관리자 승인을 받았는가?
--   [ ] 다운그레이드 후 m011 이하만 동작하는 코드 버전을 배포할 준비가 됐는가?

-- 인덱스 제거 (CREATE 와 역순)
DROP INDEX IF EXISTS ix_knowledge_index_runs_started;
DROP INDEX IF EXISTS ix_knowledge_chunks_category;
DROP INDEX IF EXISTS ix_knowledge_chunks_content_hash;
DROP INDEX IF EXISTS uq_knowledge_chunks_doc_chunk;

-- 테이블 제거
DROP TABLE IF EXISTS knowledge_chunks;
DROP TABLE IF EXISTS knowledge_index_runs;

-- schema_migrations 정리 — 다음 부팅 시 m012 재적용 가능하게
DELETE FROM schema_migrations WHERE id = 12;
