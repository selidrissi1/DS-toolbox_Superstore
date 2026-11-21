"""
Step 3 - Machine learning indicator: loss risk.

A decision tree predicts whether an order line will lose money (Profit < 0).
Its predicted probability becomes the "loss_risk" indicator, and its split points
show the discount level where losses start, which checks our answer to Q2.

Run:  python ml_model.py
"""

import json
import os

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

CLEAN_PATH = "data/clean/superstore_clean.csv"
REPORTS_DIR = "reports"

# Inputs known at the time of the sale. Never profit or margin: they contain the answer.
NUMERIC_FEATURES = ["discount", "quantity", "order_month"]
CATEGORICAL_FEATURES = ["sub_category", "region", "segment", "ship_mode"]

TEST_SIZE = 0.30          # 70% train / 30% test, as in the course slides
MAX_DEPTH = 4             # a shallow tree keeps the rules readable
MIN_SAMPLES_LEAF = 20     # each rule must cover at least 20 lines
RANDOM_STATE = 42         # same split every run, so results are reproducible
BASELINE_THRESHOLD = 0.20  # baseline rule: "discount above 20% means a loss"


def make_features(df):
    """One-hot encode the categories (scikit-learn needs numbers)."""
    X = pd.get_dummies(df[NUMERIC_FEATURES + CATEGORICAL_FEATURES], columns=CATEGORICAL_FEATURES, dtype=int)
    y = (df["profit"] < 0).astype(int)
    return X, y


def scores(y_true, y_pred):
    """Precision, recall and F1 on the loss class. Accuracy alone flatters the model,
    because only about 1 line in 5 loses money."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
    }


def train_and_evaluate(df):
    X, y = make_features(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )

    model = DecisionTreeClassifier(
        max_depth=MAX_DEPTH, min_samples_leaf=MIN_SAMPLES_LEAF, random_state=RANDOM_STATE
    )
    model.fit(X_train, y_train)

    tree_pred = model.predict(X_test)
    baseline_pred = (X_test["discount"] > BASELINE_THRESHOLD).astype(int)

    evaluation = {
        "train_lines": len(X_train),
        "test_lines": len(X_test),
        "loss_share_test": float(y_test.mean()),
        "tree": scores(y_test, tree_pred),
        "baseline_rule": scores(y_test, baseline_pred),
        "tree_confusion_matrix": confusion_matrix(y_test, tree_pred).tolist(),
        "baseline_confusion_matrix": confusion_matrix(y_test, baseline_pred).tolist(),
    }
    importance = (
        pd.Series(model.feature_importances_, index=X.columns)
        .sort_values(ascending=False)
        .rename("importance")
    )
    rules = export_text(model, feature_names=list(X.columns), show_weights=True)
    return model, evaluation, importance, rules


def add_loss_risk(df, model):
    """The ML indicator: probability that each line loses money."""
    X, _ = make_features(df)
    df = df.copy()
    df["loss_risk"] = model.predict_proba(X)[:, 1]
    return df


def loss_risk_by_band(scored_df):
    """Average predicted loss risk per sub-category and discount band (for the dashboard)."""
    table = scored_df.groupby(["sub_category", "discount_band"]).agg(
        lines=("loss_risk", "size"), avg_loss_risk=("loss_risk", "mean")
    )
    return table.reset_index()


def run(df):
    """Train, evaluate and score. Returns everything the dashboard needs."""
    model, evaluation, importance, rules = train_and_evaluate(df)
    scored = add_loss_risk(df, model)
    return {
        "model": model,
        "evaluation": evaluation,
        "importance": importance,
        "rules": rules,
        "scored": scored,
        "risk_by_band": loss_risk_by_band(scored),
    }


if __name__ == "__main__":
    df = pd.read_csv(CLEAN_PATH)
    result = run(df)
    evaluation = result["evaluation"]

    print("=== Test set results (loss class) ===")
    for name in ["tree", "baseline_rule"]:
        s = evaluation[name]
        print(f"{name:14s} precision {s['precision']:.3f}  recall {s['recall']:.3f}  "
              f"F1 {s['f1']:.3f}  accuracy {s['accuracy']:.3f}")
    print("\nTree confusion matrix [[no loss correct, false alarm], [missed loss, loss caught]]:")
    print(evaluation["tree_confusion_matrix"])

    print("\n=== Most important inputs ===")
    print(result["importance"].head(8).round(3))

    print("\n=== Tree rules ===")
    print(result["rules"])

    os.makedirs(f"{REPORTS_DIR}/metrics", exist_ok=True)
    with open(f"{REPORTS_DIR}/ml_evaluation.json", "w") as f:
        json.dump(evaluation, f, indent=2)
    with open(f"{REPORTS_DIR}/tree_rules.txt", "w") as f:
        f.write(result["rules"])
    result["importance"].to_csv(f"{REPORTS_DIR}/metrics/ml_feature_importance.csv")
    result["risk_by_band"].to_csv(f"{REPORTS_DIR}/metrics/ml_loss_risk_by_band.csv", index=False)
    print(f"Saved evaluation, rules and loss-risk table to {REPORTS_DIR}/")
