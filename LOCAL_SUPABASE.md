# Local Supabase development stack

Use this development-only stack to test GroundDesk’s Supabase authentication
and PostgreSQL persistence. GroundDesk owns the `public` application schema
through Alembic; do not create `supabase/migrations` or run `supabase db push`
for this repository.

## Start the stack

Docker and the Supabase CLI are required. From the repository root, install
the CLI using the [official Supabase CLI instructions](https://supabase.com/docs/guides/local-development/cli/getting-started), then run:

```bash
supabase start
supabase status
```

`supabase status` prints the local API URL, publishable key, database URL, and
the Inbucket URL. The checked-in `supabase/config.toml` disables public signup
and routes any future invitation/reset redirects to the local frontend. No
service role key or database password is committed.

Create or update the ignored `.env` with the actual values printed by that
command. The database URL should use SQLAlchemy’s psycopg v3 scheme:

```dotenv
APP_ENV=development
PERSISTENCE_BACKEND=database
DATABASE_AUTO_CREATE=false
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_PUBLISHABLE_KEY=<value from supabase status>
DATABASE_URL=postgresql+psycopg://postgres:<password>@127.0.0.1:54322/postgres
DATABASE_MIGRATION_URL=postgresql+psycopg://postgres:<password>@127.0.0.1:54322/postgres
VECTOR_STORE=local
EMBEDDING_PROVIDER=hashing
EMBEDDING_MODEL=hashing
EMBEDDING_DIMENSIONS=384
GENERATION_PROVIDER=template
```

Apply the application migrations exactly once to a new local stack:

```bash
uv sync --locked
uv run --locked alembic upgrade head
```

Then start the API with the environment above:

```bash
uv run --locked uvicorn app.main:app --reload
```

Run `make frontend-dev` in a second terminal and open
`http://127.0.0.1:5173`. The public interface is organization-login only, so
create users and memberships through an administrator provisioning workflow
before users sign in. The authenticated `/api/onboarding` endpoint remains the
sole GroundDesk provisioning mutation; it is not a public sign-up route.

## Verification and cleanup

Confirm Alembic’s active revision against the local PostgreSQL database, then
use the Supabase Studio or SQL editor to inspect the `public` tables and their
RLS policies. Run the product’s focused checks before broader testing:

```bash
uv run --locked pytest -q tests/unit/test_config.py tests/integration/test_alembic.py tests/integration/test_startup.py
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Local data is disposable and is not promoted to Supabase Cloud. For a future
hosted project, create an empty project, store Auth/database values as
deployment secrets, run this same Alembic history once from a migration job,
and only then point the API at it.
