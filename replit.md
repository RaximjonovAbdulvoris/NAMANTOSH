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

## TURON TAXI Telegram bot

Python bot: `python -m bot.main`. Regions: Toshkent and Namangan. The driver form collects
name, phone, document and car photos. The brand form collects basic car details.
No Spectre form, membership gate, office page, AI OCR, Google Sheets or extra operator queues.
The driver operator controls are Tayyor, Izoh berish and Jarayonda.

Configure the bot token and Namangan group IDs using the existing environment values:
`TELEGRAM_BOT_TOKEN`, `DRIVER_GROUP_1`, `DRIVER_GROUP_2`, `BRAND_GROUP`, `ARCHIVE_GROUP`.
Tashkent group IDs can be supplied as `TASHKENT_*` environment variables or
with `python -m bot.configure tashkent`. Each region uses its own destinations.
Contact details are read from `TURON_CONTACT_TASHKENT` and `TURON_CONTACT_NAMANGAN`;
leave them blank until actual details are supplied. `PERSIST_DIR` must be durable.
Do not deploy on top of a running HUMO bot or reuse its token/state.

Run `python -m unittest discover -s tests -q` to check offline behavior.
