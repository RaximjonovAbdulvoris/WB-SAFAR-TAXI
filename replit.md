# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally
- `python -m bot.main` — run the WB TAXI HUMO Telegram bot locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.

## WB TAXI HUMO Telegram Bot

Located in `bot/`. Long-polling Python Telegram bot built with `python-telegram-bot` 21.

- `bot/main.py` — entry point, registers conversation handlers
- `bot/config.py` — loads `TELEGRAM_BOT_TOKEN`, 4× `DRIVER_GROUP_*`, `BRAND_GROUP` from env
- `bot/handlers/start.py` — `/start` and main menu (Ariza Tashlash / Brend Ariza)
- `bot/handlers/driver.py` — 13-step driver registration: name → phone (button) → docs warning → 8 doc photos (passport, license, tech passport, selfie, litsenziya) → 4 car photos → plate. Sends 2 albums (10-photo docs + 2-photo selfie/litsenziya) to all 4 driver groups.
- `bot/handlers/brand.py` — branding application: warning (SPARK/NEXIA 3/<2016 not eligible) → name → phone → model → year → color. Sends formatted message to brand group.
- `bot/templates/` — optional template images (`passport_front.jpg`, etc.) shown to the user when each photo is requested. See `bot/templates/README.md`.

Workflow: `Telegram Bot` (console output, command `python -m bot.main`).
