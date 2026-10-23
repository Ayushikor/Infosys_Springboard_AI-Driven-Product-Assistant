# AI Feedback Analysis Module

## Overview
A FastAPI-based AI service that analyzes product feedback using Google's Gemini model. It classifies sentiment, identifies feedback categories, extracts pain points and feature requests, and generates a concise summary.

## Tech Stack
- **Language:** Python
- **Backend:** FastAPI, Uvicorn
- **LLM Provider:** Google Gemini API
- **Model:** `gemini-3.1-flash-lite`
- **Validation:** Pydantic

## Features
- Sentiment analysis
- Feedback categorization
- Pain-point extraction
- Feature-request extraction
- Structured JSON responses

## Setup

Run these commands from the project root:

```bash
cd ai_module
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file inside `ai_module/`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
```

Keep your API key private. Never commit `.env` to Git.

## Run the Service

```bash
uvicorn app.main:app --reload --port 8001
```

API documentation: `http://127.0.0.1:8001/docs`

## API Endpoint

**POST** `/feedback/analyze`

Example request:

```json
{
  "feedback": "The app is useful, but it loads slowly and needs dark mode."
}
```

The response contains structured feedback analysis, including sentiment, category, pain points, feature requests, and summary.

**GET** `/health` — checks whether the service is running.

## Testing

```bash
pytest -q
```

## Project Structure

```text
ai_module/
├── app/
│   ├── core/config.py
│   ├── main.py
│   ├── schemas/feedback.py
│   └── services/feedback_analyzer.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Integration
This module runs as an independent service. The main backend or frontend can call its API to analyze product feedback.
