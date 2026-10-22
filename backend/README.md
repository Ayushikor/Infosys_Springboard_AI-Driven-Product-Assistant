# AI-Driven Product Assistant -- Backend (Flask + MongoDB)

This is the backend service for the **AI-Driven Product Assistant**, built using Python, Flask, and MongoDB (via PyMongo). It provides RESTful APIs for the React frontend, handling user authentication, product management, feedback collection, feature prioritization, PRD tracking, and roadmap management.

---

## Architecture Overview

```
backend/
├── app.py                  # Application factory, CORS setup, and error handlers
├── config.py               # Reads environment variables via python-dotenv
├── db.py                   # MongoDB connection management (PyMongo)
├── helpers.py              # Uniform API responses, ID generator, normalizers
├── requirements.txt        # Python dependency manifest
├── .env.example            # Template for environment configuration
├── .env                    # Local runtime configuration (git-ignored)
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py      # /api/auth (register, login, logout)
│   ├── product_routes.py   # /api/products (list, search, retrieve by ID, CRUD)
│   ├── state_routes.py     # /api/state (hydrates all React contexts at once)
│   ├── feedback_routes.py  # /api/feedback (CRUD & bulk import)
│   ├── feature_routes.py   # /api/features (RICE scoring & backlog features)
│   ├── prd_routes.py       # /api/prds (Product Requirement Documents)
│   ├── roadmap_routes.py   # /api/roadmap (Timeline & milestones)
│   ├── workspace_routes.py # /api/workspaces (Team workspaces)
│   ├── theme_routes.py     # /api/themes (NLP feedback themes)
│   ├── dashboard_routes.py # /api/activity (Recent activity feed)
│   ├── preferences_routes.py# /api/preferences (User theme & table preferences)
│   └── chat_routes.py      # /api/chat (Assistant conversation history)
└── tests/
    ├── __init__.py
    └── test_api.py         # Pytest test suite with mock MongoDB
```

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.13 supported)
- **MongoDB** running locally (`localhost:27017`) or a remote MongoDB Atlas connection URI.
- **Node.js 18+** (for running the React frontend)

---

## 2. Environment Configuration

Copy the sample environment file to `.env`:

```bash
cd backend
cp .env.example .env
```

*(On Windows PowerShell: `Copy-Item .env.example .env`)*

### Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string (local or MongoDB Atlas) |
| `MONGO_DB_NAME` | `product_assistant_db` | Name of the MongoDB database |
| `FLASK_SECRET_KEY` | `dev-secret-key-student-project` | Secret key used for session signing and cookies |
| `FLASK_ENV` | `development` | Flask environment |
| `FLASK_DEBUG` | `0` | Debug mode (`1` for reload, `0` for production/quiet) |
| `PORT` | `5000` | HTTP port for the Flask backend |

> **Security Note:** Never commit `.env` containing real production passwords or cloud database credentials. Use `.env.example` as a template.

---

## 3. Installation & Virtual Environment

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## 4. Running the Backend Server

With your virtual environment activated:

```bash
python app.py
```

The server will start on:
```
http://localhost:5000
```

Verify that the server and database are healthy:
```bash
curl http://localhost:5000/api/health
```
Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "db_name": "product_assistant_db"
}
```

---

## 5. Running the Tests

The test suite runs against an in-memory mock MongoDB layer so it can be executed anywhere without a running database daemon:

```bash
pytest tests/ -v
```

---

## 6. Connecting the React Frontend

The React frontend includes a built-in switch between local mock data and the live Flask backend:

1. Open `.env` (or create one from `.env.example`) in the **root project directory**:
   ```ini
   VITE_API_MODE=real
   VITE_API_BASE_URL=http://localhost:5000/api
   ```
2. Start the React development server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser. The React application will now send all requests to `http://localhost:5000/api` and persist data in MongoDB.

---

## 7. API Reference Summary

All API responses follow a uniform JSON structure:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Authentication
- `POST /api/auth/register` - Create a new user account.
- `POST /api/auth/login` - Authenticate with email and password.
- `POST /api/auth/logout` - Clear user session.

### Products & Search
- `GET /api/products` - Retrieve products with optional query parameters (`?q=...`, `?category=...`, `?status=...`).
- `GET /api/products/search?q=<query>` - Dedicated product search endpoint.
- `GET /api/products/<id>` - Retrieve a single product by ID (returns 404 if missing).
- `POST /api/products` - Create a new product.
- `PUT /api/products/<id>` - Update product fields.
- `DELETE /api/products/<id>` - Remove a product.

### Application State & Workspaces
- `GET /api/state` - Returns all collections (feedback, features, prds, roadmap, themes) in one round trip to hydrate the frontend.
- `GET /api/workspaces` - List workspaces.
- `POST /api/workspaces` - Create workspace.
- `POST /api/workspaces/<id>/switch` - Switch active workspace.

### Feedback
- `GET /api/feedback` - Retrieve feedback items.
- `POST /api/feedback` - Create new feedback.
- `PUT /api/feedback/<id>` - Update feedback item.
- `DELETE /api/feedback/<id>` - Delete feedback item.
- `POST /api/feedback/import` - Bulk import feedback records from CSV/JSON.

### Features & Prioritization (RICE)
- `GET /api/features` - Retrieve backlog features.
- `POST /api/features` - Add feature with reach, impact, confidence, and effort.
- `PUT /api/features/<id>` - Update feature.
- `DELETE /api/features/<id>` - Remove feature.

### PRDs & Roadmap
- `GET /api/prds` - Retrieve Product Requirement Documents.
- `POST /api/prds` - Create PRD document.
- `GET /api/roadmap` - Retrieve roadmap items.
- `POST /api/roadmap` - Add milestone or release item.

### Chat & Activity
- `GET /api/activity` - Fetch the audit log of recent workspace actions.
- `GET /api/chat` - Retrieve assistant conversation history.
- `PUT /api/chat` - Persist updated conversation history.
- `DELETE /api/chat` - Clear chat history.
