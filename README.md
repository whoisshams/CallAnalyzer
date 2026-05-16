# CallAnalyser

A configurable hub-and-spoke multi-agent QA system for analyzing call center recordings. A coordinator dispatches three specialized AI reviewers in parallel — agent tone, patient tone, and call outcome — and streams live progress to the browser as each result arrives.

Currently demoed with hospital support calls.

---



> 📹 **Demo coming soon** — [watch the full demo](#)  


---

## Architecture

![CallAnalyser Architecture](CallAnalyzerArchitecture.png)

---

## Features

- **Parallel AI reviewers** — agent tone, patient tone, and call outcome scored simultaneously
- **Live streaming UI** — real-time progress via Server-Sent Events as each reviewer completes
- **Structured output** — every report is schema-validated before it reaches the frontend
- **Audio upload** — drop an MP3 and Whisper transcribes it before analysis
- **Flag & score** — composite support score with automatic flagging on threshold breaches

---

## Prerequisites


| Requirement                                 | Download                                                                                           |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Python 3.11+                                | [python.org](https://www.python.org/downloads/)                                                    |
| Node.js 18+                                 | [nodejs.org](https://nodejs.org/)                                                                  |
| Anthropic API key                           | [console.anthropic.com](https://console.anthropic.com/)                                            |
| Whisper server *(optional, for MP3 upload)* | [whisper.cpp](https://github.com/ggerganov/whisper.cpp) or any OpenAI-compatible server on `:9000` |


---

## Installation

```bash
# 1. Clone
git clone https://github.com/your-username/CallRecordingAnalyzer.git
cd CallRecordingAnalyzer

# 2. Python virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Backend dependencies
cd backend && pip install -r requirements.txt

# 4. API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > backend/.env

# 5. Frontend dependencies
cd ../frontend && npm install
```

---

## Usage

Open two terminals from the repo root.

```bash
# Terminal 1 — Backend API (http://localhost:8000)
source .venv/bin/activate
cd backend && uvicorn api.main:app --reload

# Terminal 2 — Frontend (http://localhost:5173)
cd frontend && npm run dev
```

Open `http://localhost:5173`, paste or load a transcript, and click **Analyze**.

To run the pipeline directly on all sample transcripts without the UI:

```bash
cd backend && python agent/hub_spoke.py
# Reports written to backend/output/*.json
```

---

## Contributing

1. Fork the repo and create a feature branch.
2. Keep each reviewer tool focused on a single scoring concern.
3. Run `python agent/verify_outputs.py` before opening a PR to confirm outputs validate against the schema.

---

