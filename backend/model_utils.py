from typing import Dict, Any

from .schemas import RiskLevel, PredictionInput, TriageInput


def simple_risk_model(payload: PredictionInput) -> RiskLevel:
    """
    Minimal, deterministic rule-based model (legacy):
    - amount >= 10000 -> "high"
    - amount >= 1000  -> "medium"
    - else -> "low"
    """
    amount = payload.amount
    if amount >= 10000:
        return "high"
    if amount >= 1000:
        return "medium"
    return "low"


def triage_risk_model(payload: TriageInput) -> RiskLevel:
    """Simple clinical triage rules for MVP:
    - If shortness_of_breath: high
    - Else if age >= 75 and fever: high
    - Else if age >= 65 or (fever and cough): medium
    - Else: low
    Deterministic and easily auditable.
    """
    if payload.shortness_of_breath:
        return "high"
    if payload.age >= 75 and payload.fever:
        return "high"
    if payload.age >= 65 or (payload.fever and payload.cough):
        return "medium"
    return "low"


# === ML training & selection utilities (RF/XGBoost/LightGBM) ===
import io

# Heavy ML deps are imported lazily inside functions to keep base API usable
# even when optional packages (joblib, pandas, numpy, sklearn, xgboost, lightgbm)
# are not installed.
XGBClassifier = None  # type: ignore
LGBMClassifier = None  # type: ignore


def _records_to_dataframe(records: list[dict]) -> tuple[Any, Any]:
    import pandas as pd  # local import to avoid hard dependency at import time
    import numpy as np

    df = pd.DataFrame(records)
    y = df.pop("label").values
    if "features" in df.columns:
        feat_series = df.pop("features").fillna({})
        feat_df = pd.json_normalize(feat_series)
        df = pd.concat([df, feat_df], axis=1)
    return df, y


def _build_preprocessor(df: Any) -> Any:
    import pandas as pd  # type: ignore
    from sklearn.compose import ColumnTransformer  # type: ignore
    from sklearn.preprocessing import OneHotEncoder, StandardScaler  # type: ignore

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ]
    )
    return pre


def _grid_rf() -> tuple[Any, dict]:
    from sklearn.ensemble import RandomForestClassifier  # type: ignore

    clf = RandomForestClassifier(random_state=42)
    params = {
        "clf__n_estimators": [100, 300],
        "clf__max_depth": [None, 10, 20],
    }
    return clf, params


def _grid_xgb():
    try:
        from xgboost import XGBClassifier  # type: ignore
    except Exception:
        return None, {}
    clf = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        tree_method="hist",
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    params = {
        "clf__n_estimators": [200, 400],
        "clf__max_depth": [3, 6],
        "clf__learning_rate": [0.05, 0.1],
    }
    return clf, params


def _grid_lgbm():
    try:
        from lightgbm import LGBMClassifier  # type: ignore
    except Exception:
        return None, {}
    clf = LGBMClassifier(objective="multiclass", num_class=3, random_state=42)
    params = {
        "clf__n_estimators": [200, 400],
        "clf__max_depth": [-1, 10, 20],
        "clf__learning_rate": [0.05, 0.1],
    }
    return clf, params


def train_select_serialize(records: list[dict], scoring: str = "f1_macro", cv_folds: int = 3) -> tuple[str, float, dict, bytes]:
    import numpy as np  # type: ignore
    from sklearn.pipeline import Pipeline  # type: ignore
    from sklearn.model_selection import GridSearchCV  # type: ignore
    from sklearn.compose import ColumnTransformer  # just for type context, but not strictly required  # type: ignore
    import joblib  # type: ignore

    X_df, y = _records_to_dataframe(records)
    pre = _build_preprocessor(X_df)

    grids: list[tuple[str, Any]] = []

    rf, rf_params = _grid_rf()
    from sklearn.pipeline import Pipeline as SkPipeline  # type: ignore

    rf_pipe = SkPipeline(steps=[("pre", pre), ("clf", rf)])
    from sklearn.model_selection import GridSearchCV as SkGridSearchCV  # type: ignore

    rf_gs = SkGridSearchCV(rf_pipe, rf_params, cv=cv_folds, scoring=scoring, n_jobs=-1)
    grids.append(("RandomForest", rf_gs))

    xgb, xgb_params = _grid_xgb()
    if xgb is not None:
        xgb_pipe = SkPipeline(steps=[("pre", pre), ("clf", xgb)])
        xgb_gs = SkGridSearchCV(xgb_pipe, xgb_params, cv=cv_folds, scoring=scoring, n_jobs=-1)
        grids.append(("XGBoost", xgb_gs))

    lgbm, lgbm_params = _grid_lgbm()
    if lgbm is not None:
        lgbm_pipe = SkPipeline(steps=[("pre", pre), ("clf", lgbm)])
        lgbm_gs = SkGridSearchCV(lgbm_pipe, lgbm_params, cv=cv_folds, scoring=scoring, n_jobs=-1)
        grids.append(("LightGBM", lgbm_gs))

    best_name = ""
    best_score = -np.inf
    best_params: dict = {}
    best_estimator: Any | None = None

    for name, gs in grids:
        gs.fit(X_df, y)
        if gs.best_score_ > best_score:
            best_name = name
            best_score = float(gs.best_score_)
            best_params = dict(gs.best_params_)
            best_estimator = gs.best_estimator_

    if best_estimator is None:
        raise RuntimeError("No estimator was trained successfully")

    buffer = io.BytesIO()
    joblib.dump(best_estimator, buffer)
    artifact_bytes = buffer.getvalue()

    return best_name, best_score, best_params, artifact_bytes


def load_model_from_bytes(artifact: bytes):
    import joblib  # type: ignore

    return joblib.load(io.BytesIO(artifact))

