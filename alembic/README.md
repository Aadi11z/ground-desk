# GroundDesk database migrations

Alembic is the only active migration history. The initial revision
`20260807_01` recreates the product-interaction schema from the three retired
raw SQL files, including the Supabase RLS policies on PostgreSQL.

For a new database, run:

```bash
DATABASE_MIGRATION_URL=postgresql+psycopg://... uv run --locked alembic upgrade head
```

For an existing database that already has every table, column, index, and RLS
policy from the archived SQL files, take a backup, verify the schema manually,
then mark the baseline without changing customer rows and apply the later,
additive revisions:

```bash
DATABASE_MIGRATION_URL=postgresql+psycopg://... uv run --locked alembic stamp 20260807_01
DATABASE_MIGRATION_URL=postgresql+psycopg://... uv run --locked alembic upgrade head
```

Do not run `upgrade` against an existing pre-Alembic database. The baseline is
non-destructive only when it is applied with `stamp` after review.

Use a direct administrative connection for migrations. The Cloud Run API should
receive only its bounded pooled `DATABASE_URL`; do not inject migration
credentials into the application service.
