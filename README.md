# FirstPR

<img src="frontend/public/firstpr-logo.png" alt="FirstPR logo" width="96" />

FirstPR helps new contributors explore public GitHub repositories. It reads repository documentation and open issues, recommends possible starting points when AI is available, generates contribution plans, and turns bug screenshots into issue drafts.

The app uses a Next.js 16 / React 19 frontend, a FastAPI backend, Supabase for authentication and saved data, GitHub's API for repository facts, and Gemma or a configured open-weight model for AI features. Bun runs the frontend. There is no seeded or mock repository data in the UI.

## Features

| Page | What it does |
| --- | --- |
| Dashboard | Shows saved analysis, plan, and triage counts, recent activity, and recommendations from the latest analysis. |
| Repositories | Scans a public GitHub repository and saves its documentation-based conventions and issue recommendations. |
| Plans | Generates and saves a contribution plan for a specific GitHub issue. |
| Bug triage | Analyzes a screenshot, finds related issues, and drafts a report you can copy. |
| History and settings | Shows activity, your profile, and backend connection status. |

FirstPR does not post GitHub issues or create pull requests for you.

## Architecture

```text
Browser (Next.js)
  ├─ Supabase Auth: email sign-up and sign-in
  └─ /api/v1/* with the user's Supabase access token
           ↓ Next.js rewrite
FastAPI
  ├─ verifies the access token
  ├─ reads public repositories through the GitHub API
  ├─ validates AI output and suggested file paths
  └─ stores results and activity in Supabase
```

The browser uses only the Supabase publishable/anon key. FastAPI uses the service-role key for database writes and filters saved records by the authenticated user ID. Keep the service-role key, JWT secret, and AI key on the backend.

## Requirements

- [Bun](https://bun.com/docs/installation).
- Python 3.11 or newer.
- A Supabase project with Email authentication enabled.
- Optional: a GitHub token for a higher API rate limit.
- For AI features: a Gemini API key with access to a Gemma model, or an OpenAI-compatible endpoint serving an open-weight model.

## Local setup

### 1. Set up Supabase

Create a Supabase project and run [supabase/schema.sql](supabase/schema.sql) **once** in its SQL Editor. It creates profiles, repository analyses, plans, triage results, activity history, and row-level security policies.

Enable **Authentication → Providers → Email**. If email confirmation is enabled, add your local frontend origin, such as `http://localhost:3000`, to the allowed redirect URLs and confirm the signup email before signing in.

### 2. Add environment variables

For a fresh checkout, copy [backend/.env.example](backend/.env.example) to `backend/.env` and [frontend/.env.example](frontend/.env.example) to `frontend/.env.local`. If either destination already exists, edit it in place so you do not overwrite credentials. Both local files are ignored by Git.

On Windows PowerShell, these commands copy only when the destination is absent:

```powershell
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env.local)) { Copy-Item frontend\.env.example frontend\.env.local }
```

Backend variables in `backend/.env`:

| Variable | Required | Purpose |
| --- | --- | --- |
| `SUPABASE_URL` | Yes | Supabase project URL. |
| `SUPABASE_KEY` | Yes for saving | **Service-role/secret key**, never the browser anon key. The included SQL policies rely on server-side writes. |
| `SUPABASE_JWT_SECRET` | Yes | Legacy JWT secret. Backend startup requires it; newer asymmetric access tokens are verified through Supabase JWKS. |
| `GEMINI_API_KEY` | For Gemma | Server-side Gemini API key. Leave blank if using the alternative provider. |
| `GEMMA_MODEL` | For Gemma | A Gemma model available to the key; the example uses `gemma-4-26b-a4b-it`. |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Alternative AI provider | An OpenAI-compatible endpoint and open-weight model. Used when `GEMINI_API_KEY` is blank. |
| `GITHUB_TOKEN` | No | GitHub API token to raise the rate limit. Only public repositories are supported. |
| `FRONTEND_ORIGIN` | For direct browser-to-API calls | Origin allowed by FastAPI CORS; defaults to `http://localhost:3000`. |
| `REQUEST_TIMEOUT_SECONDS` | No | Backend HTTP/AI request timeout; defaults to 30. |
| `MAX_UPLOAD_SIZE_MB` | No | Screenshot size limit; defaults to 4. |

Frontend variables in `frontend/.env.local`:

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | The same Supabase project URL. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser-safe Supabase publishable/anon key. |
| `BACKEND_URL` | URL reachable **from the Next.js server**; locally use `http://127.0.0.1:8000`. |

Never place a service-role key or AI key in a `NEXT_PUBLIC_*` variable. Restart a server after changing its environment file.

### 3. Start the backend

From the project root in Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On macOS or Linux, use `python3 -m venv .venv` and `.venv/bin/python -m pip install -r backend/requirements.txt` from the root. Then run `../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/`.

Check [API health](http://127.0.0.1:8000/api/v1/health) and [interactive API docs](http://127.0.0.1:8000/docs). Health reports configuration; it does **not** test an AI generation request or a database write.

### 4. Start the frontend

Open another terminal from the project root:

```powershell
Set-Location frontend
bun install
bun run dev
```

Open [http://localhost:3000](http://localhost:3000), create an account or sign in, and enter a public GitHub URL such as `https://github.com/owner/repo`. HTTPS `github.com` and `www.github.com` repository URLs are accepted, including a trailing slash or `.git` suffix.

## How repository analysis works

1. FastAPI fetches GitHub metadata, README, a contributing guide if present, and the repository file tree.
2. It prefers open issues labeled `good first issue`, then `help wanted`. If neither label yields issues, it checks other open issues.
3. The AI provider extracts documented conventions and scores issues. Its structured output is validated, and suggested file paths must exist in the fetched tree.
4. The analysis is saved to Supabase and appears in your repository list and dashboard.

If AI is missing, times out, or returns an error, the repository scan can still save GitHub facts with a warning. It does not invent recommendations. A repository with no suitable open issues can also have zero recommendations. Plans and screenshot triage require successful AI requests.

## API routes

All paths below are prefixed with `/api/v1`. Apart from health, each request needs `Authorization: Bearer <Supabase access token>`. The frontend sends the token automatically through the Next.js `/api/v1/*` rewrite.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Public health/configuration status. |
| `GET` | `/users/me` | Signed-in user's profile. |
| `GET` | `/dashboard` | Saved counts and recent activity. |
| `POST` | `/repositories/analyze` | Scan a repository. JSON: `repository_url`, optional `issues` (1–20, default 6), optional `top` (1–10, default 3). |
| `GET` | `/repositories` | List your saved analyses. |
| `GET` | `/repositories/{analysis_id}` | Get a saved analysis and refresh its GitHub metadata. |
| `POST` | `/plans` | Generate a plan. JSON: `repository_url` and `issue_number`. |
| `GET` | `/plans` | List your saved plans. |
| `GET` | `/plans/{plan_id}` | Get a saved plan. |
| `POST` | `/triage` | Multipart form: `repository_url`, `image`, optional `note`. |
| `GET` | `/activity` | Activity history; optional `limit` (1–100). |

The backend accepts **PNG and JPEG screenshots up to 4 MB** by default and checks file signatures. The current frontend picker also lists WebP, but the backend rejects WebP uploads.

## Project layout

```text
backend/
  app/api/routes/          API endpoints
  app/services/            GitHub, analysis, planning, triage, activity
  app/ai/                  Providers, prompts, validated output schemas
  app/db/                  Supabase client and queries
  app/core/                Configuration, JWT verification, errors, logging
  tests/                   Backend tests
frontend/
  src/app/                 Next.js layout, entry point, styles, favicon
  src/components/workspace/ Authentication screen and page views
  src/lib/                 API client, Supabase client, shared types
  public/                  FirstPR logo
supabase/schema.sql         Database tables and RLS policies
```

## Checks and production commands

After installing dependencies, run commands from their respective directories:

```powershell
# frontend/
bun run typecheck
bun run build
bun run start

# backend/ on Windows
..\.venv\Scripts\python.exe -m pytest
```

`bun run start` serves the production Next.js build. Keep FastAPI running separately. For deployment, configure the same variables on the respective hosts, set `BACKEND_URL` to an address the Next.js server can reach, and set `FRONTEND_ORIGIN` to the deployed browser origin. Keep secrets on the backend and use HTTPS.

## Troubleshooting and current limits

- **The API will not start:** Fill `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_JWT_SECRET` in `backend/.env`. Run Uvicorn from `backend/` so it reads that file.
- **A scan finishes but is not saved:** Confirm `SUPABASE_KEY` is the service-role key, the SQL schema is installed, and the backend was restarted. Without that key, the frontend may show a temporary analysis preview.
- **AI suggestions are unavailable:** Check your configured provider and its generation access. A `gemma` status from `/health` confirms configuration only. A warning on a saved analysis describes the provider's state **when that scan ran**; analyze again after the provider recovers.
- **GitHub requests fail:** Use a public repository and set `GITHUB_TOKEN` if anonymous rate limits are exhausted.
- **The frontend cannot reach the API:** Confirm FastAPI is running on port 8000, `BACKEND_URL` points to it, and Next.js has been restarted after configuration changes.
- **Saved triage results:** The triage response appears after upload and creates an activity entry, but there is no endpoint to reopen a saved triage. Settings shows profile and connection state but does not edit account preferences.

The service-role key bypasses Supabase row-level security. FastAPI verifies each caller's access token and scopes reads to that user. Never expose the service-role key in browser code or a public repository.

