-- GroundDesk durable interaction persistence.
-- Apply this migration to PostgreSQL/Supabase before setting
-- PERSISTENCE_BACKEND=database in the application.
--
-- Authentication and row-level security policies are intentionally introduced
-- in the subsequent identity/tenant-isolation migration. Until that step,
-- expose this database only through the backend service.

create table if not exists workspaces (
  id varchar(64) primary key,
  name varchar(200) not null,
  created_at timestamptz not null default now()
);

create table if not exists conversations (
  id varchar(64) primary key,
  workspace_id varchar(64) not null references workspaces(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_conversations_workspace_id
  on conversations(workspace_id);

create table if not exists messages (
  id varchar(64) primary key,
  conversation_id varchar(64) not null references conversations(id) on delete cascade,
  workspace_id varchar(64) not null references workspaces(id),
  role varchar(20) not null check (role in ('user', 'assistant')),
  content text not null,
  trace_id varchar(64),
  created_at timestamptz not null default now()
);

create index if not exists ix_messages_conversation_id
  on messages(conversation_id, created_at);
create index if not exists ix_messages_workspace_id
  on messages(workspace_id, created_at);
create index if not exists ix_messages_trace_id
  on messages(trace_id);

create table if not exists answer_traces (
  trace_id varchar(64) primary key,
  conversation_id varchar(64) not null references conversations(id) on delete cascade,
  workspace_id varchar(64) not null references workspaces(id),
  user_message_id varchar(64) not null references messages(id) on delete cascade,
  assistant_message_id varchar(64) not null references messages(id) on delete cascade,
  question text not null,
  answer text not null,
  citations jsonb not null default '[]'::jsonb,
  suggested_ticket_reply text,
  confidence double precision not null,
  needs_escalation boolean not null,
  created_at timestamptz not null default now()
);

create index if not exists ix_answer_traces_workspace_id
  on answer_traces(workspace_id, created_at);
create index if not exists ix_answer_traces_conversation_id
  on answer_traces(conversation_id, created_at);

create table if not exists feedback (
  id varchar(64) primary key,
  trace_id varchar(64) not null references answer_traces(trace_id) on delete cascade,
  workspace_id varchar(64) not null references workspaces(id),
  rating integer not null check (rating between 1 and 5),
  feedback_type varchar(64),
  comment text,
  corrected_answer text,
  created_at timestamptz not null default now()
);

create index if not exists ix_feedback_workspace_id
  on feedback(workspace_id, created_at);
create index if not exists ix_feedback_trace_id
  on feedback(trace_id);
