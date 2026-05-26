-- GroundDesk authenticated workspace membership and interaction ownership.
-- Run after 0001_product_interactions.sql in a Supabase PostgreSQL project.

create table if not exists workspace_members (
  workspace_id varchar(64) not null references workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role varchar(40) not null check (role in ('member', 'knowledge_manager', 'owner')),
  created_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

create index if not exists ix_workspace_members_user_id
  on workspace_members(user_id, workspace_id);

alter table conversations
  add column if not exists user_id uuid references auth.users(id) on delete set null;
alter table messages
  add column if not exists user_id uuid references auth.users(id) on delete set null;
alter table answer_traces
  add column if not exists user_id uuid references auth.users(id) on delete set null;
alter table feedback
  add column if not exists user_id uuid references auth.users(id) on delete set null;

create index if not exists ix_conversations_user_id
  on conversations(user_id, updated_at);
create index if not exists ix_messages_user_id
  on messages(user_id, created_at);
create index if not exists ix_answer_traces_user_id
  on answer_traces(user_id, created_at);
create index if not exists ix_feedback_user_id
  on feedback(user_id, created_at);

-- These policies protect direct Supabase client access. The FastAPI service
-- must still authorize memberships before Qdrant retrieval because Qdrant
-- does not apply PostgreSQL Row Level Security.
alter table workspaces enable row level security;
alter table workspace_members enable row level security;
alter table conversations enable row level security;
alter table messages enable row level security;
alter table answer_traces enable row level security;
alter table feedback enable row level security;

create schema if not exists private;

create or replace function private.is_grounddesk_workspace_member(target_workspace_id varchar)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = target_workspace_id
      and wm.user_id = (select auth.uid())
  );
$$;

revoke all on function private.is_grounddesk_workspace_member(varchar) from public;
grant usage on schema private to authenticated;
grant execute on function private.is_grounddesk_workspace_member(varchar) to authenticated;

drop policy if exists "members can view their workspaces" on workspaces;
create policy "members can view their workspaces"
  on workspaces for select to authenticated
  using (private.is_grounddesk_workspace_member(id));

drop policy if exists "members can view own membership" on workspace_members;
create policy "members can view own membership"
  on workspace_members for select to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "members manage own conversations" on conversations;
create policy "members manage own conversations"
  on conversations for all to authenticated
  using (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  )
  with check (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  );

drop policy if exists "members manage own messages" on messages;
create policy "members manage own messages"
  on messages for all to authenticated
  using (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  )
  with check (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  );

drop policy if exists "members view own traces" on answer_traces;
create policy "members view own traces"
  on answer_traces for select to authenticated
  using (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  );

drop policy if exists "members manage own feedback" on feedback;
create policy "members manage own feedback"
  on feedback for all to authenticated
  using (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  )
  with check (
    user_id = (select auth.uid())
    and private.is_grounddesk_workspace_member(workspace_id)
  );
