# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

GitHub destination: https://github.com/RaximjonovAbdulvoris/NAMANTOSH (`main`).
The user replaced the former HUMO-NAMANGAN destination with NAMANTOSH.

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
- `bot/config.py` — loads `TELEGRAM_BOT_TOKEN`, 2× `DRIVER_GROUP_*`, `BRAND_GROUP`, and optional `ARCHIVE_GROUP` from env
- `bot/handlers/start.py` — region selection, explicit confirmation and regional menus. Namangan has contact/office; Tashkent has an additional Spectre Energy application instead.
- `bot/handlers/driver.py` — driver registration: name → phone → document photos → car photos → plate. Sends albums to one operator group, rotating within the selected region.
- `bot/handlers/brand.py` — branding application: eligibility warning → name → phone → model → year → color → plate. Tashkent Spectre Energy asks the same fields without assuming branding eligibility restrictions.
- `bot/subscription.py` — common membership gate for all application types, using @WB_HUMO_TAXI.
- `bot/regions.py` — regional destinations. DRIVER_GROUP_1–2, BRAND_GROUP and ARCHIVE_GROUP are Namangan settings; DRIVER_GROUP_3–4 are no longer used. Never reuse Namangan destinations as a fallback for missing Tashkent destinations.
- `bot/handlers/operator.py` — records are isolated by source chat/message; operator replies and archive destinations follow the application's region, not the applicant's current menu.
- `bot/templates/` — optional template images (`passport_front.jpg`, etc.) shown to the user when each photo is requested. See `bot/templates/README.md`.

Workflow: `Telegram Bot` (console output, command `python -m bot.main`).

### Tashkent destination setup

Provide numeric Telegram chat IDs (typically starting with `-100`) in:

- `TASHKENT_DRIVER_GROUP_1` — driver applications; optional `TASHKENT_DRIVER_GROUP_2` enables rotation between two groups.
- `TASHKENT_BRAND_GROUP` — brand applications.
- `TASHKENT_SPECTRE_GROUP` — Spectre Energy applications.
- `TASHKENT_ARCHIVE_GROUP` — completed Tashkent applications.

Several application types may intentionally use the same Tashkent group ID.
The bot needs permission to send messages/photos in destination groups and to
delete originals in operator groups. It must be an admin of the shared
subscription channel to reliably check membership. Missing destinations block
the affected form before collection. Missing/unavailable archives do not delete
the original application.

One combined conversation handles both forms; `/start` and “Hududni almashtirish”
discard incomplete form data and require a new region confirmation. `/cancel`
returns to the confirmed region's menu. Preserve `bot_persistence.pkl` on durable
storage (`PERSIST_DIR`) across restarts to retain pending applications and relay
metadata. Do not commit persistence data or credentials.

Offline checks: `python -m unittest discover -s tests -v`. Tests use mocked
Telegram calls and do not send real applications.
