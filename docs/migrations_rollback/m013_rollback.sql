-- m013 rollback (수동 실행 only) — knowledge_vectors 제거
--
-- ⚠ 자동 실행 절대 금지. 운영자 명시 승인 + clinic.db 백업 후에만 실행.
-- ⚠ 본 SQL 은 임베딩 영속화 데이터 전체를 삭제한다 — 18-5 도입 후 임베딩
--    결과가 모두 사라진다 (다음 reindex + embedding_provider 활성 시 재생성
--    되지만 외부 API 토큰 비용/시간 발생).
-- ⚠ 본 SQL 은 ``knowledge_chunks`` 는 건드리지 않는다 — chunk 영속화는 m012
--    소유. m012 까지 함께 롤백하려면 m013 → m012 순서로 실행.
--
-- 실행 후 schema_migrations 에서 id=13 행 제거 — 다음 부팅 시 m013 자동 재적용.
--
-- 의도된 사용 시나리오:
--   1. m013 가 운영 환경에서 예상치 못한 부작용 (인덱스 충돌 등) 을 일으킨 경우
--   2. v1.3.5 → v1.3.4 다운그레이드 (vector 단계 비활성화)
--   3. embedding 차원/모델 일괄 재구성 전 초기화
--
-- 실행 전 체크리스트:
--   [ ] %APPDATA%\도수치료예약\clinic.db 를 별도 위치에 백업했는가?
--   [ ] backups\ 폴더의 자동 백업이 24h 이내 생성됐는가?
--   [ ] 사용자/관리자 승인을 받았는가?
--   [ ] 다운그레이드 후 m012 이하만 동작하는 코드 버전을 배포할 준비가 됐는가?

-- 인덱스 제거 (CREATE 와 역순)
DROP INDEX IF EXISTS ix_knowledge_vectors_chunk_id;
DROP INDEX IF EXISTS ix_knowledge_vectors_content_hash;
DROP INDEX IF EXISTS uq_knowledge_vectors_chunk_provider_model;

-- 테이블 제거 (FK CASCADE 가 chunk 삭제로 vector 까지 정리하지만, 본 SQL 은
-- chunk 는 보존하고 vector 만 제거)
DROP TABLE IF EXISTS knowledge_vectors;

-- schema_migrations 정리 — 다음 부팅 시 m013 재적용 가능하게
DELETE FROM schema_migrations WHERE id = 13;
