# AI-Driven Product Assistant

Independent AI module built with FastAPI. The first planned feature is
Feedback Intelligence, with Gemini as the initial model provider and Ollama
support planned for later.

Feedback analysis is not implemented yet.

## Setup

From this directory, create a virtual environment, install the dependencies
from `requirements.txt`, and copy `.env.example` to `.env`. Add your own
Gemini API key to `.env`; do not commit that file.

## Run

Start the development server with:

```bash
uvicorn app.main:app --reload
```
