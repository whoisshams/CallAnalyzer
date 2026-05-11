# Call Recording Analyzer Frontend

Vite + React + JavaScript frontend scaffold for the Call Recording Analyzer.

## Local Development

Install frontend dependencies:

```bash
npm install
```

Start the frontend dev server:

```bash
npm run dev
```

By default, the app expects the backend at `http://localhost:8000`. Override it with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Run the backend API from the repository root in a separate terminal:

```bash
cd backend
source ../.venv/bin/activate
uvicorn api.main:app --reload
```

## API Client

The API helper lives in `src/lib/api.js`.

Available helpers:

- `checkHealth()` calls `GET /health`.
- `analyzeTranscript(payload)` calls `POST /analyze`.
