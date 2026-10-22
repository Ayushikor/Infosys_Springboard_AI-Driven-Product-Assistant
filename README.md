# Infosys Springboard: AI-Driven Product Assistant

The **AI-Driven Product Assistant** (AI Product Manager Copilot) is a web application designed to help product managers analyze feedback, extract themes, calculate RICE prioritization scores, generate Product Requirement Documents (PRDs), manage roadmaps, and interact with an AI product assistant.

The project consists of:
- **Frontend:** Built with React 18, Vite, Tailwind CSS, Recharts, and Axios.
- **Backend:** Built with Python, Flask, PyMongo, and MongoDB.

---

## Quick Start Guide

### 1. Backend Setup (Flask + MongoDB)

1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Copy `.env.example` to `.env` (or configure your MongoDB URI):
     ```bash
     cp .env.example .env
     ```
   - By default, it connects to a local MongoDB instance at `mongodb://localhost:27017` with database `product_assistant_db`.
5. Run tests:
   ```bash
   pytest tests/ -v
   ```
6. Start the Flask backend:
   ```bash
   python app.py
   ```
   *The backend will run on `http://localhost:5000`.*

---

### 2. Frontend Setup (React + Vite)

1. Open another terminal in the root project folder:
   ```bash
   npm install
   ```
2. Enable real backend mode:
   - In `.env` (create from `.env.example` if needed), set:
     ```ini
     VITE_API_MODE=real
     VITE_API_BASE_URL=http://localhost:5000/api
     ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:5173` in your browser.

---

## Project Structure

```
├── .env.example            # Frontend environment variable template
├── backend/
│   ├── app.py              # Flask app factory, CORS, and error handlers
│   ├── config.py           # Configuration from environment variables
│   ├── db.py               # Database connection using PyMongo
│   ├── helpers.py          # Response formatters and data normalizers
│   ├── requirements.txt    # Python dependencies (Flask, PyMongo, bcrypt, pytest)
│   ├── .env.example        # Backend environment template
│   ├── routes/             # REST API routes (auth, products, feedback, features, PRD, roadmap)
│   └── tests/              # Test suite
├── src/                    # React frontend application
│   ├── api/                # API client configuration
│   ├── components/         # Reusable UI components
│   ├── context/            # Authentication and App Data contexts
│   ├── pages/              # Views (Dashboard, Feedback, Prioritization, PRDs, Roadmap, Chat)
│   └── utils/              # Calculation helpers (RICE scoring, theme analysis)
└── package.json            # Frontend npm scripts and dependencies
```

---

## Information to Confirm with Your Teammate

If your teammate is managing the shared MongoDB database or deployment, confirm the following:
1. **MongoDB Connection String (`MONGO_URI`)**:
   - Local: `mongodb://localhost:27017`
   - Cloud / Atlas: `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority`
2. **Database Name (`MONGO_DB_NAME`)**:
   - Configured default: `product_assistant_db` (change in `.env` if your team agreed on a specific database name).
3. **Specific Collection Names**:
   - Defaults used: `products`, `users`, `feedback`, `features`, `prds`, `roadmap`, `workspaces`, `themes`, `activity`, `chat_messages`.
