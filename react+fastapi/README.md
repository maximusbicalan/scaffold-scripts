# React + FastAPI starter generator

This generator extracts the reusable infrastructure pattern from BookSuki while
leaving BookSuki-specific users, providers, bookings, and marketplace code behind.

## Generate a project

macOS/Linux:

```bash
./scaffold-scripts/react+fastapi/create-project.sh ../my-app-name
```

Windows Command Prompt:

```bat
scaffold-scripts\react+fastapi\create-project.bat ..\my-app-name
```

That one command creates the source/configuration files, initializes the backend
with uv, creates the React TypeScript Vite app, installs Tailwind CSS and Redux
Toolkit, starts PostgreSQL and Redis with Docker Compose, and applies the initial
Alembic migration.

Prerequisites: uv, Node.js/npm, and Docker with Compose. Current Vite versions
require a supported current Node.js release.

Useful options:

```text
--skip-services   generate and install, but do not start Docker or migrate
--skip-install    only write files (useful for reviewing or testing the template)
--python 3.13     select another backend Python version
```

The generator refuses to overwrite an existing path. This is intentional: a
partial run remains inspectable, and rerunning never destroys existing work.

## The files worth templating

The most reusable backend files are `pyproject.toml`, `.env.example`,
`compose.yaml`, Alembic's configuration and environment, `app/core/config.py`,
`app/core/database.py`, `app/core/redis.py`, the FastAPI lifespan in `main.py`,
the API router aggregator, and one complete model/schema/repository/service/route
slice that shows where new domain features belong.

The most reusable frontend files are `package.json`, `vite.config.ts`,
`src/index.css`, `src/lib/api.ts`, `src/app/store.ts`, `src/app/hooks.ts`, the
Redux provider in `src/main.tsx`, the router in `src/App.tsx`, and one complete
feature slice that demonstrates typed Redux state and API calls.

Generated lockfiles (`uv.lock` and `package-lock.json`) should be committed to a
real starter repository. `.env` and runtime data volumes should not be committed.
