## How to Run the project?

1. Starting Supabase \
`supabase start` \
`supabase status` \
Port: 54323

2. For Backend dependencies \
`uv sync --locked` \
`uv run --locked alembic upgrade head` \

3. For API \
`make api` \
Port: 8000

4. For React frontend \
`make frontend-dev` \
Port: 5173 
