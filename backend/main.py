from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from typing import List
import logging
import os

# === App imports ===
from .database import (init_db, get_db, Prediction, ModelArtifact, Patient
, get_patient_by_id, update_patient, delete_patient
                       )
from .schemas import (
    PredictionInput, PredictionResponse, PredictionRecord,
    TriageInput, TrainRequest, TrainResponse,
    PatientCreate, PatientOut, UpdatePatientRequest, DeleteResponse
)
from .model_utils import simple_risk_model, triage_risk_model, train_select_serialize, load_model_from_bytes

# === Paths ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

# === Logging ===
logging.basicConfig(level=os.environ.get("SEKOU_LOG_LEVEL", "INFO"))
logger = logging.getLogger("sekouai")

from contextlib import asynccontextmanager

# === Lifespan handler ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("SekouAI app started")
    yield

# === FastAPI app ===
app = FastAPI(
    title="SekouAI",
    version="1.0.0",
    description="SekouAI: Clinical triage API that classifies patient urgency based on simple inputs. Persists predictions and serves a lightweight frontend.",
    contact={"name": "SekouAI Team", "url": "https://example.com", "email": "support@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
)

# === CORS ===
origins_env = os.environ.get("SEKOU_CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Security headers middleware ===
@app.middleware("http")
async def set_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-XSS-Protection", "0")
    return response

# === Static files ===
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# === Templates ===
templates = Jinja2Templates(directory=os.path.join(FRONTEND_DIR, "templates"))

# === FRONTEND ROUTES ===

@app.get("/", response_class=HTMLResponse, tags=["frontend"])
def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/add", response_class=HTMLResponse, tags=["frontend"])
def serve_add(request: Request):
    return templates.TemplateResponse("add_patient.html", {"request": request})

@app.get("/history", response_class=HTMLResponse, tags=["frontend"])
def serve_history(request: Request, db: Session = Depends(get_db)):
    rows: List[Prediction] = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(200).all()
    predictions = []
    for r in rows:
        data = r.input_data or {}
        predictions.append({
            "id": r.id,
            "name": data.get("name", "N/A"),
            "age": data.get("age", "N/A"),
            "sex": data.get("sex", ""),
            "risk_level": r.risk_level,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return templates.TemplateResponse("history.html", {"request": request, "predictions": predictions})

@app.get("/patients", response_class=HTMLResponse, tags=["frontend"])
def serve_patients(request: Request, db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).limit(100).all()
    return templates.TemplateResponse("patients.html", {"request": request, "patients": patients})


# === API ROUTES ===

@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.post("/predict", response_model=PredictionResponse, tags=["predict"])
def predict(payload: PredictionInput, db: Session = Depends(get_db)):
    active_model = db.query(ModelArtifact).filter(ModelArtifact.active == True).order_by(ModelArtifact.created_at.desc()).first()
    try:
        if active_model:
            model = load_model_from_bytes(active_model.artifact)
            data = payload.model_dump()
            features = data.pop("features", None) or {}
            row = {**data, **features}
            import pandas as pd
            X_df = pd.DataFrame([row])
            pred = model.predict(X_df)[0]
            risk = str(pred)
            if risk not in {"low", "medium", "high"}:
                risk = simple_risk_model(payload)
        else:
            risk = simple_risk_model(payload)
    except Exception:
        risk = simple_risk_model(payload)

    record = Prediction(risk_level=risk, input_data=payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return PredictionResponse(risk_level=risk, id=record.id, created_at=record.created_at.isoformat())


@app.post("/triage", response_model=PredictionResponse, tags=["triage"])
def triage(payload: TriageInput, db: Session = Depends(get_db)):
    risk = triage_risk_model(payload)
    record = Prediction(risk_level=risk, input_data=payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return PredictionResponse(risk_level=risk, id=record.id, created_at=record.created_at.isoformat())


@app.get("/predictions", response_model=List[PredictionRecord], tags=["predict"])
def list_predictions(db: Session = Depends(get_db)):
    rows = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(100).all()
    return [{"id": r.id, "risk_level": r.risk_level, "created_at": r.created_at.isoformat(), "input_data": r.input_data} for r in rows]


@app.post("/train", response_model=TrainResponse, tags=["ml"])
def train(request: TrainRequest, db: Session = Depends(get_db)):
    records = [r.model_dump() for r in request.records]
    best_name, best_score, best_params, artifact = train_select_serialize(records, scoring=request.scoring, cv_folds=request.cv_folds)
    db.query(ModelArtifact).filter(ModelArtifact.active == True).update({"active": False})
    model_row = ModelArtifact(
        name=best_name,
        metrics={"score": best_score, "params": best_params},
        artifact=artifact,
        active=True,
    )
    db.add(model_row)
    db.commit()
    db.refresh(model_row)
    return TrainResponse(best_model_name=best_name, best_score=float(best_score), best_params=best_params, model_id=model_row.id)


@app.get("/models", tags=["ml"])
def list_models(db: Session = Depends(get_db)):
    rows = db.query(ModelArtifact).order_by(ModelArtifact.created_at.desc()).all()
    return [{"id": m.id, "name": m.name, "created_at": m.created_at.isoformat(), "metrics": m.metrics, "active": m.active} for m in rows]


# === PATIENTS API ===

@app.post("/patients", response_model=PatientOut, tags=["patients"])
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/patients/{patient_id}", response_class=HTMLResponse, tags=["patients"])
def get_patient_detail(request: Request, patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    input_data = patient.input_data or {}
    return templates.TemplateResponse("patient_detail.html", {
        "request": request,
        "patient": {
            "id": patient.id,
            "created_at": patient.created_at.strftime("%Y-%m-%d %H:%M"),
            "risk_level": patient.risk_level,
            **input_data
        }
    })

@app.get("/patients/{patient_id}/edit", response_class=HTMLResponse, tags=["patients"])
def edit_patient_form(request: Request, patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse("patient_edit.html", {"request": request, "patient": patient})

@app.post("/patients/{patient_id}/edit", tags=["patients"])
def update_patient_data(patient_id: int, update: UpdatePatientRequest, db: Session = Depends(get_db)):
    updated = update_patient(db, patient_id, update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"success": True, "message": "Patient updated successfully", "id": updated.id}

@app.post("/patients/{patient_id}/delete", response_model=DeleteResponse, tags=["patients"])
def delete_patient_data(patient_id: int, db: Session = Depends(get_db)):
    success = delete_patient(db, patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    return DeleteResponse(success=True, message="Patient deleted successfully")

@app.get("/patients/{patient_id}/delete", response_class=HTMLResponse, tags=["patients"])
def confirm_delete_patient(request: Request, patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse("patient_delete.html", {
        "request": request,
        "patient": patient
    })

@app.get("/patients/api", response_model=List[PatientOut], tags=["patients"])
def list_patients(db: Session = Depends(get_db)):
    return db.query(Patient).order_by(Patient.created_at.desc()).limit(100).all()
