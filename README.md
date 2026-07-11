# Acme Data Room

A due-diligence document repository: import files from Google Drive or upload from your
computer, view them in the browser, and delete them from the room (without touching the
Drive originals).

Built for a take-home assignment. Backend: Flask / SQLAlchemy / Postgres. Frontend:
React / TypeScript / Vite / Tailwind / shadcn-ui.

## Live demo

- App: https://frontend-psi-eight-94.vercel.app
- API: https://acme-dataroom-api.onrender.com

Both are on free tiers, which means two things worth knowing before you click around:

- **The Render backend spins down after 15 minutes idle** and takes ~50s to wake back up on
  the next request — the first click after a while looks stuck; it isn't.
- **Uploaded/imported file bytes don't survive that spin-down** (Render's free tier has no
  persistent disk; see "Design decisions" below). File names/metadata persist in Postgres,
  but viewing a file after an idle period may 404 until you re-import it. A paid Render plan
  with a persistent disk fixes this; documented as a known tradeoff rather than worked around,
  since the assignment explicitly permits local-disk storage over blob storage.
- **The Google OAuth consent screen is in Testing mode** (not verified by Google, which is a
  review process meant for production apps, not a take-home). Only Google accounts added as
  test users in the Cloud Console can complete the "Connect Google Drive" flow — if you're
  reviewing this and want to test that part, let me know your Google account email and I'll
  add it. Upload, view, and delete all work for anyone regardless.

![Empty state](docs/screenshots/01-empty-state.png)
![Drive import dialog](docs/screenshots/02-drive-import-dialog.png)
![Imported files](docs/screenshots/03-imported-files.png)
![Delete confirmation](docs/screenshots/04-delete-confirm.png)

## Architecture

```
frontend/   Vite + React + TS SPA (shadcn/ui components, Tailwind v4)
backend/    Flask API, SQLAlchemy models, Flask-Migrate migrations
```

The frontend never talks to Google directly. All Drive access — OAuth, listing, downloading
— goes through the Flask backend, which is the only thing holding credentials. This keeps
the OAuth client secret and the long-lived refresh token off the browser entirely.

### Data model

**`files`** — one row per file in the data room, regardless of where it came from.
- `source`: `upload` or `google_drive`
- `google_file_id`: set only for Drive imports; used to make re-importing the same file
  idempotent (importing twice returns the existing row instead of duplicating)
- `storage_path`: a random UUID, decoupled from the user-facing `name` — avoids filesystem
  collisions/traversal from untrusted filenames and means renaming never touches disk
- `deleted_at`: soft delete. The physical file is removed from disk immediately (so storage
  doesn't grow unbounded), but the DB row is kept for an audit trail — appropriate for a
  due-diligence context where "what was in the room and when" can matter, even for
  something later removed. Hard delete would be a reasonable simpler choice too; this is the
  one tradeoff I'd flag as worth revisiting with the team.

**`google_oauth_tokens`** — single-tenant token store. This MVP has no login system (an
explicitly optional extra-credit item in the brief), so there's exactly one Drive
connection for the whole app rather than one per user. `access_token` and `refresh_token`
are encrypted at rest (Fernet symmetric encryption, key from `TOKEN_ENCRYPTION_KEY`) since
a stolen DB backup shouldn't be enough to impersonate the OAuth grant. A real multi-tenant
version would add a `user_id` FK and a unique constraint on `(user_id, provider)` — the
single-row assumption in `app/google_client.py` is the main thing that'd need to change.

## Design decisions worth calling out

- **OAuth scope: `drive.readonly`, not `drive.file`.** I started with `drive.file`
  (narrowest possible grant) but it only lets `files.list()` see files the app has already
  touched — it can't browse a user's existing Drive. That only works if you use Google's
  official Picker widget, which handles per-file grants internally. Since this app implements
  its own file browser (the brief allows either), listing arbitrary existing files needs
  `drive.readonly`: full read access, no write/delete capability in Drive. Documented in
  `app/google_client.py`.
- **Token refresh is centralized.** Every Drive-touching route goes through
  `google_client.get_credentials()`, which transparently refreshes an expired access token
  and persists the new one. If the *refresh* token itself is invalid (revoked by the user,
  or otherwise dead — the "expired oAuth token" edge case called out in the brief), the
  stale row is deleted and a 401 is returned with a machine-readable code
  (`drive_reauth_required` / `drive_not_connected`) that the frontend uses to reset to a
  clean "reconnect" state rather than showing a raw error.
- **Google-native files (Docs/Sheets/Slides) are exported, not downloaded.** They have no
  underlying bytes to fetch directly — `download_drive_file()` detects the native mimetypes
  and calls Drive's `export` endpoint instead (Docs → PDF, Sheets → xlsx, Slides → pptx).
  Folders are excluded from the picker entirely (recursive folder import is out of scope for
  this MVP).
- **Idempotent import.** Re-importing a Drive file you've already imported returns the
  existing row rather than creating a duplicate, keyed on `google_file_id`.
- **CORS + cookies, not tokens, for frontend↔backend auth.** The frontend holds no
  credentials at all; it just carries a Flask session cookie used transiently for OAuth CSRF
  protection during the connect handshake.

## Known limitations / what I'd do with more time

- No pagination in the Drive picker beyond the first 50 results (the API supports
  `pageToken`; the frontend doesn't request more pages yet).
- No per-user auth (explicitly optional in the brief) — see the single-tenant note above.
- No search/filtering (explicitly optional in the brief).
- Large uploads/downloads are synchronous within the request; a production version would
  background large Drive exports.

## Setup

### Prerequisites

- Node.js 20+
- Python 3.11+
- PostgreSQL (running locally, or any reachable instance)
- A Google Cloud project with the Drive API enabled and an OAuth 2.0 Web client (see below)

### 1. Google OAuth client

1. [console.cloud.google.com](https://console.cloud.google.com) → new project.
2. **APIs & Services → Library** → enable **Google Drive API**.
3. **APIs & Services → OAuth consent screen** → External → add yourself as a **test user**
   (keeps the app out of Google's verification review while testing).
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → Web
   application → authorized redirect URI: `http://localhost:5000/api/auth/google/callback`
   (adjust host/port to match your backend if different).
5. Note the Client ID and Client Secret.

### 2. Database

```bash
createdb dataroom
# or, via psql:
psql -U postgres -c "CREATE DATABASE dataroom;"
```

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env         # fill in DATABASE_URL, GOOGLE_CLIENT_ID/SECRET, and generate the two keys below
```

Generate the two secrets referenced in `.env.example`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"                              # FLASK_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # TOKEN_ENCRYPTION_KEY
```

```bash
flask db upgrade      # apply migrations
python run.py         # starts on http://localhost:5000
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_API_URL=http://localhost:5000/api
npm run dev                  # starts on http://localhost:5173
```

Open http://localhost:5173, click **Connect Google Drive**, and go.

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/auth/google/status` | Is Drive connected? |
| GET | `/api/auth/google/login` | Redirect to Google consent |
| GET | `/api/auth/google/callback` | OAuth callback (Google → here) |
| POST | `/api/auth/google/disconnect` | Clear the stored token |
| GET | `/api/drive/files` | List the user's Drive files (paginated) |
| POST | `/api/drive/import` | Import a Drive file by `fileId` |
| GET | `/api/files` | List files in the data room |
| POST | `/api/files/upload` | Upload a local file (multipart) |
| GET | `/api/files/:id` | Stream a file for in-browser viewing |
| DELETE | `/api/files/:id` | Remove a file from the data room |
