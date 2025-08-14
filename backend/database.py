from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    LargeBinary,
    Boolean,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, UTC
import os

# === Configuration de la base de données SQLite ===
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.getenv("SEKOU_SQLITE_PATH", os.path.join(DATA_DIR, "app.db"))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# === Modèles de données ===

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    risk_level = Column(String, index=True, nullable=False)
    input_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelArtifact(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., RandomForest, XGBoost, LightGBM
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    metrics = Column(JSON, nullable=False)  # CV metrics, best params
    artifact = Column(LargeBinary, nullable=False)  # joblib bytes
    active = Column(Boolean, default=True, nullable=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def get_patient_by_id(db, patient_id: int) -> Prediction | None:
    return db.query(Prediction).filter(Prediction.id == patient_id).first()

def update_patient(db, patient_id: int, updates: dict) -> Prediction | None:
    patient = get_patient_by_id(db, patient_id)
    if patient:
        patient.input_data.update(updates)
        db.commit()
        db.refresh(patient)
    return patient

def delete_patient(db, patient_id: int) -> bool:
    patient = get_patient_by_id(db, patient_id)
    if patient:
        db.delete(patient)
        db.commit()
        return True
    return False

# === Initialisation et session DB ===

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
