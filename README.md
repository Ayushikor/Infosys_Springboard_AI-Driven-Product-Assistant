<div align="center">

# 🚀 AI-Driven Product Assistant

### Your Intelligent Companion for Product Management

An AI-powered product management application designed to help organize product workflows, manage requirements, collect feedback, prioritize features, and plan product roadmaps.

</div>

---

## 💡 About the Project

The AI-Driven Product Assistant is a product management application designed to support common product planning and collaboration workflows.

It combines a React frontend with a Python backend built using FastAPI and a MongoDB database. A separate FastAPI AI module provides AI-powered customer-feedback analysis using CrewAI and Google's Gemini model.

The application provides a foundation for managing products, collecting user feedback, prioritizing features, preparing Product Requirements Documents (PRDs), and organizing product roadmaps. AI-powered functionality can be integrated into these workflows to help product teams work more efficiently.

The repository also contains three JSON datasets—customer feedback, user reviews, and support tickets—which are used as the input source for the AI module's combined feedback-analysis workflow.

## 🎯 Problem Statement

Product managers often need to coordinate information across multiple workflows, including:

- Product requirements and documentation.
- Feature requests and prioritization.
- Customer feedback analysis.
- Product planning and roadmaps.
- Collaboration and project information.

Managing these activities separately can make information difficult to organize and maintain.

This project aims to bring these workflows together in a single application, with opportunities to incorporate AI assistance into product management tasks.

## ✨ Key Features

### 🔐 Authentication and User Profiles

Provides backend functionality for user registration, login, and profile-related operations.

### 📦 Product Management

Supports product-related data and management workflows.

### 💬 Feedback Management

Provides functionality for collecting and managing product feedback.

### 🎯 Feature Prioritization

Supports organizing and prioritizing product features.

### 📝 Product Requirements Documents

Provides functionality for managing Product Requirements Documents (PRDs).

### 🗺️ Product Roadmaps

Supports organizing product roadmap information and planning activities.

### 📊 Dashboard

Provides dashboard-related API functionality for presenting application information.

### ⚙️ User Preferences

Includes backend functionality for managing supported user preferences and application settings.

### 🤖 AI-Powered Feedback Analysis

The separate AI module provides four specialized agents for analyzing customer feedback:

- **Theme Extraction:** Identifies common themes and recurring topics.
- **Pain-Point Identification:** Identifies underlying customer problems and frustrations.
- **Feature Request Clustering:** Groups semantically similar feature requests.
- **Trend Analysis:** Analyzes recurring topics and how feedback patterns change over time.

> **Implementation note:** The exact features available depend on the current implementation. The frontend currently defaults to mock API mode (`VITE_API_MODE=mock`). AI endpoints can be tested directly through the AI module's Swagger UI even while frontend-to-AI integration is pending. AI integrations, analytics, and other advanced capabilities should be described as implemented features only after they have been developed and tested.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| React | Frontend user interface |
| JavaScript | Frontend application logic |
| Vite | Frontend development server and build tooling |
| Python | Backend and AI module programming language |
| FastAPI | Main backend API and separate AI module API |
| MongoDB | Application database and persistence |
| Uvicorn | ASGI server for running FastAPI |
| CrewAI | Defines AI agent roles, tasks, and execution workflows |
| Google Gemini | Large language model used by the AI agents |
| Pydantic | Input, output, and structured-response validation |
| Pytest | Automated Python testing |
| Git and GitHub | Version control and team collaboration |

Additional frontend libraries and backend packages may be used depending on the project's implementation.

## 🏗️ System Architecture

The application follows a frontend–backend–database architecture, with a separate AI analysis service.

### AI Feedback-Analysis Workflow

The following diagram illustrates the flow from the three JSON input datasets through preprocessing and the four CrewAI agents to structured results and the application layer.

<div align="center">

### AI Feedback-Analysis Workflow

The following workflow illustrates how customer feedback moves from the three JSON datasets through preprocessing and the four CrewAI agents to structured analysis results.

1. **Input Data:** 100 customer feedback records, 100 support tickets, and 100 user reviews (300 records in total in the currently supplied datasets).

2. **Data Preprocessing – Python:** Validates JSON records, normalizes fields, removes exact duplicates, and processes timestamps.

3. **CrewAI – Feedback Intelligence:** Executes four specialized agents:
   - Agent 1: Theme Extraction
   - Agent 2: Pain-Point Identification
   - Agent 3: Feature Request Clustering
   - Agent 4: Trend Analysis

4. **Structured Analysis Results:** Produces themes, pain points, feature clusters, and trends.

5. **Application Layer:** FastAPI provides backend APIs, MongoDB supports application data persistence, and React provides the frontend interface.

**Figure: AI-Driven Product Assistant – Feedback Intelligence Workflow**

</div>

### Application Architecture

```text
                 👤 USER
                    |
                    v
        +--------------------------+
        |      React Frontend      |
        |                          |
        |  User Interface          |
        |  Forms and Pages         |
        +------------+-------------+
                     |
                     | HTTP Requests
                     v
        +--------------------------+
        |    Main FastAPI Backend  |
        |                          |
        |  API Routes              |
        |  Request Validation      |
        |  Application Logic       |
        +------------+-------------+
                     |
           +---------+---------+
           |                   |
           v                   v
  +----------------+  +----------------------+
  |    MongoDB     |  |  Separate AI Module  |
  | Application    |  |  FastAPI + CrewAI    |
  | Data           |  +----------+-----------+
  +----------------+             |
                                 v
                      +----------------------+
                      | Local JSON Datasets  |
                      +----------+-----------+
                                 |
                                 v
                      +----------------------+
                      |   AI Orchestrator    |
                      +----------+-----------+
                                 |
              +------------------+------------------+
              |          |              |           |
              v          v              v           v
          +--------+ +--------+    +--------+  +--------+
          |Agent 1 | |Agent 2 |    |Agent 3 |  |Agent 4 |
          |Themes  | |Pain    |    |Feature |  |Trends  |
          |        | |Points  |    |Clusters|  |        |
          +--------+ +--------+    +--------+  +--------+
                                 |
                                 v
                      Structured JSON Results
```

### Request Flow

1. A user interacts with the React frontend.
2. The frontend sends an HTTP request to the FastAPI backend.
3. FastAPI validates the request and executes the relevant application logic.
4. The backend interacts with MongoDB when database operations are required.
5. The AI module independently reads the three local JSON datasets through its dataset loader for the combined analysis workflow.
6. The orchestrator prepares agent-specific inputs and executes the four agents.
7. The AI module returns structured JSON results and per-agent execution statuses.
8. Connecting AI-generated results to the React frontend is planned future work.

**Data-source distinction:** MongoDB is used by the main application for persistence and can be populated by the backend dataset-loading script. The AI orchestrator's combined analysis workflow reads the local JSON files under `datasets/`; it does not use MongoDB as that workflow's feedback input source.

## 🤖 AI Feedback Analysis Module

The AI module is a separate FastAPI service located in `ai_module/`. It uses CrewAI to define agent roles and tasks, Google Gemini as the language model, and Pydantic schemas to validate structured inputs and outputs.

### Agent 1 – Theme Extraction

**Agent 1 is the individual agent developed for this contribution.** Its purpose is to identify recurring themes and group semantically similar feedback into meaningful categories.

**Workflow:**

1. Receives feedback records containing an ID, title, and message.
2. Reads every feedback record and identifies recurring topics.
3. Groups semantically similar feedback rather than creating one theme for every comment.
4. Generates a concise theme name and meaningful description.
5. Extracts relevant keywords.
6. Associates original feedback IDs with the appropriate themes.
7. Validates structured output using Pydantic and application-level assignment checks.

The theme schema rejects duplicate IDs in the input request and duplicate IDs within an individual theme. It permits the same feedback ID to appear in multiple themes when the feedback is relevant to more than one topic. Records omitted by the model can be preserved in an `Other / Uncategorized` theme for review.

### Agent 2 – Pain-Point Identification

Agent 2 identifies actual customer difficulties, frustrations, and unmet needs. It groups similar problems and assigns a severity level:

- **High:** Major problems that significantly affect customers or prevent product use.
- **Medium:** Problems that cause noticeable inconvenience.
- **Low:** Minor issues with limited impact.
- **Unknown:** Insufficient information to determine severity.

Its structured output includes pain-point names, categories, severity, descriptions, original feedback IDs, and supporting evidence.

**This agent was developed by a teammate.**

### Agent 3 – Feature Request Clustering

Agent 3 identifies genuine requests for new capabilities, integrations, improvements, or product functionality. It groups semantically similar requests and keeps non-feature-request feedback in an unclustered list.

Its structured output includes feature names, descriptions, categories, mention counts, original feedback IDs, source channels, and unclustered feedback IDs.

**This agent was developed by a teammate.**

### Agent 4 – Trend Analysis

Agent 4 identifies recurring feedback topics and analyzes how their mentions change over time. It uses feedback IDs, source channels, original feedback text, and timezone-aware timestamps.

The service calculates weekly counts from the original timestamps and derives trend directions such as `Increasing`, `Decreasing`, `Stable`, `Emerging`, and `Insufficient Data`. Its output also includes an overall summary, recurring topics, and data-quality notes.

**This agent was developed by a teammate.**

### Dataset Preparation and Integration

The project contains three JSON datasets:

- `datasets/customer_feedback.json`
- `datasets/support_tickets.json`
- `datasets/user_reviews.json`

The AI module's `dataset_loader.py` reads these local files, validates required fields, normalizes records into a common structure, processes timestamps, and handles duplicate IDs.

The normalized records include fields such as:

- `feedback_id`
- `source_channel`
- `raw_text`
- `title`
- `message`
- Timestamp
- Dataset name

The loader was previously verified against the supplied project data, which contained 100 records in each dataset (300 records in total). This count can change if the JSON files are updated.

The repository also contains `backend/scripts/load_datasets.py`, which is used for loading supplied datasets into MongoDB.

MongoDB loading and the AI module's local JSON loading are separate operations.

### Multi-Agent Orchestration

The AI module provides a combined workflow through:

`POST /analysis/run-all`

The orchestrator:

1. Loads the three local JSON datasets.
2. Checks that records are available and within the configured agent input limit.
3. Converts normalized records into the input schema required by each agent.
4. Runs Theme Extraction, Pain-Point Identification, Feature Clustering, and Trend Analysis in sequence.
5. Preserves each successful agent result.
6. Records individual agent failures so one failure does not necessarily stop the remaining agents.

The combined response includes:

- `total_feedback_analyzed`
- `source_counts`
- `execution_order`
- `agent_status`
- `errors`
- `results`

**Possible overall statuses:**

- `completed`: All four agents completed successfully.
- `partial_success`: The workflow ran, but one or more agents failed. Successful results are preserved and failed results are reported separately.

An HTTP 200 response with `partial_success` does **not** mean all four agents succeeded. Always inspect `agent_status` and `errors`.

### Current AI Integration Status

In the latest observed combined execution, the endpoint returned HTTP 200 with `partial_success`.

| Component | Latest Observed Status |
|---|---|
| JSON dataset loader | Previously verified with 300 supplied records |
| Agent 1 – Theme Extraction | Completed successfully in the latest observed combined run |
| Agent 2 – Pain-Point Identification | Requires further debugging and validation verification with its owner |
| Agent 3 – Feature Request Clustering | Requires further debugging and validation verification with its owner |
| Agent 4 – Trend Analysis | Completed successfully in the latest observed combined run |
| Multi-agent orchestration | Returned HTTP 200 with `partial_success` and preserved successful results |
| AI results connected to React frontend | Planned work; not yet verified as complete |

This status reflects the observed run at the time this README was updated and may change as the team updates the agents.

## 📁 Project Structure

The following is a high-level overview of the repository.

```text
Infosys_Springboard_AI-Driven-Product-Assistant/
|
+-- ai_module/
|   +-- app/
|   |   +-- core/
|   |   |   +-- config.py
|   |   +-- schemas/
|   |   |   +-- feature_clustering.py
|   |   |   +-- feedback.py
|   |   |   +-- pain_point.py
|   |   |   +-- theme_extraction.py
|   |   |   +-- trend_analysis.py
|   |   +-- services/
|   |   |   +-- dataset_loader.py
|   |   |   +-- feature_clustering_agent.py
|   |   |   +-- feedback_analyzer.py
|   |   |   +-- orchestrator.py
|   |   |   +-- pain_point_agent.py
|   |   |   +-- theme_extraction_agent.py
|   |   |   +-- trend_analysis_agent.py
|   |   +-- main.py
|   +-- tests/
|   +-- README.md
|   +-- requirements.txt
|
+-- backend/
|   +-- routes/
|   +-- scripts/
|   |   +-- load_datasets.py
|   +-- tests/
|   +-- app.py
|   +-- config.py
|   +-- db.py
|   +-- helpers.py
|   +-- requirements.txt
|   +-- README.md
|
+-- database/
|   +-- schemas/
|   +-- indexes.py
|   +-- README.md
|
+-- datasets/
|   +-- customer_feedback.json
|   +-- support_tickets.json
|   +-- user_reviews.json
|
+-- src/
|   +-- api/
|   +-- components/
|   +-- context/
|   +-- pages/
|   +-- services/
|   +-- utils/
|   +-- App.jsx
|   +-- index.css
|   +-- main.jsx
|
+-- docs/
|   +-- images/
|       +-- ai-feedback-workflow.jpeg
|
+-- index.html
+-- package.json
+-- package-lock.json
+-- postcss.config.js
+-- tailwind.config.js
+-- vite.config.js
+-- README.md
```

## 🚀 Getting Started

Follow these instructions to prepare your local development environment. The main backend, AI module, and frontend run as separate processes during local development.

### Prerequisites

Install the following tools:

- Python compatible with the project's dependencies.
- Node.js and npm.
- Git.
- Access to a MongoDB database, either locally or through MongoDB Atlas.
- A Google Gemini API key for live AI analysis.

### 1. Clone the Repository

```powershell
git clone https://github.com/Ayushikor/Infosys_Springboard_AI-Driven-Product-Assistant.git
cd Infosys_Springboard_AI-Driven-Product-Assistant
```

### 2. Python Environment Setup

The following example creates a shared virtual environment under the backend directory. If you already have `backend/venv`, activate the existing environment instead.

```powershell
python -m venv backend\venv
.\backend\venv\Scripts\Activate.ps1
```

Install the main backend dependencies:

```powershell
python -m pip install -r backend\requirements.txt
```

Install the AI module dependencies into the same environment:

```powershell
python -m pip install -r ai_module\requirements.txt
```

If PowerShell blocks script activation, use an approved execution-policy setting for your machine or activate the environment through Command Prompt.

### 3. Backend Setup

Navigate to the backend directory:

```powershell
cd backend
```

Create a `.env` file inside `backend/` using the backend configuration and any provided example file as a reference. Typical variables include:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=product_assistant_db
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=0
PORT=8000
ENSURE_INDEXES=true
```

For MongoDB Atlas, replace `MONGO_URI` with your own connection string. Do not share database credentials or commit `.env` files.

### 4. Run the Main Backend

Run this command from the `backend/` directory with the virtual environment activated:

```powershell
python -m uvicorn app:app --reload --port 8000
```

The main backend should generally be available at:

`http://127.0.0.1:8000`

### 5. Configure the AI Module

Open a separate terminal from the project root and navigate to `ai_module/`:

```powershell
cd ai_module
```

Create an `.env` file inside `ai_module/`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
```

Keep the Gemini API key private. Do not add it to source code, screenshots, or public commits.

Start the AI module with `ai_module/` as the current working directory so its `.env` file is found as expected.

### 6. Run the AI Module

With the virtual environment activated and the current directory set to `ai_module/`, run:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

The AI module should be available at:

`http://127.0.0.1:8001`

### 7. Frontend Setup

Open another terminal in the project root, where the root `package.json` is located.

Install the frontend dependencies:

```powershell
npm install
```

Start the Vite development server:

```powershell
npm run dev
```

Follow the URL printed by Vite in the terminal, commonly:

`http://localhost:5173`

The current `src/api/apiConfig.js` defaults to mock mode (`VITE_API_MODE=mock`).

When the relevant real API integration is ready, the frontend can be configured using a root `.env` file:

```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Restart the Vite development server after changing environment variables.

Frontend-to-AI-results integration is separate from running the AI module; the AI service can be tested independently through Swagger on port `8001`.

### 8. Load Datasets into MongoDB (Optional Backend Data Setup)

The repository includes `backend/scripts/load_datasets.py`.

To populate MongoDB with the supplied datasets, configure the backend `.env`, ensure MongoDB is reachable, and run the script from the `backend/` directory:

```powershell
python scripts/load_datasets.py
```

This database-loading step is separate from the AI orchestrator's local JSON loading. The combined AI analysis workflow reads the three JSON files from the root `datasets/` directory through `ai_module/app/services/dataset_loader.py`.

## 📚 API Documentation

FastAPI automatically generates interactive API documentation. The project has two separate FastAPI services, each with its own Swagger UI.

| Service | Swagger UI | ReDoc |
|---|---|---|
| Main application backend | `http://127.0.0.1:8000/docs` | `http://127.0.0.1:8000/redoc` |
| AI feedback analysis module | `http://127.0.0.1:8001/docs` | `http://127.0.0.1:8001/redoc` |

### Main Backend Swagger UI

Start the main backend on port `8000` and open:

`http://127.0.0.1:8000/docs`

This documentation displays the routes registered by the main backend, including authentication, state, feedback, workspace, theme, feature, PRD, roadmap, dashboard, preferences, chat, and product routes.

The main backend health endpoint is:

`GET /api/health`

### AI Module Swagger UI

Start the AI module on port `8001` and open:

`http://127.0.0.1:8001/docs`

Use this Swagger UI to test the AI analysis endpoints directly.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Checks whether the AI module is running. |
| POST | `/feedback/analyze` | Analyzes a single feedback text for sentiment, category, pain points, feature requests, and summary. |
| POST | `/themes/extract` | Runs Agent 1 – Theme Extraction. |
| POST | `/pain-points/identify` | Runs Agent 2 – Pain-Point Identification. |
| POST | `/features/cluster` | Runs Agent 3 – Feature Request Clustering. |
| POST | `/trends/analyze` | Runs Agent 4 – Trend Analysis. |
| POST | `/analysis/run-all` | Loads local JSON datasets and runs the combined agent workflow. |

### How to Test an AI Endpoint in Swagger

1. Start the AI module on port `8001`.
2. Open `http://127.0.0.1:8001/docs`.
3. Find and expand the endpoint you want to test.
4. Click **Try it out**.
5. Enter the required JSON request body, if the endpoint accepts one.
6. Click **Execute**.
7. Review the HTTP status code and JSON response.

### Example: Agent 1 – Theme Extraction

Endpoint:

`POST /themes/extract`

Example request:

```json
{
  "feedback": [
    {
      "id": "FB-001",
      "title": "Slow application",
      "message": "The application takes too long to load."
    },
    {
      "id": "FB-002",
      "title": "Loading problems",
      "message": "Pages load very slowly."
    },
    {
      "id": "FB-003",
      "title": "Payment issue",
      "message": "The payment page sometimes freezes."
    }
  ]
}
```

The response contains `total_feedback_analyzed` and `themes`. Each theme includes a name, description, keywords, and associated original feedback IDs.

### Example: Agent 2 – Pain-Point Identification

Endpoint:

`POST /pain-points/identify`

Example request:

```json
{
  "feedback": [
    {
      "id": "FB-001",
      "title": "Slow application",
      "message": "The application takes too long to load."
    },
    {
      "id": "FB-002",
      "title": "Login problem",
      "message": "I cannot log in after resetting my password."
    }
  ]
}
```

The response contains pain-point names, categories, severity, descriptions, original feedback IDs, and supporting evidence.

### Example: Agent 3 – Feature Request Clustering

Endpoint:

`POST /features/cluster`

Example request:

```json
{
  "feedback": [
    {
      "feedback_id": "FB-001",
      "source_channel": "customer_feedback",
      "raw_text": "Please add a dark mode."
    },
    {
      "feedback_id": "REV-001",
      "source_channel": "user_reviews",
      "raw_text": "I would like the application to support a dark theme."
    }
  ]
}
```

The response contains feature clusters and `unclustered_feedback_ids`, with cluster names, descriptions, categories, mention counts, original feedback IDs, and source channels.

### Example: Agent 4 – Trend Analysis

Endpoint:

`POST /trends/analyze`

Example request:

```json
{
  "feedback": [
    {
      "feedback_id": "FB-001",
      "source_channel": "customer_feedback",
      "raw_text": "Checkout is slow.",
      "timestamp": "2026-10-05T10:00:00+05:30"
    },
    {
      "feedback_id": "FB-002",
      "source_channel": "support_tickets",
      "raw_text": "Checkout takes too long.",
      "timestamp": "2026-10-12T10:00:00+05:30"
    }
  ]
}
```

Trend Analysis requires timezone-aware timestamps and at least two feedback records. Weekly counts and trend direction are calculated from the original timestamps.

### Run All Four Agents

Endpoint:

`POST /analysis/run-all`

This endpoint reads the three local JSON datasets through the AI module's dataset loader. The current endpoint does not require a JSON request body.

**Steps:**

1. Start the AI module on port `8001`.
2. Open `http://127.0.0.1:8001/docs`.
3. Expand `POST /analysis/run-all`.
4. Click **Try it out**, if displayed.
5. Click **Execute**.
6. Inspect `agent_status`, `errors`, and `results` in the response.

**Response interpretation:**

- **HTTP 200 with `status: "completed"`:** All four agents completed successfully.
- **HTTP 200 with `status: "partial_success"`:** The workflow ran, but one or more agents failed. Successful results are retained; inspect `agent_status` and `errors`.
- **HTTP 503:** The overall workflow could not start or complete, for example because the datasets could not be loaded or prepared.

An HTTP 200 response with `partial_success` does not mean every agent is working. Always inspect the individual statuses.

## 🔑 Environment Variables

The application uses environment variables for configuration. The variable names depend on the service.

### Backend (`backend/.env`)

Typical configuration includes:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=product_assistant_db
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=0
PORT=8000
ENSURE_INDEXES=true
```

### AI Module (`ai_module/.env`)

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
```

### Frontend (root `.env`)

When using the real main backend API mode, the configuration may include:

```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Refer to the root and backend `.env.example` files and the service configuration files for actual variable names and defaults.

Never publish API keys, database passwords, tokens, or other secrets in source code or documentation.

## 🧪 Testing

### AI Module Tests

The AI module tests are located in `ai_module/tests/`. They cover dataset loading, feedback schemas and quality, individual agent services, and orchestration.

Run from the `ai_module/` directory with the virtual environment activated:

```powershell
python -m pytest tests/ -v
```

Some agent tests use mocked CrewAI responses. Passing mocked tests verifies the tested application logic but does not guarantee that live Gemini requests will succeed. Verify live endpoints separately through the AI module's Swagger UI.

### Main Backend Tests

The main backend tests are located in `backend/tests/`.

Run from the `backend/` directory with the virtual environment activated:

```powershell
python -m pytest tests/ -v
```

The tests may require a reachable test database or other environment configuration. Review the test setup before running database-dependent tests against any database containing important data.

## 🔒 Security Best Practices

- Keep credentials in environment variables.
- Never commit `.env` files containing secrets.
- Validate incoming API requests and AI-generated structured output.
- Apply authentication and authorization to protected application endpoints.
- Restrict CORS to trusted frontend origins.
- Avoid exposing sensitive information in error responses.
- Use a separate test database for automated tests.
- Review dependencies and keep them updated.
- Do not include private customer information in public screenshots, logs, or example requests.

## 🔮 Future Enhancements

Potential future improvements include:

- 🤖 Connecting AI-generated analysis results to the React frontend and relevant dashboards.
- 📊 Advanced product feedback analysis and reporting.
- 🎯 Intelligent feature prioritization.
- 🗺️ Automated roadmap suggestions.
- 📈 Product analytics and reporting.
- 🤝 Improved collaboration workflows.
- 🧠 Retrieval-augmented generation for project knowledge.
- ✅ Further validation and end-to-end testing of Pain-Point Identification and Feature Request Clustering.

These are potential enhancements and planned work, not claims that all capabilities are already implemented.

## 👥 Contributors

This project is being developed collaboratively as part of the Infosys Springboard project initiative.

Agent 1 – Theme Extraction, dataset preparation/loading, and integration of the JSON datasets with the AI analysis workflow are the individual contributions documented here.

Agents 2, 3, and 4 were developed by teammates.

Contributors can use GitHub issues, feature branches, and pull requests to discuss, implement, and review changes.

## 🤝 Contributing

Contributions should follow the team's development workflow:

1. Create or select an appropriate feature branch.
2. Implement changes in files you own or coordinate changes with the relevant teammate.
3. Test the affected functionality.
4. Commit changes with a descriptive message.
5. Open a pull request for review before merging into `main`.

## 📄 License

Add the project's applicable license information here once the team has selected and documented a license.

---

<div align="center">

🚀 **Building Smarter Product Management Workflows**

**AI-Driven Product Assistant**

</div>