# AI Product Manager Copilot

A frontend-only React application for product managers to turn customer feedback into prioritized features, PRDs, and a roadmap. Everything runs in the browser. There is no backend, database, or external AI service.

## Quick start

```bash
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

## Accounts

Multiple product managers can use the app. Each account has its own private data.

- **Demo account:** `admin@copilot.com` / `Admin123!`. Preloaded with 22 feedback records, 8 features, 4 PRDs, 8 roadmap items.
- **New users:** click **Create an account** on the login page. Enter a full name, a username (3–20 letters, numbers, or underscores), a work email, a role, and a password. Passwords need 8+ characters with an uppercase letter, a lowercase letter, and a number. New accounts start empty.

Usernames and emails are unique, case-insensitive. Each user's feedback, features, PRDs, roadmap, workspaces, and chat history are stored under their own account and are not visible to other users.

## Features

- **Login and registration** with validation, show/hide password, remember me, and protected routes.
- **Overview dashboard** with four live metrics, a 14-day trend chart, sentiment donut, top themes, high-priority features, an insight card, and recent activity.
- **Workspaces:** create, edit, switch, and view activity.
- **Feedback upload:** drag-and-drop or file picker for CSV and JSON. The file is parsed in the browser, validated, previewed, and imported into your data. Nothing is uploaded to a server.
- **Feedback list:** search, filters (sentiment, theme, source), sortable columns, pagination, row and bulk selection, view/edit/delete with confirmation.
- **Themes:** local keyword-based analysis (labelled mock/local). Recalculates from current feedback. Theme cards show sentiment, impact, priority score, and trend; a detail modal lists related feedback and lets you edit keywords.
- **Prioritization:** RICE scores computed as (Reach × Impact × Confidence) ÷ Effort. Confidence must be 0–1 and effort must be greater than 0. Add, edit, delete, search, filter, sort, and change status.
- **PRD viewer:** template-generated PRDs from a feature, editable sections, status changes, export as Markdown or text, print.
- **Roadmap:** timeline view grouped by month with overdue highlighting, and a kanban view with drag-and-drop plus a select control for keyboard users.
- **AI Copilot chat:** rule-based local assistant that answers from your current data. Clearly labelled demo/mock mode.
- **Settings:** profile, theme toggle, compact tables preference, application info, current API mode, logout.

## Project structure

```
src/
  api/          apiConfig.js, apiClient.js (mock or real), mockApi.js, mockData.js
  components/   layout/ (AppLayout, Sidebar, Topbar, ProtectedRoute)
                common/ (Button, Input, Modal, Badge, DataTable, EmptyState)
  context/      AuthContext, AppDataContext, ThemeContext
  pages/        Login, Register, Dashboard, Workspace, FeedbackUpload, FeedbackList,
                ThemesDashboard, Prioritization, PRDViewer, Roadmap, Chat, Settings, NotFound
  services/     chatService.js
  utils/        csvParser, riceScore, themeAnalyzer, prdGenerator, formatters
```

## Configuration

Copy `.env.example` to `.env` if you want to change the defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_MODE` | `mock` | `mock` runs fully locally. `real` sends requests to the backend. |
| `VITE_API_BASE_URL` | `http://localhost:3000/api` | Backend base URL, used only in `real` mode. |

Do not put secrets in `VITE_*` variables. Vite ships them to the browser.

### Mock mode (default)

All data lives in LocalStorage under `copilot.users` (accounts) and `copilot.data.<userId>` (each user's data). The session is stored in `copilot.session`. Pages call `apiClient`, which routes to `mockApi`. Each call simulates a short network delay and returns `{ success, data, message }`.

### Real mode

Set `VITE_API_MODE=real` and point `VITE_API_BASE_URL` at your backend. `apiClient.js` uses the same method names as mock mode. If the backend is unreachable or returns an error, the UI shows that error. It never silently falls back to mock data.

No backend is included. To connect one, implement the endpoints listed in `src/api/apiClient.js`.

## Known limitations

Be aware of these before a demo or review:

- **Authentication is demo-grade.** Passwords are hashed with SHA-256 and a per-user salt in the browser. This is not production security. A real system needs a server, bcrypt/argon2, HTTP-only cookies or tokens, rate limiting, and email verification.
- **Data is per browser.** LocalStorage is local to one browser profile on one device. Clearing site data deletes accounts and their data.
- **No password recovery.** There is no reset flow, because there is no email service.
- **Theme analysis is keyword-based.** It is not semantic. Feedback that lacks an explicit theme is matched by keywords, so results can be imperfect.
- **Copilot answers are rule-based.** They use your current data and templates, not a language model.
- **Notifications icon is decorative.** It does not show a notification list.
- **Global search** routes to a page with a query string. It does not filter across all data.
- **PRD generation is template-based.** The text is generic and should be edited before use.

## Verification status

The app was built and checked in a sandbox without network access, so `npm install` and `npm run dev` were not run there. What was verified:

- All 38 source files parse without syntax errors.
- Every relative import resolves to an existing file.
- Every `apiClient` call used by the UI maps to a method in `mockApi`.
- RICE, theme analysis, CSV/JSON parsing, and PRD generation pass 15 logic checks.
- Registration, login, password hashing, duplicate detection, per-user data isolation, and session persistence pass 18 checks.

Not verified in that environment: the Vite compile step, rendering in a browser, responsive layout, and light/dark visuals. Run `npm run dev` and check those before presenting.

## Connecting a real backend later

1. Implement the endpoints used in `realApi` in `src/api/apiClient.js`.
2. Set `VITE_API_MODE=real` and `VITE_API_BASE_URL` in `.env`.
3. Replace the client-side password hashing with server-side hashing, and move session handling to the server.
