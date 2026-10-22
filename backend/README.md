AI-Driven Product Assistant — Backend (FastAPI + MongoDB)

This is the backend service for the AI-Driven Product Assistant, built using Python, FastAPI, and MongoDB. It provides RESTful APIs for the React frontend, handling user authentication, product management, feedback collection, feature prioritization, Product Requirements Documents (PRDs), roadmap management, and related product management workflows.

FastAPI provides request validation, asynchronous endpoint support, and automatically generated API documentation.

---

Architecture Overview

backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Application configuration and environment variables
├── db.py                      # MongoDB connection management
├── helpers.py                 # Shared API response helpers and utilities
├── requirements.txt           # Python dependencies
├── .env.example               # Environment configuration template
├── .env                       # Local configuration (git-ignored)
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py         # Authentication: registration and login
│   ├── product_routes.py      # Product management and search
│   ├── state_routes.py        # Application state
│   ├── feedback_routes.py     # Feedback management and bulk import
│   ├── feature_routes.py      # Features and RICE prioritization
│   ├── prd_routes.py          # Product Requirement Documents
│   ├── roadmap_routes.py      # Roadmaps and milestones
│   ├── workspace_routes.py    # Team workspaces
│   ├── theme_routes.py        # Feedback themes
│   ├── dashboard_routes.py    # Recent activity
│   ├── preferences_routes.py  # User preferences
│   └── chat_routes.py         # Assistant conversation history
└── tests/
    ├── __init__.py
    ├── test_api.py
    └── test_database_package.py

database/
├── __init__.py
├── indexes.py                 # MongoDB index creation
├── README.md                  # Database documentation
└── schemas/                   # Collection schemas and validators

Note: This is the intended project structure. Update filenames and directories to match the actual files in your repository.

The "database/" directory is located at the project root, alongside "backend/" and "src/". It contains collection schemas, validation helpers, and index definitions.

The "backend/db.py" module should remain the central location for MongoDB connection management so that database access is consistent throughout the application.

---

1. Prerequisites

Install the following software before running the backend:

- Python 3.10 or newer
- MongoDB Community Server or a MongoDB Atlas database
- Node.js 18 or newer for the React frontend
- Git for version control

You can use a local MongoDB instance or connect to MongoDB Atlas through a connection URI.

---

2. Environment Configuration

Navigate to the backend directory:

cd backend

Create a local environment file from the example:

Windows PowerShell:

Copy-Item .env.example .env

macOS / Linux:

cp .env.example .env

Environment Variables

Configure the variables supported by your application in "backend/.env".

Example:

MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=product_assistant_db
SECRET_KEY=replace-with-a-secure-secret
PORT=8000

Variable| Example Value| Description
"MONGO_URI"| "mongodb://localhost:27017"| MongoDB connection string
"MONGO_DB_NAME"| "product_assistant_db"| Database name
"SECRET_KEY"| A secure random value| Application secret, if required by the authentication implementation
"PORT"| "8000"| Backend server port, if supported by the application

Important: These are example configuration names. Your application may use different variable names, such as "JWT_SECRET_KEY", "JWT_SECRET", or "MONGODB_URL". Keep the names consistent with your actual "config.py", "db.py", and authentication implementation.

If your application still uses "FLASK_SECRET_KEY", "FLASK_ENV", or "FLASK_DEBUG", remove or replace those settings only after confirming that the FastAPI application no longer depends on them.

Security

- Never commit your actual ".env" file to GitHub.
- Keep database credentials and authentication secrets private.
- Commit ".env.example" with placeholder values only.
- Use a strong secret for production deployments.
- Configure MongoDB Atlas network access and database permissions securely.

---

3. Installation and Virtual Environment

Step 1: Navigate to the backend

cd backend

Step 2: Create a virtual environment

Windows:

python -m venv venv

Activate it:

.\venv\Scripts\Activate.ps1

If you are using Command Prompt:

venv\Scripts\activate

macOS / Linux:

python3 -m venv venv
source venv/bin/activate

Step 3: Install dependencies

python -m pip install --upgrade pip
pip install -r requirements.txt

Make sure your "requirements.txt" includes the dependencies actually used by the application, such as:

- "fastapi"
- "uvicorn"
- The MongoDB driver used by your project, such as "pymongo" or "motor"
- "python-dotenv", if used for environment variables
- "pytest", if used for testing

Install the packages through "requirements.txt" rather than maintaining a separate set of manually installed dependencies.

---

4. Running the FastAPI Backend

Make sure your virtual environment is activated and your environment variables are configured.

If "main.py" contains the FastAPI application object named "app", start the development server with:

uvicorn main:app --reload --host 127.0.0.1 --port 8000

The backend will be available at:

http://127.0.0.1:8000

The "--reload" option automatically restarts the server when code changes. Use it for local development, not as a production server configuration.

Alternative: Running through Python

If your "main.py" explicitly starts Uvicorn when executed as a script, you may also be able to run:

python main.py

Otherwise, use the Uvicorn command above.

Automatic API Documentation

FastAPI generates interactive API documentation automatically.

Swagger UI:

http://127.0.0.1:8000/docs

ReDoc:

http://127.0.0.1:8000/redoc

These pages allow developers to inspect the available endpoints, view request and response schemas, and test API requests.

Health Check

If your application implements a health-check endpoint at "/api/health", test it using:

curl http://127.0.0.1:8000/api/health

Example response:

{
  "status": "healthy",
  "database": "connected",
  "db_name": "product_assistant_db"
}

The example response is illustrative. Your actual response depends on the health-check implementation.

If the endpoint does not exist, add it to your FastAPI application or use an existing health endpoint. Do not assume the endpoint is available simply because it is documented here.

---

5. MongoDB Integration

MongoDB stores the application's persistent data, including user accounts, products, feedback, features, PRDs, roadmaps, and other supported application resources.

The backend is responsible for:

1. Reading the MongoDB connection URI from the environment.
2. Establishing a database connection.
3. Accessing the configured database and collections.
4. Processing frontend requests.
5. Returning JSON responses to the React application.
6. Handling database errors appropriately.

Database Configuration

Configure your MongoDB connection using the environment variables expected by the application.

For a local MongoDB instance, an example connection URI is:

mongodb://localhost:27017

For MongoDB Atlas, use the connection URI supplied by your Atlas deployment and store it in your local ".env" file.

Never commit a real Atlas URI containing credentials.

Database Package and Indexes

The root-level "database/" directory documents the application's collection structures, schemas, validators, and index definitions.

Refer to:

database/README.md

for the database documentation.

If your application creates indexes at startup, confirm that this behavior is implemented in the FastAPI application lifecycle or database initialization code.

Index creation should be safe to run repeatedly. If a unique index cannot be created because existing documents contain duplicate values, resolve the duplicates before attempting to create the index.

Note: Database validation and index creation behavior depends on your actual implementation. This README does not imply that validators are automatically applied to every request.

---

6. API Testing

Run the tests from the backend directory with the virtual environment activated:

pytest tests/ -v

If your tests require additional packages, install them through "requirements.txt".

What to Test

Verify the following:

- User registration and login.
- Authentication and authorization.
- Product creation, retrieval, updating, and deletion.
- Feedback creation and management.
- Feature prioritization.
- PRD and roadmap operations.
- Workspace operations.
- MongoDB connectivity.
- Invalid request handling.
- Error responses and appropriate HTTP status codes.

If your tests were originally written for Flask, update them to use FastAPI's testing tools, such as "fastapi.testclient.TestClient", where appropriate.

Also verify that any mocks or fixtures match the database driver used by the FastAPI backend.

---

7. Connecting the React Frontend

The React frontend communicates with the FastAPI backend through HTTP requests.

Step 1: Configure the frontend environment

In the root project directory, create or update the frontend ".env" file:

VITE_API_MODE=real
VITE_API_BASE_URL=http://127.0.0.1:8000/api

Use these settings only if your frontend supports "VITE_API_MODE" and "VITE_API_BASE_URL".

The URL must match the actual FastAPI route prefixes and port.

Step 2: Start the FastAPI backend

From the backend directory:

uvicorn main:app --reload --host 127.0.0.1 --port 8000

Step 3: Start the React frontend

Open a second terminal in the project root:

npm install
npm run dev

Step 4: Open the application

Visit the local frontend URL displayed by Vite, commonly:

http://localhost:5173

The React application should send requests to the configured FastAPI backend, which processes them and interacts with MongoDB.

CORS Configuration

The FastAPI application must allow requests from the React development server's origin.

For example, if the frontend runs on "http://localhost:5173", configure the appropriate CORS middleware in the FastAPI application.

Only allow trusted origins in production. Do not use unrestricted origins with credentialed requests.

Important Integration Checks

Confirm that:

- The frontend's API base URL points to FastAPI, not the old Flask server.
- The frontend and backend use matching endpoint paths.
- HTTP methods match the implemented routes.
- Request bodies match the backend's expected schemas.
- Response formats match the frontend's expectations.
- Authentication tokens, cookies, and session handling work correctly.
- CORS is configured correctly.
- MongoDB changes persist after restarting the backend.

---

8. API Reference Summary

The following endpoints describe the intended API surface of the application. Confirm the actual routes in the FastAPI source code or at "/docs" before relying on this list.

Authentication

Method| Endpoint| Description
POST| "/api/auth/register"| Register a user
POST| "/api/auth/login"| Authenticate a user
POST| "/api/auth/logout"| Log out a user, if implemented

Products and Search

Method| Endpoint| Description
GET| "/api/products"| Retrieve products
GET| "/api/products/search?q=<query>"| Search products
GET| "/api/products/{id}"| Retrieve a product by ID
POST| "/api/products"| Create a product
PUT| "/api/products/{id}"| Update a product
DELETE| "/api/products/{id}"| Delete a product

Application State and Workspaces

Method| Endpoint| Description
GET| "/api/state"| Retrieve application state
GET| "/api/workspaces"| Retrieve workspaces
POST| "/api/workspaces"| Create a workspace
POST| "/api/workspaces/{id}/switch"| Switch the active workspace

Feedback

Method| Endpoint| Description
GET| "/api/feedback"| Retrieve feedback
POST| "/api/feedback"| Create feedback
PUT| "/api/feedback/{id}"| Update feedback
DELETE| "/api/feedback/{id}"| Delete feedback
POST| "/api/feedback/import"| Import feedback records, if supported

Features and Prioritization

Method| Endpoint| Description
GET| "/api/features"| Retrieve features
POST| "/api/features"| Create a feature
PUT| "/api/features/{id}"| Update a feature
DELETE| "/api/features/{id}"| Delete a feature

PRDs and Roadmap

Method| Endpoint| Description
GET| "/api/prds"| Retrieve PRDs
POST| "/api/prds"| Create a PRD
GET| "/api/roadmap"| Retrieve roadmap items
POST| "/api/roadmap"| Create a roadmap item

Chat, Activity, Themes, and Preferences

Method| Endpoint| Description
GET| "/api/activity"| Retrieve recent activity
GET| "/api/chat"| Retrieve chat history
PUT| "/api/chat"| Update chat history
DELETE| "/api/chat"| Clear chat history, if supported
GET| "/api/themes"| Retrieve feedback themes, if implemented
GET| "/api/preferences"| Retrieve user preferences, if implemented

Note: This table is a documentation template based on the intended application features. It is not a guarantee that every route exists or uses the listed HTTP method. FastAPI's generated documentation at "/docs" is the authoritative reference for the routes registered in the running application.

---

9. Development Workflow

A typical local development workflow is:

1. Pull the latest project changes from GitHub.
2. Activate the Python virtual environment.
3. Install any new dependencies.
4. Configure the ".env" file.
5. Start MongoDB or verify MongoDB Atlas connectivity.
6. Run the FastAPI backend.
7. Run the React frontend.
8. Test the APIs and user workflows.
9. Run the automated tests.
10. Commit and push the verified changes to GitHub.

Before committing, review the files being staged and ensure that ".env", virtual environments, caches, and other local-only files are excluded.

---

10. Troubleshooting

Backend fails to start

Check that the virtual environment is active and that all dependencies are installed.

Verify the entry-point filename and application object used in the Uvicorn command.

MongoDB connection fails

Check the connection URI, database permissions, network access, and whether the local MongoDB service is running.

React cannot connect to the backend

Verify the backend port, frontend API base URL, route prefixes, and CORS configuration.

API returns 404

Check the registered FastAPI routes and their prefixes at:

http://127.0.0.1:8000/docs

Authentication fails

Check the request schema, password verification logic, token or session configuration, and frontend handling of authentication responses.

Tests fail

Check whether the tests still expect Flask-specific behavior and whether they use the same database driver and response schemas as the FastAPI implementation.

---

11. Technology Stack

- Frontend: React
- Backend: Python, FastAPI
- API Server: Uvicorn
- Database: MongoDB
- Database Driver: PyMongo or Motor, depending on the implementation
- API Documentation: OpenAPI, Swagger UI, and ReDoc
- Testing: Pytest and applicable FastAPI testing tools
- Version Control: Git and GitHub

---

12. Security and Deployment

Before deploying the application:

- Replace development secrets with secure production values.
- Configure production MongoDB credentials and network permissions.
- Restrict CORS to approved frontend origins.
- Validate incoming requests.
- Enforce authentication and authorization where required.
- Avoid exposing database credentials or sensitive application data in logs.
- Use a production-appropriate server configuration.
- Configure environment variables through the deployment platform.
- Test all critical user workflows against the deployed backend.

---

Project: AI-Driven Product Assistant
Backend Framework: FastAPI
Database: MongoDB