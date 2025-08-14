# sekou-ai

Production-ready MVP of SekouAI — a healthcare AI for intelligent medical triage.

- Backend: FastAPI (Python) with SQLite (app.db) via SQLAlchemy
- Frontend: Responsive HTML/CSS/JS designed for clinical environments
- Risk levels: "low", "medium", "high"
- All predictions are persisted with inputs and timestamp for traceability

## Run locally
1) Create/activate a Python 3.12+ environment
2) Install deps:
   - pip install -r requirements.txt
3) Start API:
   - uvicorn backend.main:app --host 0.0.0.0 --port 8000
4) Open the app:
   - Visit http://localhost:8000/ (served by FastAPI templates)
   - Optional routes: http://localhost:8000/add, http://localhost:8000/history, http://localhost:8000/patients

### Frontend features
- Dashboard with lateral sidebar navigation (Dashboard, Add Patient, History).
- Risk analysis dashboard: total counts and low/medium/high distribution with a simple bar chart.
- Multiple patient forms: Adult triage, Pediatric template quick actions, and optional custom vitals.
- Predict buttons open a dedicated risk overlay with status and metadata.
- Medical templates to pre-fill triage form: Adult Respiratory Distress, Adult Mild Symptoms, Pediatric Fever & Cough.
- Accessible form with labels, fieldset/legend, aria-live results.
- Recent predictions table with risk badges and timestamps.
- Separated JavaScript modules: static/js/{api,utils,dashboard,forms,app}.js.
- Patients list and patient detail/edit/delete views (backed by persisted prediction records).
- Legacy predict demo kept for backward compatibility/testing.

## API endpoints
- GET http://localhost:8000/health
- POST http://localhost:8000/triage
  Body example:
  {
    "age": 72,
    "sex": "female",
    "fever": true,
    "cough": true,
    "shortness_of_breath": false
  }
  Response example:
  {
    "risk_level": "high",
    "id": 42,
    "created_at": "2025-08-14T00:00:00Z"
  }
- POST http://localhost:8000/predict (legacy — kept for tests/backward compatibility)
- GET  http://localhost:8000/predictions
- POST http://localhost:8000/train (provide records to train and activate best model)
- GET  http://localhost:8000/models (list trained models, active flag, and metrics)

OpenAPI docs are available at http://localhost:8000/docs and http://localhost:8000/redoc.

## Docker
- Build: docker build -t sekouai:latest .
- Run (Windows PowerShell):
  docker run --rm -p 8000:8000 -e SEKOU_SQLITE_PATH=/app/app.db -v ${PWD}\app.db:/app/app.db sekouai:latest

## Configuration
- SEKOU_SQLITE_PATH: path to SQLite file (default: app.db)
- SEKOU_CORS_ORIGINS: comma-separated list of allowed origins (default: *)
- SEKOU_LOG_LEVEL: logging level (e.g., INFO, DEBUG)

## Security & privacy
- CORS defaults to * for development; configure SEKOU_CORS_ORIGINS for production (e.g., https://yourclinic.example).
- Basic HTTP security headers are set (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, X-XSS-Protection).
- No PHI/PII should be sent; this is an MVP with a simple rule-based model, not a certified medical device.
- Use a managed, encrypted database and audit logging for real deployments.

## Documentation
Architecture and design documents are in the `docs/` folder:
- Use case diagram: docs/use_case_diagram.png
- Sequence diagram: docs/sequence_diagram.png
- Class diagram: docs/class_diagram.png
- Deployment diagram: docs/deployment_diagram.png
- Architecture_UML_SekouAI.docx
- Technologies_MVP_SekouAI.docx

## Tests
- Run: pytest
- Tests cover health check, legacy prediction, and listing predictions.

## Project layout
- backend/
  - main.py (FastAPI app)
  - model_utils.py (triage + legacy rule-based models)
  - database.py (SQLAlchemy models and session)
  - schemas.py (Pydantic models)
- frontend/
  - index.html (UI), static/style.css (styles)
- requirements.txt
- Dockerfile
