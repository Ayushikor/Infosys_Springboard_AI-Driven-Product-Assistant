AI-Driven Product Assistant — Backend

This is the backend service for the AI-Driven Product Assistant project. It uses Python, FastAPI, and MongoDB to provide APIs for the React frontend.

Technologies Used

- Python
- FastAPI
- MongoDB
- Uvicorn
- Pydantic

Project Structure

backend/
├── app.py
├── config.py
├── db.py
├── helpers.py
├── requirements.txt
├── .env.example
├── routes/
├── tests/
└── README.md

Note: The actual files and folders may differ depending on your project.

Prerequisites

Install the following before running the backend:

- Python 3.10 or a compatible version required by your dependencies
- MongoDB Atlas account or a local MongoDB installation
- Git

Installation

1. Navigate to the backend directory

cd backend

2. Create a virtual environment

python -m venv venv

3. Activate the virtual environment

Windows PowerShell:

.\venv\Scripts\Activate.ps1

4. Install dependencies

python -m pip install -r requirements.txt

Environment Configuration

Create a ".env" file in the backend directory using ".env.example" as a reference.

Add your MongoDB connection string and any other required configuration.

Important: Use the environment variable names expected by your actual "config.py" and "db.py" files. Never commit your ".env" file or expose database credentials.

Running the Backend

If "app.py" contains an object named "app" initialized with "FastAPI()", start the server with:

uvicorn app:app --reload

The backend will usually be available at:

http://127.0.0.1:8000

API Documentation

When the server is running, open these pages in your browser:

- Swagger UI: "http://127.0.0.1:8000/docs"
- ReDoc: "http://127.0.0.1:8000/redoc"

These pages display the API endpoints registered in your FastAPI application.

Frontend Integration

The React frontend should send HTTP requests to the FastAPI backend.

Make sure the frontend's API base URL matches the address and port where the backend is running.

Database Integration

MongoDB stores the application's data. The database connection should be configured using environment variables and the existing database configuration code.

Verify that MongoDB is reachable before testing database-dependent API endpoints.

Testing

Start the backend and test the available endpoints using Swagger UI or your preferred API testing tool.

Verify registration, login, profile access, and other implemented features.

Security

- Keep database credentials in environment variables.
- Never commit ".env" files or secrets.
- Validate incoming request data.
- Protect authenticated endpoints appropriately.
- Configure CORS for the frontend origins that should be allowed.

Development Status

The backend is under development as part of the AI-Driven Product Assistant project. Features and API endpoints depend on the current implementation.
