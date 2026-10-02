#!/usr/bin/env python3
"""Create a React + FastAPI + PostgreSQL + Redis starter project.

The generator only uses Python's standard library. By default it bootstraps the
backend with uv, bootstraps the frontend with create-vite, installs dependencies,
starts PostgreSQL and Redis, and applies the initial Alembic migration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import textwrap
from pathlib import Path


def clean(value: str) -> str:
    return textwrap.dedent(value).lstrip("\n")


def run(command: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def require(command: str, help_text: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"Missing required command: {command}. {help_text}")


def available_port(preferred: int, reserved: set[int]) -> int:
    """Return the preferred localhost port, or the next available one."""
    port = preferred
    while port <= 65535:
        if port not in reserved:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.bind(("127.0.0.1", port))
                except OSError:
                    port += 1
                    continue
            return port
        port += 1
    raise SystemExit(f"No available TCP port found starting at {preferred}.")


def write(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean(content), encoding="utf-8", newline="\n")
    print(f"  wrote {relative_path}")


def project_files(
    project_name: str,
    database_name: str,
    session_secret: str,
    python_version: str,
    postgres_port: int,
    redis_port: int,
) -> dict[str, str]:
    title = project_name.replace("-", " ").replace("_", " ").title()
    return {
        ".gitignore": r'''
            # Environment and secrets
            .env
            .env.*
            !.env.example

            # Python / uv
            __pycache__/
            *.py[cod]
            .venv/
            .pytest_cache/
            .ruff_cache/
            .coverage
            htmlcov/

            # Node / Vite
            node_modules/
            dist/
            .vite/
            npm-debug.log*

            # Editors and OS files
            .idea/
            .vscode/
            .DS_Store
            Thumbs.db
        ''',
        ".env.example": f'''
            APP_NAME={title} API
            APP_ENV=development
            API_V1_PREFIX=/api/v1
            DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:{postgres_port}/{database_name}
            REDIS_URL=redis://127.0.0.1:{redis_port}/0
            CORS_ORIGINS=http://localhost:5173
            SESSION_SECRET=replace-me-with-a-long-random-value

            POSTGRES_USER=app
            POSTGRES_PASSWORD=app
            POSTGRES_DB={database_name}
            POSTGRES_PORT={postgres_port}
            REDIS_PORT={redis_port}
        ''',
        ".env": f'''
            APP_NAME={title} API
            APP_ENV=development
            API_V1_PREFIX=/api/v1
            DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:{postgres_port}/{database_name}
            REDIS_URL=redis://127.0.0.1:{redis_port}/0
            CORS_ORIGINS=http://localhost:5173
            SESSION_SECRET={session_secret}

            POSTGRES_USER=app
            POSTGRES_PASSWORD=app
            POSTGRES_DB={database_name}
            POSTGRES_PORT={postgres_port}
            REDIS_PORT={redis_port}
        ''',
        "compose.yaml": r'''
            services:
              postgres:
                image: postgres:17-alpine
                restart: unless-stopped
                environment:
                  POSTGRES_USER: ${POSTGRES_USER}
                  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
                  POSTGRES_DB: ${POSTGRES_DB}
                ports:
                  - "${POSTGRES_PORT:-5432}:5432"
                volumes:
                  - postgres_data:/var/lib/postgresql/data
                healthcheck:
                  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
                  interval: 3s
                  timeout: 3s
                  retries: 20

              redis:
                image: redis:7-alpine
                restart: unless-stopped
                command: redis-server --appendonly yes
                ports:
                  - "${REDIS_PORT:-6379}:6379"
                volumes:
                  - redis_data:/data
                healthcheck:
                  test: ["CMD", "redis-cli", "ping"]
                  interval: 3s
                  timeout: 3s
                  retries: 20

            volumes:
              postgres_data:
              redis_data:
        ''',
        "README.md": f'''
            # {title}

            Starter generated with React, TypeScript, Vite, Tailwind CSS, Redux Toolkit,
            FastAPI, async SQLAlchemy, Alembic, PostgreSQL, and Redis.

            ## Start development

            macOS/Linux:

            ```bash
            ./scripts/dev.sh
            ```

            Windows Command Prompt:

            ```bat
            scripts\\dev.bat
            ```

            The frontend runs at <http://localhost:5173>, the API at
            <http://localhost:8000>, and OpenAPI docs at <http://localhost:8000/docs>.

            ## Common commands

            ```bash
            docker compose up -d --wait
            cd backend && uv run alembic upgrade head
            cd backend && uv run alembic revision --autogenerate -m "describe change"
            cd backend && uv run pytest
            cd backend && uv run ruff check .
            cd frontend && npm run test
            cd frontend && npm run build
            ```

            Copy `.env.example` to `.env` for a fresh checkout, then replace the
            development credentials before using this outside local development.

            ## Architecture

            `backend/app/api/routes` owns HTTP concerns, `services` owns application
            rules, and `repositories` owns database queries. Shared database, Redis,
            settings, and middleware code lives under `backend/app/core`.

            `frontend/src/app` contains the Redux store and typed hooks,
            `frontend/src/features` contains feature slices/components, and
            `frontend/src/lib` contains API and environment infrastructure.
        ''',
        "scripts/dev.sh": r'''
            #!/usr/bin/env bash
            set -euo pipefail

            ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
            cd "$ROOT_DIR"
            docker compose up -d --wait
            (cd backend && uv run alembic upgrade head)

            cleanup() {
              kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
            }
            trap cleanup EXIT INT TERM

            (cd backend && uv run uvicorn app.main:app --reload --reload-dir app) &
            BACKEND_PID=$!
            (cd frontend && npm run dev) &
            FRONTEND_PID=$!
            wait
        ''',
        "scripts/dev.bat": r'''
            @echo off
            setlocal
            cd /d "%~dp0.."

            docker compose up -d --wait || exit /b 1

            cd backend
            uv run alembic upgrade head || exit /b 1
            cd ..

            start "API" /D "%CD%\backend" cmd /k "uv run uvicorn app.main:app --reload --reload-dir app"
            start "Frontend" /D "%CD%\frontend" cmd /k "npm run dev"

            echo API and frontend started in separate windows.
        ''',
        "backend/pyproject.toml": r'''
            [project]
            name = "backend"
            version = "0.1.0"
            description = "FastAPI backend"
            readme = "README.md"
            requires-python = ">=3.12"
            dependencies = [
                "alembic>=1.16",
                "asyncpg>=0.30",
                "fastapi[standard]>=0.116",
                "pydantic-settings>=2.10",
                "redis[hiredis]>=6.4",
                "sqlalchemy[asyncio]>=2.0.43",
            ]

            [dependency-groups]
            dev = [
                "httpx>=0.28",
                "pytest>=8.4",
                "pytest-asyncio>=1.1",
                "ruff>=0.12",
            ]

            [tool.pytest.ini_options]
            asyncio_mode = "auto"
            testpaths = ["tests"]

            [tool.ruff]
            line-length = 100
            target-version = "py312"

            [tool.ruff.lint.isort]
            known-first-party = ["app"]
            known-third-party = ["alembic", "sqlalchemy"]
        ''',
        "backend/.python-version": f"{python_version}\n",
        "backend/README.md": r'''
            # Backend

            Run commands from this directory with `uv run`, for example:

            ```bash
            uv run uvicorn app.main:app --reload
            uv run alembic upgrade head
            uv run pytest
            ```
        ''',
        "backend/app/__init__.py": "",
        "backend/app/core/__init__.py": "",
        "backend/app/core/config.py": r'''
            from functools import lru_cache
            from pathlib import Path

            from pydantic_settings import BaseSettings, SettingsConfigDict

            PROJECT_ROOT = Path(__file__).resolve().parents[3]


            class Settings(BaseSettings):
                model_config = SettingsConfigDict(
                    env_file=PROJECT_ROOT / ".env",
                    env_file_encoding="utf-8",
                    extra="ignore",
                )

                app_name: str = "Starter API"
                app_env: str = "development"
                api_v1_prefix: str = "/api/v1"
                database_url: str
                redis_url: str
                cors_origins: str = "http://localhost:5173"
                session_secret: str

                @property
                def cors_origin_list(self) -> list[str]:
                    return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


            @lru_cache
            def get_settings() -> Settings:
                return Settings()  # type: ignore[call-arg]


            settings = get_settings()
        ''',
        "backend/app/core/database.py": r'''
            from collections.abc import AsyncIterator
            from typing import Annotated

            from fastapi import Depends
            from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

            from app.core.config import settings

            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


            async def get_db() -> AsyncIterator[AsyncSession]:
                async with AsyncSessionFactory() as session:
                    try:
                        yield session
                    except Exception:
                        await session.rollback()
                        raise


            SessionDep = Annotated[AsyncSession, Depends(get_db)]
        ''',
        "backend/app/core/redis.py": r'''
            from typing import Annotated

            from fastapi import Depends, Request
            from redis.asyncio import Redis


            def get_redis(request: Request) -> Redis:
                return request.app.state.redis


            RedisDep = Annotated[Redis, Depends(get_redis)]
        ''',
        "backend/app/core/middleware.py": r'''
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            from app.core.config import settings


            def install_middleware(app: FastAPI) -> None:
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=settings.cors_origin_list,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
        ''',
        "backend/app/models/__init__.py": r'''
            from app.models.base import Base
            from app.models.item import Item

            __all__ = ["Base", "Item"]
        ''',
        "backend/app/models/base.py": r'''
            from sqlalchemy.orm import DeclarativeBase


            class Base(DeclarativeBase):
                pass
        ''',
        "backend/app/models/item.py": r'''
            from datetime import datetime
            from uuid import UUID, uuid4

            from sqlalchemy import DateTime, String, func
            from sqlalchemy.orm import Mapped, mapped_column

            from app.models.base import Base


            class Item(Base):
                __tablename__ = "items"

                id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
                name: Mapped[str] = mapped_column(String(120), index=True)
                created_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), server_default=func.now()
                )
        ''',
        "backend/app/schemas/__init__.py": "",
        "backend/app/schemas/item.py": r'''
            from datetime import datetime
            from uuid import UUID

            from pydantic import BaseModel, ConfigDict, Field


            class ItemCreate(BaseModel):
                name: str = Field(min_length=1, max_length=120)


            class ItemRead(BaseModel):
                model_config = ConfigDict(from_attributes=True)

                id: UUID
                name: str
                created_at: datetime
        ''',
        "backend/app/repositories/__init__.py": "",
        "backend/app/repositories/item_repository.py": r'''
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.models.item import Item


            class ItemRepository:
                def __init__(self, db: AsyncSession) -> None:
                    self.db = db

                async def list(self) -> list[Item]:
                    result = await self.db.scalars(select(Item).order_by(Item.created_at.desc()))
                    return list(result.all())

                async def create(self, name: str) -> Item:
                    item = Item(name=name)
                    self.db.add(item)
                    await self.db.flush()
                    return item
        ''',
        "backend/app/services/__init__.py": "",
        "backend/app/services/item_service.py": r'''
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.models.item import Item
            from app.repositories.item_repository import ItemRepository
            from app.schemas.item import ItemCreate


            class ItemService:
                def __init__(self, db: AsyncSession) -> None:
                    self.db = db
                    self.repository = ItemRepository(db)

                async def list_items(self) -> list[Item]:
                    return await self.repository.list()

                async def create_item(self, payload: ItemCreate) -> Item:
                    item = await self.repository.create(payload.name)
                    await self.db.commit()
                    await self.db.refresh(item)
                    return item
        ''',
        "backend/app/api/__init__.py": "",
        "backend/app/api/dependencies.py": r'''
            from typing import Annotated

            from fastapi import Depends

            from app.core.database import SessionDep
            from app.services.item_service import ItemService


            def get_item_service(db: SessionDep) -> ItemService:
                return ItemService(db)


            ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
        ''',
        "backend/app/api/routes/__init__.py": "",
        "backend/app/api/routes/health.py": r'''
            from fastapi import APIRouter
            from sqlalchemy import text

            from app.core.database import SessionDep
            from app.core.redis import RedisDep

            router = APIRouter(prefix="/health", tags=["health"])


            @router.get("")
            async def health(db: SessionDep, redis: RedisDep) -> dict[str, bool]:
                await db.execute(text("SELECT 1"))
                redis_ok = await redis.ping()
                return {"database": True, "redis": bool(redis_ok)}
        ''',
        "backend/app/api/routes/items.py": r'''
            from fastapi import APIRouter, status

            from app.api.dependencies import ItemServiceDep
            from app.schemas.item import ItemCreate, ItemRead

            router = APIRouter(prefix="/items", tags=["items"])


            @router.get("", response_model=list[ItemRead])
            async def list_items(service: ItemServiceDep) -> list[ItemRead]:
                items = await service.list_items()
                return [ItemRead.model_validate(item) for item in items]


            @router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
            async def create_item(payload: ItemCreate, service: ItemServiceDep) -> ItemRead:
                item = await service.create_item(payload)
                return ItemRead.model_validate(item)
        ''',
        "backend/app/api/router.py": r'''
            from fastapi import APIRouter

            from app.api.routes import health, items

            api_router = APIRouter()
            api_router.include_router(health.router)
            api_router.include_router(items.router)
        ''',
        "backend/app/main.py": r'''
            from collections.abc import AsyncIterator
            from contextlib import asynccontextmanager

            from fastapi import FastAPI
            from redis.asyncio import Redis

            from app.api.router import api_router
            from app.core.config import settings
            from app.core.database import engine
            from app.core.middleware import install_middleware


            @asynccontextmanager
            async def lifespan(app: FastAPI) -> AsyncIterator[None]:
                redis = Redis.from_url(settings.redis_url, decode_responses=True)
                await redis.ping()
                app.state.redis = redis
                try:
                    yield
                finally:
                    await redis.aclose()
                    await engine.dispose()


            app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
            install_middleware(app)
            app.include_router(api_router, prefix=settings.api_v1_prefix)


            @app.get("/")
            async def root() -> dict[str, str]:
                return {"message": settings.app_name}
        ''',
        "backend/tests/__init__.py": "",
        "backend/tests/test_config.py": r'''
            from app.core.config import settings


            def test_api_prefix() -> None:
                assert settings.api_v1_prefix.startswith("/")
        ''',
        "backend/alembic.ini": r'''
            [alembic]
            script_location = %(here)s/alembic
            prepend_sys_path = .
            path_separator = os
            sqlalchemy.url = postgresql+asyncpg://unused:unused@localhost/unused

            [loggers]
            keys = root,sqlalchemy,alembic
            [handlers]
            keys = console
            [formatters]
            keys = generic
            [logger_root]
            level = WARNING
            handlers = console
            qualname =
            [logger_sqlalchemy]
            level = WARNING
            handlers =
            qualname = sqlalchemy.engine
            [logger_alembic]
            level = INFO
            handlers =
            qualname = alembic
            [handler_console]
            class = StreamHandler
            args = (sys.stderr,)
            level = NOTSET
            formatter = generic
            [formatter_generic]
            format = %(levelname)-5.5s [%(name)s] %(message)s
            datefmt = %H:%M:%S
        ''',
        "backend/alembic/env.py": r'''
            import asyncio
            from logging.config import fileConfig

            from alembic import context
            from sqlalchemy import Connection, pool
            from sqlalchemy.ext.asyncio import async_engine_from_config

            from app.core.config import settings
            from app.models import Base  # imports every model registered with metadata

            config = context.config
            if config.config_file_name is not None:
                fileConfig(config.config_file_name)
            config.set_main_option("sqlalchemy.url", settings.database_url)
            target_metadata = Base.metadata


            def run_migrations_offline() -> None:
                context.configure(
                    url=settings.database_url,
                    target_metadata=target_metadata,
                    literal_binds=True,
                    dialect_opts={"paramstyle": "named"},
                )
                with context.begin_transaction():
                    context.run_migrations()


            def do_run_migrations(connection: Connection) -> None:
                context.configure(connection=connection, target_metadata=target_metadata)
                with context.begin_transaction():
                    context.run_migrations()


            async def run_migrations_online() -> None:
                configuration = config.get_section(config.config_ini_section, {})
                connectable = async_engine_from_config(
                    configuration,
                    prefix="sqlalchemy.",
                    poolclass=pool.NullPool,
                )
                async with connectable.connect() as connection:
                    await connection.run_sync(do_run_migrations)
                await connectable.dispose()


            if context.is_offline_mode():
                run_migrations_offline()
            else:
                asyncio.run(run_migrations_online())
        ''',
        "backend/alembic/script.py.mako": r'''
            """${message}

            Revision ID: ${up_revision}
            Revises: ${down_revision | comma,n}
            Create Date: ${create_date}
            """
            from typing import Sequence, Union

            from alembic import op
            import sqlalchemy as sa
            ${imports if imports else ""}

            revision: str = ${repr(up_revision)}
            down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
            branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
            depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


            def upgrade() -> None:
                ${upgrades if upgrades else "pass"}


            def downgrade() -> None:
                ${downgrades if downgrades else "pass"}
        ''',
        "backend/alembic/versions/0001_create_items.py": r'''
            """Create items table."""

            from collections.abc import Sequence

            import sqlalchemy as sa
            from alembic import op

            revision: str = "0001_create_items"
            down_revision: str | None = None
            branch_labels: str | Sequence[str] | None = None
            depends_on: str | Sequence[str] | None = None


            def upgrade() -> None:
                op.create_table(
                    "items",
                    sa.Column("id", sa.Uuid(), nullable=False),
                    sa.Column("name", sa.String(length=120), nullable=False),
                    sa.Column(
                        "created_at",
                        sa.DateTime(timezone=True),
                        server_default=sa.text("now()"),
                        nullable=False,
                    ),
                    sa.PrimaryKeyConstraint("id"),
                )
                op.create_index(op.f("ix_items_name"), "items", ["name"], unique=False)


            def downgrade() -> None:
                op.drop_index(op.f("ix_items_name"), table_name="items")
                op.drop_table("items")
        ''',
        "frontend/.env.example": r'''
            VITE_API_URL=/api
        ''',
        "frontend/.env": r'''
            VITE_API_URL=/api
        ''',
        "frontend/.oxlintrc.json": r'''
            {
              "$schema": "./node_modules/oxlint/configuration_schema.json",
              "plugins": ["react", "typescript", "oxc"],
              "rules": {
                "react/rules-of-hooks": "error",
                "react/only-export-components": ["warn", { "allowConstantExport": true }]
              }
            }
        ''',
        "frontend/vite.config.ts": r'''
            import tailwindcss from "@tailwindcss/vite";
            import react from "@vitejs/plugin-react";
            import { defineConfig } from "vitest/config";

            export default defineConfig({
              plugins: [react(), tailwindcss()],
              server: {
                proxy: {
                  "/api": {
                    target: "http://127.0.0.1:8000",
                    changeOrigin: true,
                  },
                },
              },
              test: {
                environment: "jsdom",
                setupFiles: "./src/test/setup.ts",
              },
            });
        ''',
        "frontend/src/index.css": r'''
            @import "tailwindcss";

            :root {
              font-family: Inter, ui-sans-serif, system-ui, sans-serif;
              color: #172033;
              background: #f7f8fb;
              font-synthesis: none;
              text-rendering: optimizeLegibility;
            }

            body { margin: 0; min-width: 320px; min-height: 100vh; }
            button, input { font: inherit; }
        ''',
        "frontend/src/vite-env.d.ts": r'''
            /// <reference types="vite/client" />
        ''',
        "frontend/src/lib/env.ts": r'''
            export const env = {
              apiUrl: import.meta.env.VITE_API_URL ?? "/api",
            } as const;
        ''',
        "frontend/src/lib/api.ts": r'''
            import axios from "axios";
            import { env } from "./env";

            export const api = axios.create({
              baseURL: env.apiUrl,
              timeout: 10_000,
              headers: { "Content-Type": "application/json" },
            });
        ''',
        "frontend/src/app/store.ts": r'''
            import { configureStore } from "@reduxjs/toolkit";
            import itemsReducer from "../features/items/itemsSlice";

            export const store = configureStore({
              reducer: { items: itemsReducer },
            });

            export type RootState = ReturnType<typeof store.getState>;
            export type AppDispatch = typeof store.dispatch;
        ''',
        "frontend/src/app/hooks.ts": r'''
            import { useDispatch, useSelector } from "react-redux";
            import type { AppDispatch, RootState } from "./store";

            export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
            export const useAppSelector = useSelector.withTypes<RootState>();
        ''',
        "frontend/src/features/items/types.ts": r'''
            export type Item = {
              id: string;
              name: string;
              created_at: string;
            };
        ''',
        "frontend/src/features/items/itemsApi.ts": r'''
            import { api } from "../../lib/api";
            import type { Item } from "./types";

            export async function fetchItems(): Promise<Item[]> {
              const response = await api.get<Item[]>("/v1/items");
              return response.data;
            }

            export async function createItem(name: string): Promise<Item> {
              const response = await api.post<Item>("/v1/items", { name });
              return response.data;
            }
        ''',
        "frontend/src/features/items/itemsSlice.ts": r'''
            import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
            import { createItem, fetchItems } from "./itemsApi";
            import type { Item } from "./types";

            type ItemsState = {
              values: Item[];
              status: "idle" | "loading" | "ready" | "failed";
              error: string | null;
            };

            const initialState: ItemsState = { values: [], status: "idle", error: null };

            export const loadItems = createAsyncThunk("items/load", fetchItems);
            export const addItem = createAsyncThunk("items/add", createItem);

            const itemsSlice = createSlice({
              name: "items",
              initialState,
              reducers: {},
              extraReducers: (builder) => {
                builder
                  .addCase(loadItems.pending, (state) => {
                    state.status = "loading";
                    state.error = null;
                  })
                  .addCase(loadItems.fulfilled, (state, action) => {
                    state.status = "ready";
                    state.values = action.payload;
                  })
                  .addCase(loadItems.rejected, (state) => {
                    state.status = "failed";
                    state.error = "Could not load items.";
                  })
                  .addCase(addItem.fulfilled, (state, action) => {
                    state.values.unshift(action.payload);
                  });
              },
            });

            export default itemsSlice.reducer;
        ''',
        "frontend/src/features/items/itemsSlice.test.ts": r'''
            import { describe, expect, it } from "vitest";
            import reducer, { addItem } from "./itemsSlice";

            describe("items reducer", () => {
              it("stores an item returned by the API", () => {
                const item = {
                  id: "7b596aca-cfda-442a-b209-417004fe4c51",
                  name: "First item",
                  created_at: "2026-01-01T00:00:00Z",
                };
                const state = reducer(undefined, addItem.fulfilled(item, "request-id", item.name));
                expect(state.values).toEqual([item]);
              });
            });
        ''',
        "frontend/src/features/items/ItemsPage.tsx": f'''
            import {{ type FormEvent, useEffect, useState }} from "react";
            import {{ useAppDispatch, useAppSelector }} from "../../app/hooks";
            import {{ addItem, loadItems }} from "./itemsSlice";

            export function ItemsPage() {{
              const dispatch = useAppDispatch();
              const {{ values, status, error }} = useAppSelector((state) => state.items);
              const [name, setName] = useState("");

              useEffect(() => {{ void dispatch(loadItems()); }}, [dispatch]);

              async function submit(event: FormEvent) {{
                event.preventDefault();
                const value = name.trim();
                if (!value) return;
                await dispatch(addItem(value)).unwrap();
                setName("");
              }}

              return (
                <main className="mx-auto min-h-screen max-w-3xl px-6 py-16">
                  <p className="font-semibold text-indigo-600">Full-stack starter</p>
                  <h1 className="mt-2 text-4xl font-bold tracking-tight">{title}</h1>
                  <p className="mt-3 text-slate-600">
                    React + Redux Toolkit talking to FastAPI, PostgreSQL, and Redis.
                  </p>

                  <form onSubmit={{submit}} className="mt-10 flex gap-3 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
                    <input
                      className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-indigo-500"
                      value={{name}}
                      onChange={{(event) => setName(event.target.value)}}
                      placeholder="Add an item"
                      aria-label="Item name"
                    />
                    <button className="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-500">
                      Add
                    </button>
                  </form>

                  {{status === "loading" && <p className="mt-8 text-slate-500">Loading…</p>}}
                  {{error && <p className="mt-8 text-red-600">{{error}}</p>}}
                  <ul className="mt-6 grid gap-3">
                    {{values.map((item) => (
                      <li key={{item.id}} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                        <span className="font-medium">{{item.name}}</span>
                      </li>
                    ))}}
                  </ul>
                </main>
              );
            }}
        ''',
        "frontend/src/App.tsx": r'''
            import { BrowserRouter, Route, Routes } from "react-router-dom";
            import { ItemsPage } from "./features/items/ItemsPage";

            export default function App() {
              return (
                <BrowserRouter>
                  <Routes>
                    <Route path="/" element={<ItemsPage />} />
                  </Routes>
                </BrowserRouter>
              );
            }
        ''',
        "frontend/src/main.tsx": r'''
            import { StrictMode } from "react";
            import { createRoot } from "react-dom/client";
            import { Provider } from "react-redux";
            import App from "./App";
            import { store } from "./app/store";
            import "./index.css";

            createRoot(document.getElementById("root")!).render(
              <StrictMode>
                <Provider store={store}>
                  <App />
                </Provider>
              </StrictMode>,
            );
        ''',
        "frontend/src/test/setup.ts": r'''
            import "@testing-library/jest-dom/vitest";
        ''',
    }


def bootstrap(target: Path, python_version: str, skip_install: bool) -> None:
    target.mkdir(parents=True)
    if skip_install:
        (target / "backend").mkdir()
        (target / "frontend").mkdir()
        return

    require("uv", "Install it from https://docs.astral.sh/uv/getting-started/installation/.")
    require("npm", "Install a current Node.js LTS release first.")
    run(["uv", "init", "backend", "--no-package", "--python", python_version], target)
    run(
        [
            "npm",
            "create",
            "vite@latest",
            "frontend",
            "--",
            "--template",
            "react-ts",
            "--no-interactive",
        ],
        target,
    )


def install(target: Path) -> None:
    run(["uv", "sync", "--all-groups"], target / "backend")
    run(["npm", "install"], target / "frontend")
    run(
        [
            "npm",
            "install",
            "@reduxjs/toolkit",
            "react-redux",
            "react-router-dom",
            "axios",
            "tailwindcss",
            "@tailwindcss/vite",
        ],
        target / "frontend",
    )
    run(
        [
            "npm",
            "install",
            "--save-dev",
            "vitest",
            "jsdom",
            "@testing-library/react",
            "@testing-library/jest-dom",
        ],
        target / "frontend",
    )

    package_path = target / "frontend/package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["scripts"]["test"] = "vitest run"
    safe_package_name = re.sub(r"[^a-z0-9-]+", "-", target.name.lower().replace("_", "-"))
    package["name"] = f"{safe_package_name.strip('-')}-frontend"
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    run(["npm", "install"], target / "frontend")


def write_fallback_frontend_package(target: Path) -> None:
    safe_package_name = re.sub(r"[^a-z0-9-]+", "-", target.name.lower().replace("_", "-"))
    package = {
        "name": f"{safe_package_name.strip('-')}-frontend",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "tsc -b && vite build",
            "lint": "oxlint",
            "test": "vitest run",
            "preview": "vite preview",
        },
        "dependencies": {
            "@reduxjs/toolkit": "^2.9.0",
            "axios": "^1.12.0",
            "react": "^19.1.0",
            "react-dom": "^19.1.0",
            "react-redux": "^9.2.0",
            "react-router-dom": "^7.9.0",
        },
        "devDependencies": {
            "@tailwindcss/vite": "^4.1.0",
            "@testing-library/jest-dom": "^6.8.0",
            "@testing-library/react": "^16.3.0",
            "@types/node": "^24.5.0",
            "@types/react": "^19.1.0",
            "@types/react-dom": "^19.1.0",
            "@vitejs/plugin-react": "^5.0.0",
            "jsdom": "^27.0.0",
            "oxlint": "^1.81.0",
            "tailwindcss": "^4.1.0",
            "typescript": "~5.9.0",
            "typescript-eslint": "^8.44.0",
            "vite": "^7.1.0",
            "vitest": "^3.2.0",
        },
    }
    write(target, "frontend/package.json", json.dumps(package, indent=2) + "\n")
    write(
        target,
        "frontend/index.html",
        '''
            <!doctype html>
            <html lang="en">
              <head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>Starter</title></head>
              <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
            </html>
        ''',
    )
    write(
        target,
        "frontend/tsconfig.json",
        '''
            {"files": [], "references": [{"path": "./tsconfig.app.json"}, {"path": "./tsconfig.node.json"}]}
        ''',
    )
    write(
        target,
        "frontend/tsconfig.app.json",
        '''
            {"compilerOptions":{"target":"ES2022","useDefineForClassFields":true,"lib":["ES2022","DOM","DOM.Iterable"],"allowJs":false,"skipLibCheck":true,"esModuleInterop":true,"allowSyntheticDefaultImports":true,"strict":true,"forceConsistentCasingInFileNames":true,"module":"ESNext","moduleResolution":"Bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx"},"include":["src"]}
        ''',
    )
    write(
        target,
        "frontend/tsconfig.node.json",
        '''
            {"compilerOptions":{"composite":true,"skipLibCheck":true,"module":"ESNext","moduleResolution":"Bundler","allowImportingTsExtensions":true,"noEmit":true,"types":["node"]},"include":["vite.config.ts"]}
        ''',
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="New project directory (for example: my-app)")
    parser.add_argument("--python", default="3.12", help="Backend Python version (default: 3.12)")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Write all source/config files without downloading dependencies",
    )
    parser.add_argument(
        "--skip-services",
        action="store_true",
        help="Do not start Docker services or apply migrations",
    )
    args = parser.parse_args()

    target = Path(args.name).expanduser().resolve()
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing path: {target}")

    project_name = target.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", project_name):
        raise SystemExit("Project name may contain letters, numbers, hyphens, and underscores.")
    database_name = re.sub(r"[^a-z0-9_]", "_", project_name.lower().replace("-", "_"))

    postgres_port = available_port(5432, set())
    redis_port = available_port(6379, {postgres_port})
    if postgres_port != 5432:
        print(f"PostgreSQL port 5432 is occupied; using {postgres_port} instead.")
    if redis_port != 6379:
        print(f"Redis port 6379 is occupied; using {redis_port} instead.")

    print(f"Creating {project_name} in {target}")
    try:
        bootstrap(target, args.python, args.skip_install)
        if args.skip_install:
            write_fallback_frontend_package(target)

        for relative_path, content in project_files(
            project_name,
            database_name,
            secrets.token_urlsafe(48),
            args.python,
            postgres_port,
            redis_port,
        ).items():
            write(target, relative_path, content)

        if os.name != "nt":
            (target / "scripts/dev.sh").chmod(0o755)

        if not args.skip_install:
            install(target)

        if not args.skip_services:
            require("docker", "Install Docker Desktop or Docker Engine with Compose.")
            run(["docker", "compose", "up", "-d", "--wait"], target)
            if args.skip_install:
                print("Skipping migrations because dependencies were not installed.")
            else:
                run(["uv", "run", "alembic", "upgrade", "head"], target / "backend")

    except Exception:
        print(f"\nScaffolding stopped. Partial output remains at {target}", file=sys.stderr)
        raise

    print("\nDone. Starting the development app...")
    print(f"  Project: {target}")

    if os.name == "nt":
        run(["cmd.exe", "/c", r"scripts\dev.bat"], target)
    else:
        run(["./scripts/dev.sh"], target)


if __name__ == "__main__":
    main()
