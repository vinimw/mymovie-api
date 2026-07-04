# My Movies API

FastAPI backend for the My Movies project. It handles authentication, watched titles, watched episodes, dashboard data, and OMDb integration.

## Tech stack

- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Pydantic v2
- OMDb API

## Prerequisites

- Python 3.11 or newer
- `pip`
- Docker Desktop optional, but recommended for local PostgreSQL

## Project structure

- `app/`: API code, models, schemas, services, repositories
- `alembic/`: database migrations
- `scripts/`: local helper scripts
- `.env.example`: local environment template
- `docker-compose.yml`: PostgreSQL service for local development

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
.venv/bin/python scripts/generate_password_hash.py "my_strong_password"
./scripts/start_local_postgres.sh
alembic upgrade head
uvicorn app.main:app --reload
```

Open:

```txt
http://127.0.0.1:8000/docs
```

## Installation

### 1. Create and activate the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Installed packages include FastAPI, SQLAlchemy, Alembic, `psycopg`, `passlib`, and `httpx`.

## Environment configuration

Copy the template:

```bash
cp .env.example .env
```

Important variables:

- `APP_NAME`: application display name
- `APP_ENV`: environment name such as `local`
- `APP_DEBUG`: enables debug mode
- `SQL_ECHO`: enables SQL query logging
- `API_V1_PREFIX`: default API prefix
- `BACKEND_CORS_ORIGINS`: allowed frontend origins
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: JWT signing secret
- `JWT_ALGORITHM`: JWT signing algorithm
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: access token lifetime
- `ADMIN_EMAIL`: initial admin email used for login
- `ADMIN_PASSWORD_HASH`: bcrypt password hash
- `ADMIN_EMAILS`: optional comma-separated list of login emails
- `ADMIN_PASSWORD_HASHES`: optional comma-separated list of bcrypt hashes aligned with `ADMIN_EMAILS`
- `OMDB_PROVIDER_MODE`: `mock` or `live`
- `OMDB_API_BASE_URL`: OMDb base URL
- `OMDB_API_KEY`: required when `OMDB_PROVIDER_MODE=live`
- `DEFAULT_EPISODE_RUNTIME_MINUTES`: fallback runtime for episodes without duration

Default local database values from `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://my_movies:my_movies@localhost:5433/my_movies
POSTGRES_DB=my_movies
POSTGRES_USER=my_movies
POSTGRES_PASSWORD=my_movies
POSTGRES_PORT=5433
```

## Password hash generation

Generate the admin password hash before the first run:

```bash
python scripts/generate_password_hash.py
```

Or provide the password directly:

```bash
python scripts/generate_password_hash.py "my_strong_password"
```

Generate multiple hashes in one line for `ADMIN_PASSWORD_HASHES`:

```bash
python scripts/generate_password_hash.py "password_one,password_two"
```

If you want to avoid any Python path ambiguity:

```bash
.venv/bin/python scripts/generate_password_hash.py "my_strong_password"
```

Paste the generated value into:

```env
ADMIN_PASSWORD_HASH=replace_with_bcrypt_hash
```

## Local PostgreSQL

### Recommended: helper script

```bash
chmod +x scripts/start_local_postgres.sh
./scripts/start_local_postgres.sh
```

What this script does:

- loads values from `.env` when available
- starts the `postgres` service with Docker Compose if Docker is available
- falls back to native PostgreSQL binaries if Docker is not running
- waits for the database to become ready
- prints the final `DATABASE_URL`

### Manual Docker option

```bash
docker compose up -d postgres
docker compose ps
```

Check the connection:

```bash
docker compose exec postgres psql -U my_movies -d my_movies -c '\dt'
```

### Stop the local database

```bash
chmod +x scripts/stop_local_postgres.sh
./scripts/stop_local_postgres.sh
```

## Database migrations

Run all migrations:

```bash
alembic upgrade head
```

Create a new migration:

```bash
alembic revision --autogenerate -m "describe your change"
```

Alembic is configured in:

- `alembic.ini`
- `alembic/`

## Running the API

Start the development server:

```bash
uvicorn app.main:app --reload
```

Useful URLs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/api/v1/health`

## Authentication

The API supports one or more configured logins defined by:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD_HASH`
- `ADMIN_EMAILS`
- `ADMIN_PASSWORD_HASHES`

When `ADMIN_EMAILS` and `ADMIN_PASSWORD_HASHES` are provided, values must be comma-separated and keep the same order. Example:

```env
ADMIN_EMAILS=alice@example.com,bob@example.com
ADMIN_PASSWORD_HASHES=$2b$12$hash_for_alice,$2b$12$hash_for_bob
```

The frontend authenticates against:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Authentication is cookie-based. After login, the API stores the session token in an httpOnly cookie, and the frontend sends it automatically with `credentials: "include"`.

## OMDb integration

For local mock data:

```env
OMDB_PROVIDER_MODE=mock
```

For the real OMDb API:

```env
OMDB_PROVIDER_MODE=live
OMDB_API_KEY=your_omdb_api_key
```

The project keeps the `imdb_id` field name because OMDb uses IMDb identifiers.

## Main endpoints

- `GET /`
- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/dashboard`
- `GET /api/v1/notifications`
- `GET /api/v1/notifications/unread-count`
- `POST /api/v1/notifications/read-all`
- `GET /api/v1/omdb/search`
- `GET /api/v1/omdb/titles/{imdb_id}`
- `GET /api/v1/omdb/titles/{imdb_id}/episodes`
- `GET /api/v1/titles`
- `POST /api/v1/titles`
- `GET /api/v1/titles/{title_id}`
- `PATCH /api/v1/titles/{title_id}`
- `DELETE /api/v1/titles/{title_id}`
- `POST /api/v1/titles/{title_id}/episodes`
- `DELETE /api/v1/titles/episodes/{episode_id}`

## Development notes

- Use `localhost` consistently for both frontend and backend when possible.
- The default CORS configuration allows `http://localhost:3000` and `http://127.0.0.1:3000`.
- Set `SQL_ECHO=false` to keep logs cleaner during normal development.

## Troubleshooting

### `Dependency missing` when generating the password hash

Activate the virtual environment and install the requirements first:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### `alembic upgrade head` fails

Check these items:

1. PostgreSQL is running.
2. `DATABASE_URL` in `.env` matches the running database.
3. The virtual environment is activated.
4. Dependencies were installed with `pip install -r requirements.txt`.

### The API refuses to start outside local

For non-local environments, the app now blocks startup if:

- `JWT_SECRET_KEY` is still the default value
- `JWT_SECRET_KEY` is shorter than 32 characters
- `ADMIN_PASSWORD_HASH` is still the placeholder value

### Docker is not running

The helper script can fall back to native PostgreSQL binaries if these commands are available:

- `initdb`
- `pg_ctl`
- `psql`

If they are not installed, start Docker Desktop or install PostgreSQL locally.
