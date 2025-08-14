from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Any, Dict
from datetime import datetime

# === Types réutilisables ===
RiskLevel = Literal["low", "medium", "high"]
Sex = Literal["male", "female", "other"]

# === Prédiction (API historique) ===

class PredictionInput(BaseModel):
    # Legacy MVP example features; kept for backward compatibility with existing tests
    amount: float = Field(..., ge=0, description="Transaction or metric amount")
    category: str = Field(..., min_length=1, description="Domain category")
    features: Dict[str, Any] | None = Field(default=None, description="Extra features")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "amount": 500.0,
            "category": "general",
            "features": {"k": "v"}
        }
    })


class TriageInput(BaseModel):
    """Clinical triage input for SekouAI.

    Fields:
    - name: optional patient name for UI/history.
    - age: patient age in years (0-120).
    - sex: patient sex as male/female/other.
    - fever, cough, shortness_of_breath: symptom presence flags.
    - antecedents: optional comma-separated antecedents.
    """
    name: str | None = Field(default=None, description="Patient full name (optional)")
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    sex: Sex = Field(..., description="Patient sex")
    fever: bool = Field(..., description="Fever present")
    cough: bool = Field(..., description="Cough present")
    shortness_of_breath: bool = Field(..., description="Shortness of breath present")
    antecedents: str | None = Field(default=None, description="Antecedents/comorbidities")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Jane Doe",
            "age": 72,
            "sex": "female",
            "fever": True,
            "cough": True,
            "shortness_of_breath": False,
            "antecedents": "diabetes, hypertension"
        }
    })


class PredictionResponse(BaseModel):
    risk_level: RiskLevel
    id: int
    created_at: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "risk_level": "medium",
            "id": 1,
            "created_at": "2025-08-14T00:00:00Z"
        }
    })


class PredictionRecord(BaseModel):
    id: int
    risk_level: RiskLevel
    created_at: str
    input_data: Dict[str, Any] | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1,
            "risk_level": "low",
            "created_at": "2025-08-14T00:00:00Z",
            "input_data": {"age": 45, "sex": "male", "fever": False, "cough": False, "shortness_of_breath": False}
        }
    })

# === Entraînement du modèle ===

class TrainRecord(BaseModel):
    amount: float
    category: str
    features: Dict[str, Any] | None = None
    label: RiskLevel


class TrainRequest(BaseModel):
    records: list[TrainRecord]
    scoring: str | None = Field(default="f1_macro")
    cv_folds: int | None = Field(default=3, ge=2)


class TrainResponse(BaseModel):
    best_model_name: str
    best_score: float
    best_params: Dict[str, Any]
    model_id: int
    
    # Allow field names starting with 'model_' to avoid protected namespace warning in Pydantic v2
    model_config = ConfigDict(protected_namespaces=())

# === Patient (nouvelle entité) ===

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0, le=120)
    sex: Sex = Field(..., description="Patient sex (male/female/other)")


class PatientOut(PatientCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UpdatePatientRequest(BaseModel):
    name: str | None = None
    age: int | None = None
    sex: Sex | None = None
    fever: bool | None = None
    cough: bool | None = None
    shortness_of_breath: bool | None = None
    antecedents: str | None = None

class DeleteResponse(BaseModel):
    success: bool
    message: str
