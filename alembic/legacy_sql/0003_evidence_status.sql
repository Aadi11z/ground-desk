-- Archived pre-Alembic GroundDesk evidence acceptance status for auditable answer traces.
-- Run after 0001_product_interactions.sql (and 0002 when auth is enabled).
--
-- `confidence` is retained for API/backward compatibility, but represents an
-- uncalibrated evidence-support heuristic rather than answer correctness.

alter table answer_traces
  add column if not exists evidence_status varchar(40) not null default 'unassessed';

alter table answer_traces
  add column if not exists generation_model varchar(100);
