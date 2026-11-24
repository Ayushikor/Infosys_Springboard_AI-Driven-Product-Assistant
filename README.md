# AI-Driven Product Assistant
### An AI-Powered Product Management Copilot

An intelligent product management platform that transforms raw customer feedback into actionable product insights using Artificial Intelligence, Natural Language Processing, and automated product management workflows.

The platform helps product managers understand customer needs, identify recurring problems, prioritize features, generate Product Requirement Documents (PRDs), create user stories, and plan product roadmaps from a centralized workspace.

---

## 1. Project Overview

Product managers often work with large volumes of unstructured customer feedback collected from surveys, reviews, support tickets, and other sources.

Manually analyzing this information is time-consuming and makes it difficult to identify recurring problems, understand customer priorities, and translate insights into actionable product decisions.

The AI-Driven Product Assistant addresses this challenge through an AI-powered workspace that automates important product management activities.

Users can upload customer feedback, analyze recurring themes, identify pain points, prioritize features, generate PRDs, and create structured product roadmaps.

## 2. Problem Statement

Product teams frequently struggle with:

- Large volumes of unstructured customer feedback.
- Difficulty identifying recurring customer complaints and product pain points.
- Lack of a consistent, data-driven feature prioritization process.
- Time-consuming preparation of Product Requirement Documents.
- Difficulty translating customer feedback into actionable user stories.
- Fragmented product planning and roadmap management.
- Limited visibility into customer sentiment and emerging product requirements.

**Proposed Solution**

Develop an AI-powered Product Management Assistant that processes customer feedback, extracts meaningful insights, identifies product opportunities, and automates product planning activities through specialized AI agents.

The platform provides a centralized environment for feedback analysis, feature prioritization, PRD generation, and roadmap management.

## 3. Key Features

### AI Copilot Chat
- Conversational interface for interacting with the AI product assistant.
- Context-aware responses based on product data.
- Conversation history and individual conversation management.
- Support for product planning and analysis queries.

### Customer Feedback Management
- Upload customer feedback datasets.
- Process and analyze feedback records.
- Identify recurring complaints and customer pain points.
- Organize feedback into meaningful themes.

### AI-Powered Analysis
- Customer feedback summarization.
- Theme identification and classification.
- Pain-point analysis.
- Sentiment and trend insights.

### Feature Prioritization
- Evaluate product features based on customer needs.
- Identify high-priority features.
- Support structured, data-driven product decisions.

### PRD Generation
- Generate Product Requirement Documents.
- Create structured product requirements.
- Generate user stories and acceptance criteria.

### Product Roadmap
- Organize planned features.
- Track product development priorities.
- Structure product initiatives and milestones.

### Dashboard and Workspace
- Centralized product management dashboard.
- Feedback analytics and insights.
- Workspace management.
- Activity tracking.

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React.js, JavaScript, Vite |
| UI Styling | Tailwind CSS |
| Backend API | Python, FastAPI |
| AI Framework | CrewAI |
| AI Integration | Configured LLM provider and API |
| Database | MongoDB Atlas |
| HTTP Communication | Axios, REST APIs |
| Data Processing | Python, Pandas |
| Development Tools | VS Code, Git, GitHub |

## 5. System Architecture

The application consists of three primary components.

**Frontend**
- React-based user interface.
- Handles user interactions, dashboards, chat, and product management modules.
- Communicates with the backend through REST APIs.

**Backend**
- FastAPI application.
- Handles authentication, database operations, feedback management, and product-related APIs.
- Communicates with the AI module when AI processing is required.

**AI Module**
- Separate FastAPI service.
- Uses CrewAI and specialized agents to perform AI-driven product management tasks.
- Processes feedback and generates structured product insights.

### Application Flow

```text
                 USER
                   |
                   v
          REACT FRONTEND
             (Port 5173)
                   |
                   v
          FASTAPI BACKEND
             (Port 8000)
             /         \
            v           v
       MongoDB       AI MODULE
        Atlas        (Port 8001)
                         |
                         v
                    CrewAI Agents
                         |
                         v
                   LLM Provider
```

## 6. Prerequisites

Install the following before starting the application:

- Python 3.10 or later.
- Node.js (LTS version recommended).
- npm.
- Git.
- Visual Studio Code or another code editor.
- MongoDB Atlas account.
- API key for the LLM provider configured in the AI module.

Verify your installations:

```bash
python --version
node --version
npm --version
git --version
```

## 7. MongoDB Atlas Setup

The application uses MongoDB Atlas as its cloud database.

### Step 1: Create a MongoDB Atlas Account

1. Visit https://www.mongodb.com/cloud/atlas
2. Create an account or sign in.
3. Create a new project.
4. Create a free shared cluster, if available.

### Step 2: Create a Database User

1. Open **Database Access**.
2. Select **Add New Database User**.
3. Set a username and a strong password.
4. Assign the required database privileges.
5. Save the credentials securely.

### Step 3: Configure Network Access

1. Open **Network Access**.
2. Select **Add IP Address**.
3. Add your current IP address.
4. For temporary development testing, you may allow access from anywhere using `0.0.0.0/0`.

Restrict network access to trusted IP addresses for production deployments.

### Step 4: Obtain the MongoDB Connection String

1. Open your cluster.
2. Click **Connect**.
3. Select **Drivers**.
4. Choose Python.
5. Copy the connection string.

It should look similar to:

```text
mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

Replace the placeholders with your actual database username and password.

URL-encode special characters in the password when necessary.

### Step 5: Configure the Database

Use the connection string in the backend environment configuration.

Example:

```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=product_assistant_db
```

Never commit your actual MongoDB credentials to GitHub.

## 8. API Configuration

The application uses separate backend and AI services.

### Backend API

Base URL:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### AI Module API

Base URL:

```text
http://127.0.0.1:8001
```

Interactive API documentation:

```text
http://127.0.0.1:8001/docs
```

### Frontend API Configuration

Configure the frontend environment:

```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Use the actual API base URL expected by the frontend configuration.

### AI Provider API Key

The AI module requires credentials for its configured language model provider.

1. Create an account with the configured LLM provider.
2. Generate an API key.
3. Add the key to the AI module's `.env` file using the environment variable expected by its configuration.
4. Never expose the API key in frontend code or commit it to GitHub.

**Important:** The exact AI provider and environment variable names must match the project's existing `ai_module` configuration.

## 9. Environment Variables

Create separate `.env` files for the services.

### Backend

Location:

```text
backend/.env
```

Example configuration:

```env
MONGO_URI=your_mongodb_atlas_connection_string
MONGO_DB_NAME=product_assistant_db
```

Add any authentication or security variables required by the backend configuration.

### AI Module

Location:

```text
ai_module/.env
```

Example:

```env
# Add the API key required by your configured LLM provider
YOUR_LLM_API_KEY=your_api_key
```

Use the exact variable name expected by your AI module's configuration. The example above is a placeholder, not a literal variable to copy.

### Frontend

Location:

```text
.env
```

Example:

```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Do not share `.env` files publicly.

## 10. Installation and Setup

Clone the repository:

```bash
git clone https://github.com/Ayushikor/Infosys_Springboard_AI-Driven-Product-Assistant.git
```

Navigate into the project:

```bash
cd Infosys_Springboard_AI-Driven-Product-Assistant
```

Install frontend dependencies:

```bash
npm install
```

### Install Backend Dependencies

```bash
cd backend
python -m venv venv
```

Activate the virtual environment.

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Install AI Module Dependencies

Open another terminal:

```bash
cd ai_module
python -m venv venv
```

Activate the environment.

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required `.env` files before starting the services.

## 11. Running the Application

The frontend, backend, and AI module run as three separate services.

Open three terminal windows.

### Terminal 1: Start Backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at:

http://127.0.0.1:8000

### Terminal 2: Start AI Module

```powershell
cd ai_module
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

AI module runs at:

http://127.0.0.1:8001

### Terminal 3: Start Frontend

From the project root:

```bash
npm run dev
```

Frontend runs at:

http://localhost:5173

### Access the Application

Open your browser and visit:

**http://localhost:5173**

The frontend communicates with the backend, which connects to MongoDB Atlas and the AI module.

## 12. Running Tests

### AI Module Tests

```bash
cd ai_module
python -m pytest -q
```

### Python Compilation Check

```bash
python -m compileall app
```

### Frontend Production Build

From the project root:

```bash
npm run build
```

## 13. Project Structure

```text
Infosys_Springboard_AI-Driven-Product-Assistant/
│
├── src/
│   ├── api/
│   ├── components/
│   ├── context/
│   ├── pages/
│   ├── services/
│   └── utils/
│
├── backend/
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── requirements.txt
│   └── .env
│
├── ai_module/
│   ├── app/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   └── .env
│
├── public/
├── package.json
├── vite.config.js
├── .env
└── README.md
```

*The directory tree is a high-level guide. Actual module names and folders may vary as the project evolves.*

## 14. Security Considerations

- Never commit MongoDB credentials.
- Never expose LLM API keys in frontend code.
- Store secrets in environment variables.
- Restrict MongoDB network access.
- Use appropriate authentication and authorization.
- Keep `.env` files out of version control.
- Use HTTPS and secure deployment configurations in production.

## 15. Future Enhancements

- Advanced customer sentiment analysis.
- More sophisticated feedback classification.
- Enhanced predictive feature prioritization.
- Integration with project management platforms.
- Collaborative product planning.
- Improved analytics and reporting.
- Production deployment with scalable infrastructure.

## 16. Contributors

Developed as part of the **Infosys Springboard** project initiative.

Repository:  
https://github.com/Ayushikor/Infosys_Springboard_AI-Driven-Product-Assistant

---

**AI-Driven Product Assistant**  
*Turning customer feedback into smarter product decisions.*
