"""Entity Resolution LightGBM classifier trainer."""
import sys
import json
import pickle
import random
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

try:
    import lightgbm as lgb
except ImportError:
    print("lightgbm not installed — pip install lightgbm")
    sys.exit(1)

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

from app.pipeline.entity_resolution import compute_features, FEATURE_NAMES

MODEL_PATH = Path(__file__).parent / "er_model.pkl"
METRICS_PATH = Path(__file__).parent / "er_metrics.json"
GROUND_TRUTH_PATH = Path(__file__).parent.parent / "data" / "raw" / "duplicate_ground_truth.csv"


def load_source_records(db_url: str) -> pd.DataFrame:
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    df = pd.read_sql("SELECT * FROM source_records WHERE quarantined = false LIMIT 10000", engine)
    print(f"Loaded {len(df)} source records from DB")
    return df


def load_ground_truth(path: str = str(GROUND_TRUTH_PATH)) -> pd.DataFrame:
    if not Path(path).exists():
        print(f"Ground truth not found at {path} — generating minimal synthetic truth")
        return pd.DataFrame(columns=["base_customer_id", "source_record_id_a", "source_record_id_b"])
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} ground truth pairs")
    return df


def build_training_pairs(records_df: pd.DataFrame, ground_truth_df: pd.DataFrame) -> tuple:
    record_map = {str(r["external_id"]): r.to_dict() for _, r in records_df.iterrows()}
    id_list = records_df["external_id"].tolist()

    X_rows, y_rows = [], []

    # Positive pairs
    for _, row in ground_truth_df.iterrows():
        a = record_map.get(str(row.get("source_record_id_a", "")))
        b = record_map.get(str(row.get("source_record_id_b", "")))
        if a and b:
            features = compute_features(a, b)
            X_rows.append([features.get(f, 0.0) for f in FEATURE_NAMES])
            y_rows.append(1)

    n_positive = len(y_rows)
    n_negative = n_positive * 3

    # Negative pairs
    attempts = 0
    neg = 0
    while neg < n_negative and attempts < n_negative * 10:
        attempts += 1
        a_id = random.choice(id_list)
        b_id = random.choice(id_list)
        if a_id == b_id:
            continue
        a = record_map.get(str(a_id))
        b = record_map.get(str(b_id))
        if not a or not b:
            continue
        if a.get("customer_id") == b.get("customer_id"):
            continue
        features = compute_features(a, b)
        X_rows.append([features.get(f, 0.0) for f in FEATURE_NAMES])
        y_rows.append(0)
        neg += 1

    X = pd.DataFrame(X_rows, columns=FEATURE_NAMES)
    y = pd.Series(y_rows)
    print(f"Built training set: {n_positive} positive, {neg} negative pairs")
    return X, y


def train(X: pd.DataFrame, y: pd.Series) -> tuple:
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = lgb.LGBMClassifier(
        objective="binary",
        metric="binary_logloss",
        num_leaves=31,
        learning_rate=0.05,
        n_estimators=200,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_val)[:, 1]

    # Find optimal threshold
    best_f1, best_threshold = 0.0, 0.5
    for t in [i / 100 for i in range(30, 91, 5)]:
        y_pred = (y_prob >= t).astype(int)
        f = f1_score(y_val, y_pred, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_threshold = t

    y_pred_best = (y_prob >= best_threshold).astype(int)
    prec = precision_score(y_val, y_pred_best, zero_division=0)
    rec = recall_score(y_val, y_pred_best, zero_division=0)
    auc = roc_auc_score(y_val, y_prob) if len(set(y_val)) > 1 else 0.0

    feature_importance = {}
    if HAS_SHAP:
        try:
            explainer = shap.TreeExplainer(model)
            shap_vals = explainer.shap_values(X_val)
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1]
            feature_importance = dict(zip(FEATURE_NAMES, np.abs(shap_vals).mean(axis=0).tolist()))
        except Exception:
            feature_importance = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist()))
    else:
        feature_importance = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist()))

    metrics = {
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(best_f1), 4),
        "auc_roc": round(float(auc), 4),
        "optimal_threshold": best_threshold,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "feature_importance": {k: round(float(v), 6) for k, v in feature_importance.items()},
        "trained_at": datetime.utcnow().isoformat(),
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "threshold": best_threshold, "features": FEATURE_NAMES}, f)

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ Model saved to {MODEL_PATH}")
    return model, best_threshold, metrics


def print_evaluation_report(metrics: dict):
    top_features = sorted(
        metrics.get("feature_importance", {}).items(), key=lambda x: x[1], reverse=True
    )[:10]

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║         Entity Resolution Model Report               ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Precision: {metrics['precision']:.3f}    Recall:  {metrics['recall']:.3f}          ║")
    print(f"║  F1 Score:  {metrics['f1']:.3f}    AUC-ROC: {metrics['auc_roc']:.3f}          ║")
    print(f"║  Threshold: {metrics['optimal_threshold']:.2f}                                  ║")
    print(f"║  Train: {metrics['n_train']}     Val: {metrics['n_val']}                      ║")
    print("╠══════════════════════════════════════════════════════╣")
    print("║  Top Features (SHAP / Importance):                   ║")
    for i, (fname, score) in enumerate(top_features, 1):
        print(f"║  {i:2d}. {fname:<35} {score:.4f}  ║")
    print("╚══════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    from app.config import settings

    print("Training Entity Resolution model...")
    try:
        records = load_source_records(settings.sync_database_url)
    except Exception as e:
        print(f"Could not load from DB: {e}")
        print("Generating minimal synthetic training data...")
        records = pd.DataFrame([
            {"external_id": f"CRM-{i:06d}", "source_system": "CRM",
             "first_name": f"John{i}", "last_name": "Smith", "email": f"john{i}@test.com",
             "phone": f"+1555{i:07d}", "date_of_birth": "1985-03-15",
             "address_line1": "123 Main St", "city": "New York", "country": "US",
             "customer_id": f"cust-{i:06d}"}
            for i in range(200)
        ])

    truth = load_ground_truth()
    if len(truth) == 0:
        print("No ground truth — generating synthetic pairs for demo...")
        records_list = records.to_dict("records")
        synthetic = []
        for i in range(min(100, len(records_list))):
            r = records_list[i]
            r2 = dict(r)
            r2["external_id"] = r2["external_id"] + "-DUP"
            r2["first_name"] = str(r2.get("first_name", "")).upper()
            synthetic.append({
                "base_customer_id": r.get("customer_id"),
                "source_record_id_a": r["external_id"],
                "source_record_id_b": r2["external_id"],
            })
            records = pd.concat([records, pd.DataFrame([r2])], ignore_index=True)
        truth = pd.DataFrame(synthetic)

    random.seed(42)
    np.random.seed(42)
    X, y = build_training_pairs(records, truth)

    if len(X) < 10:
        print("Too few training pairs — skipping model training")
        sys.exit(0)

    model, threshold, metrics = train(X, y)
    print_evaluation_report(metrics)
    print(f"   Use threshold {threshold:.2f} for production decisions")
