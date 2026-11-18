# NAPS Physics Library

Study materials for the National Association of Physics Students, Covenant University. One Postgres database feeds a Telegram bot and (from phase 5) a student website and admin dashboard.

Students are 100L to 400L undergraduates, mostly on phones with small data bundles. Browsing and downloading need no account.

## Phase status

| Phase | Scope | State |
| --- | --- | --- |
| 1 | Bot foundation: browse, search, uploads, duplicates, versions, admin commands, scheduler endpoints | Built, awaiting review |
| 2 | Favourites, offline packs, opportunities, templates, final year project topics, feedback, events | Not started |
| 3 | GPA tools, polls, scheduled broadcasts, course reviews | Not started |
| 4 | Practice questions, ask-the-class board, points, tutor directory | Not started |
| 5 | Admin dashboard | Not started |
| 6 | Student website and account linking | Not started |

Phase 1 ships no website code. The `/web` folder arrives with phase 5.

## What runs where

| Part | Host | Free tier |
| --- | --- | --- |
| Bot service | Render or Koyeb, webhook mode | Sleeps after idle, wakes on request |
| Database | Supabase Postgres | Pauses after a week of inactivity |
| File storage | Supabase Storage, private bucket | 1 GB |
| Scheduler | cron-job.org | 1 minute jobs allowed |
| Website | Vercel | Hobby plan |

## Setup

### 1. Supabase project

Create a project at supabase.com. Open Project settings, then Database, then Connection string, and copy the URI. Add `?sslmode=require` if it is missing. That string is `DATABASE_URL`.

Open the SQL editor, paste `supabase/migrations/0001_phase1_core.sql`, and run it. Later phases add numbered files; run them in order and never edit one that has already run.

Every table has Row Level Security switched on with no policies, so the public anon key can read nothing. The service role key bypasses RLS and stays on the server.

### 2. Storage bucket

Storage, then New bucket. Name it `materials`, keep it private, and add no policies. Files are only reachable through signed URLs the server creates.

### 3. Bot with BotFather

Send `/newbot`, choose a name and a username ending in `bot`, and keep the token for `BOT_TOKEN`.

Set the profile picture to `web/public/brand/naps-logo-color.png` once the owner has placed it. Add a description through `/setdescription`: `Past questions, notes and lab templates for Covenant University physics students.` The command menu is set by the code on startup, so do not set it by hand.

### 4. Environment

```
cd bot
cp .env.example .env
```

| Variable | Where it comes from |
| --- | --- |
| `BOT_TOKEN` | BotFather |
| `WEBHOOK_SECRET` | Any long random string; part of the webhook URL |
| `PUBLIC_URL` | Public base URL of the bot service, no trailing slash |
| `DATABASE_URL` | Supabase connection string |
| `OWNER_ID` | Your numeric Telegram id, from @userinfobot |
| `CRON_SECRET` | Any long random string; sent as the `x-cron-secret` header |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key, server only |
| `SUPABASE_ANON_KEY` | Supabase anon key, used by the website from phase 6 |
| `STORAGE_BUCKET` | `materials` |
| `SESSION_SECRET` | Random string for dashboard sessions, used from phase 5 |
| `BOT_USERNAME` | Bot handle without the @ |
| `SITE_URL` | Website URL, used from phase 6 |
| `GEMINI_API_KEY` or `GROQ_API_KEY` | Free API key, used from phase 4 |

Secrets live in `.env` and in the host's environment settings. `.env` is ignored by git; `.env.example` only lists names.

### 5. Run the bot locally

```
cd bot
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python -m app.poll
```

Polling removes any registered webhook, so run it only while developing. On first start the owner id becomes the super admin.

Talk to the bot: `/start`, pick a level, `/addcourse PHY201 | Classical Mechanics | 200 | 1`, then send a PDF with the caption `PHY201 | pq | First semester past questions | 2023 | 1 | Dr Okafor`.

### 6. Seed courses

```
python scripts/seed_courses.py courses.csv
```

The CSV has four columns: `code,title,level,semester`. See `scripts/courses.example.csv` for the shape. Rows are upserted, so re-running is safe. Use the bot's virtualenv so `app` imports resolve.

### 7. Deploy the bot

Render: new Web Service from the repository, root directory `bot`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check path `/health`, plan Free. Add every variable from the table with `PUBLIC_URL` set to the service URL. On boot the service registers `PUBLIC_URL/webhook/WEBHOOK_SECRET`.

Koyeb works the same way: same start command, same port variable, same health path.

A sleeping free service takes a few seconds to answer the first message of the day.

### 8. cron-job.org

Two jobs, both hitting the deployed service:

| Job | Schedule | Request |
| --- | --- | --- |
| Tick | every 1 minute | `POST PUBLIC_URL/cron/tick`, header `x-cron-secret: CRON_SECRET` |
| Health | every 10 minutes | `GET PUBLIC_URL/health` |

The tick keeps Supabase awake and is where scheduled broadcasts, poll closing and opportunity archiving will run from phase 2 onward. Phase 1 has nothing due yet, so it only pings the database.

### 9. Website

Phases 5 and 6. Vercel setup and deployment steps get added here when those phases land.

## Commands

Student commands:

| Command | What it does |
| --- | --- |
| `/start` | Pick a level |
| `/browse` | Level, course, category, file list |
| `/search <word>` | Course code or title matches |
| `/pq PHY201 2023 sem2` | Past questions by code, year and semester |
| `/notify` | New-file alerts on or off |
| `/help` | Command list |

Admin commands, filtered by role:

| Command | Role |
| --- | --- |
| Send a file, with or without a caption | super, uploader |
| `/addcourse CODE \| Title \| Level \| Semester` | super, uploader |
| `/addadmin <id> <role>`, `/rmadmin <id>`, `/admins` | super |
| `/ban <id>`, `/unban <id>`, `/mute <id> <minutes>` | super, moderator |
| `/maintenance <message>`, `/maintenance off` | super |
| `/backup` | super |
| `/transferowner <id>` | super |

## Admin guide

Roles. Super runs everything. Moderator handles people and announcements. Uploader handles files, courses and (from phase 2) opportunities. `OWNER_ID` is always super and cannot be removed.

Uploading. Send a document with a caption in the form `CODE | category | title | year | semester | lecturer`. Categories are `pq`, `notes`, `test`, `assign`, `template` and `other`. Year, semester and lecturer are optional. Send a document with no caption and the bot asks for each field with buttons.

Telegram only lets a bot download files up to 20 MB, so larger files are refused with a pointer to the dashboard upload. Files already in the library are rejected by SHA-256, whatever the filename.

Versions. A new file with the same course, category, title and year bumps the version. The previous row is marked outdated, and lists show current files first with `outdated` on the rest.

New-file alerts. After an upload the bot messages students at the course's level who have alerts on, at 25 messages per second. Those who blocked the bot are marked inactive and skipped.

Courses. `/addcourse` creates or updates a row. Materials on a course whose level changes stay with the course.

Pausing. `/maintenance <message>` blocks students with that message while admins keep working. `/maintenance off` resumes.

Backup. `/backup` sends a JSON file with every table in it. Keep a copy outside Telegram too.

Handing over the bot inside the app. `/transferowner <id>` asks for confirmation, then makes that person super. Update `OWNER_ID` in the environment afterwards so a restart keeps the right owner.

## Manual QA, phase 1

1. Fresh clone, `.env` filled, migration run, `python -m app.poll` running, `/start` answers.
2. Tapping a level stores it and lists that level's courses.
3. `/addcourse PHY201 | Classical Mechanics | 200 | 1` shows up under 200L.
4. A PDF sent with a full caption appears in Past questions, opens, and arrives as a file.
5. Sending the same PDF again is refused as a duplicate.
6. A different PDF with the same title, category and year becomes version 2, and version 1 is labelled outdated.
7. `/search mechanics` and `/search PHY201` both find the file.
8. `/pq PHY201 2023` filters by year, `sem2` filters by semester.
9. The Lecturer button lists recorded lecturers and filters the list.
10. A second account at the same level receives the new-file alert; `/notify` stops it.
11. A student who sends a document gets a refusal, not an upload.
12. A banned student gets silence; `/unban` restores access.
13. `/maintenance Down for updates` blocks students, leaves admins working, and `/maintenance off` restores access.
14. `/backup` returns a JSON document and `audit_log` has the action.
15. `POST /cron/tick` without the header returns 401; `/health` returns counts.
16. `pytest` passes in `bot/`.

## Files and downloads

The bucket is private and never listable. The bot sends a file the first time by uploading the bytes from storage, then caches the returned `telegram_file_id`, so repeat sends are instant. Files above the 50 MB Bot API limit become a link to the website download route, which logs the event and redirects to a 60 second signed URL.

Storage sits behind one small interface in `bot/app/services/storage.py`. Moving to Cloudflare R2 means replacing the `SupabaseStorage` class there and nothing else.

## Shared files

Materials may include lecturers' work. They are shared for study, and the credit stays with whoever wrote them. A student can report a file from the website or the bot, and an admin can remove it in one action from the dashboard.

## Security notes

- The webhook path carries `WEBHOOK_SECRET`; a wrong value gets a 403.
- `/cron/tick` requires `x-cron-secret`.
- Every query is parameterised, every piece of user text is length-limited and HTML-escaped before it is sent back.
- RLS is on for every table with no policies; the service role key never reaches a browser.
- Admin actions write to `audit_log`.
- Tokens are never logged.

## Design

Tokens live in one place once the website exists: brand red `#741810`, aqua `#96CBE4`, ink `#322B29`, success `#00AA68`, green text `#00683E`, muted `#675F5C`, ground `#F3F8FB`, border `#D9E4EA`.

Headings use Lemon Milk Medium, which is not on Google Fonts. Until the owner supplies the file for `@font-face`, the site uses Montserrat 600 to 700 uppercase in its place. Abril Fatface covers formulas, numbers, course codes and years; Inter covers body text. Both come from Google Fonts with `font-display: swap`.

Bot copy carries no custom fonts. It uses colour, the logo and plain sentences.

Place the brand files at `web/public/brand/naps-logo-color.png` and `web/public/brand/naps-logo-mono.png`.

## Handover for the next executive

1. Move the GitHub repository, the Supabase project and the Render or Koyeb service into a shared department account. Do the same with Vercel when the website exists.
2. Add the new executives as admins with `/addadmin`.
3. Rotate the bot token with BotFather `/revoke`, then update `BOT_TOKEN` in the host and restart.
4. Use BotFather's transfer option to move bot ownership.
5. Run `/transferowner <id>` and update `OWNER_ID` in the host environment.
6. A brand new bot needs no file migration. Files live in storage, so clear the cached ids with `update materials set telegram_file_id = null;` and the bot re-uploads on the next request.

## Free tiers change

Check these before each semester:

- Render free services sleep after about 15 minutes idle, and the first message after a sleep is slow.
- Supabase pauses free projects after a week without activity; the cron tick prevents that.
- Supabase Storage gives 1 GB free. Past that, either prune old versions or move to Cloudflare R2.
- Supabase has a per-file upload limit on the free plan; keep the dashboard's limit in mind when the bucket is created.
- Gemini and Groq free quotas change often, which is why phase 4 caches questions and caps each student per day.

## Repository layout

```
bot/
  app/
    handlers/      student and admin Telegram flows
    middleware/    student upsert, ban, maintenance, throttle, usage logging
    services/      storage, catalog, caption parsing, versioning, permissions, files
    config.py      settings from the environment
    main.py        FastAPI webhook host, /health, /cron/tick
    poll.py        local polling entrypoint
  tests/           pure logic tests
supabase/
  migrations/      numbered SQL files, one per phase
scripts/
  seed_courses.py  CSV course import
  courses.example.csv
```
