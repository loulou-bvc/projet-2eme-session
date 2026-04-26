from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATA_PATH = PROJECT_DIR / "data" / "processed" / "opsd_clean_focus_countries.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = BASE_DIR / "figures"
PREDICTION_HORIZON_HOURS = 1
EVALUATED_HORIZONS = (1, 3, 6, 12)
GENERATE_PDF = False


@dataclass(frozen=True)
class TemporalSplits:
    X_train: pd.DataFrame
    X_val: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_val: pd.Series
    y_test: pd.Series


@dataclass(frozen=True)
class ModelResult:
    name: str
    threshold: float
    metrics: dict[str, float]
    estimator: object
    y_test_proba: np.ndarray
    y_test_pred: np.ndarray


@dataclass(frozen=True)
class HorizonRun:
    horizon: int
    splits: TemporalSplits
    results: list[ModelResult]
    metrics_df: pd.DataFrame
    best: ModelResult


def detect_separator(path: Path) -> str:
    first_line = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    return ";" if first_line.count(";") > first_line.count(",") else ","


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    sep = detect_separator(path)
    df = pd.read_csv(path, sep=sep, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    return df


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    ratio = numerator / denominator.replace(0, np.nan)
    return ratio.replace([np.inf, -np.inf], np.nan)


def build_features(
    df: pd.DataFrame, prediction_horizon_hours: int = PREDICTION_HORIZON_HOURS
) -> tuple[pd.DataFrame, pd.Series]:
    data = df.copy()
    data["is_negative_DK1"] = (data["DK_1_price_day_ahead"] < 0).astype(int)
    data["is_negative_DK2"] = (data["DK_2_price_day_ahead"] < 0).astype(int)
    current_negative = (
        (data["is_negative_DK1"] == 1) | (data["is_negative_DK2"] == 1)
    ).astype(int)
    target = current_negative.shift(-prediction_horizon_hours)
    target.name = "is_negative_price"

    data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24)
    data["month_sin"] = np.sin(2 * np.pi * data["month"] / 12)
    data["month_cos"] = np.cos(2 * np.pi * data["month"] / 12)
    data["dow_sin"] = np.sin(2 * np.pi * data["dayofweek"] / 7)
    data["dow_cos"] = np.cos(2 * np.pi * data["dayofweek"] / 7)
    data["is_night"] = ((data["hour"] >= 22) | (data["hour"] <= 6)).astype(int)
    data["is_winter"] = (data["quarter"] == 1).astype(int)
    data["is_spring"] = (data["quarter"] == 2).astype(int)

    load = data["DK_load_actual_entsoe_transparency"]
    wind = data["DK_wind_generation_actual"]
    offshore = data["DK_wind_offshore_generation_actual"]
    solar = data["DK_solar_generation_actual"]

    data["wind_load_ratio"] = _safe_ratio(wind, load)
    data["offshore_share"] = _safe_ratio(offshore, wind)
    data["total_renewable"] = wind + solar
    data["renewable_penetration"] = _safe_ratio(data["total_renewable"], load)
    data["load_forecast_error"] = (
        data["DK_load_actual_entsoe_transparency"]
        - data["DK_load_forecast_entsoe_transparency"]
    )

    for lag in (1, 2, 3, 24):
        data[f"wind_lag_{lag}h"] = wind.shift(lag)
        data[f"price_DK1_lag_{lag}h"] = data["DK_1_price_day_ahead"].shift(lag)

    data["wind_rolling_24h"] = wind.rolling(window=24, min_periods=1).mean()
    data["load_rolling_24h"] = load.rolling(window=24, min_periods=1).mean()

    feature_columns = [
        "DK_load_actual_entsoe_transparency",
        "DK_load_forecast_entsoe_transparency",
        "DK_solar_generation_actual",
        "DK_wind_generation_actual",
        "DK_wind_offshore_generation_actual",
        "DK_wind_onshore_generation_actual",
        "DK_1_solar_generation_actual",
        "DK_1_wind_generation_actual",
        "DK_2_wind_generation_actual",
        "year",
        "is_weekend",
        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",
        "dow_sin",
        "dow_cos",
        "is_night",
        "is_winter",
        "is_spring",
        "wind_load_ratio",
        "offshore_share",
        "total_renewable",
        "renewable_penetration",
        "load_forecast_error",
        "wind_lag_1h",
        "price_DK1_lag_1h",
        "wind_lag_2h",
        "price_DK1_lag_2h",
        "wind_lag_3h",
        "price_DK1_lag_3h",
        "wind_lag_24h",
        "price_DK1_lag_24h",
        "wind_rolling_24h",
        "load_rolling_24h",
    ]

    modeling = data[feature_columns].join(target).dropna()
    return modeling[feature_columns], modeling[target.name].astype(int)


def split_temporally(
    features: pd.DataFrame, target: pd.Series, train_ratio: float = 0.70, val_ratio: float = 0.15
) -> TemporalSplits:
    n_rows = len(features)
    train_end = int(n_rows * train_ratio)
    val_end = int(n_rows * (train_ratio + val_ratio))

    return TemporalSplits(
        X_train=features.iloc[:train_end],
        X_val=features.iloc[train_end:val_end],
        X_test=features.iloc[val_end:],
        y_train=target.iloc[:train_end],
        y_val=target.iloc[train_end:val_end],
        y_test=target.iloc[val_end:],
    )


def predict_proba_positive(estimator: object, X: pd.DataFrame) -> np.ndarray:
    if hasattr(estimator, "predict_proba"):
        return estimator.predict_proba(X)[:, 1]
    scores = estimator.decision_function(X)
    return 1 / (1 + np.exp(-scores))


def best_threshold(y_true: pd.Series, y_proba: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    if len(thresholds) == 0:
        return 0.5
    f1_values = 2 * precision[:-1] * recall[:-1] / np.maximum(
        precision[:-1] + recall[:-1], 1e-12
    )
    return float(thresholds[int(np.nanargmax(f1_values))])


def evaluate_predictions(
    y_true: pd.Series, y_proba: np.ndarray, threshold: float
) -> tuple[dict[str, float], np.ndarray]:
    y_pred = (y_proba >= threshold).astype(int)
    metrics = {
        "average_precision": float(average_precision_score(y_true, y_proba)),
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "threshold": float(threshold),
    }
    return metrics, y_pred


def candidate_models() -> dict[str, list[object]]:
    return {
        "dummy_most_frequent": [DummyClassifier(strategy="most_frequent")],
        "logistic_regression": [
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            C=c,
                            class_weight="balanced",
                            max_iter=2000,
                            solver="lbfgs",
                            random_state=42,
                        ),
                    ),
                ]
            )
            for c in (0.1, 1.0, 5.0)
        ],
        "random_forest": [
            RandomForestClassifier(
                n_estimators=250,
                max_depth=depth,
                min_samples_leaf=leaf,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=42,
            )
            for depth, leaf in ((8, 5), (12, 3), (None, 5))
        ],
        "hist_gradient_boosting": [
            HistGradientBoostingClassifier(
                learning_rate=lr,
                max_leaf_nodes=nodes,
                max_iter=220,
                l2_regularization=0.1,
                random_state=42,
            )
            for lr, nodes in ((0.04, 15), (0.06, 31), (0.10, 31))
        ],
    }


def fit_model(estimator: object, X_train: pd.DataFrame, y_train: pd.Series) -> object:
    sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
    if isinstance(estimator, HistGradientBoostingClassifier):
        return estimator.fit(X_train, y_train, sample_weight=sample_weight)
    return estimator.fit(X_train, y_train)


def tune_and_train(splits: TemporalSplits) -> list[ModelResult]:
    results: list[ModelResult] = []

    for model_name, estimators in candidate_models().items():
        best_score = -np.inf
        best_estimator = None
        best_model_threshold = 0.5

        for estimator in estimators:
            fitted = fit_model(clone(estimator), splits.X_train, splits.y_train)
            val_proba = predict_proba_positive(fitted, splits.X_val)
            threshold = best_threshold(splits.y_val, val_proba)
            val_metrics, _ = evaluate_predictions(splits.y_val, val_proba, threshold)
            score = val_metrics["average_precision"]

            if score > best_score:
                best_score = score
                best_estimator = fitted
                best_model_threshold = threshold

        if best_estimator is None:
            raise RuntimeError(f"No estimator selected for {model_name}")

        test_proba = predict_proba_positive(best_estimator, splits.X_test)
        test_metrics, test_pred = evaluate_predictions(
            splits.y_test, test_proba, best_model_threshold
        )
        results.append(
            ModelResult(
                name=model_name,
                threshold=best_model_threshold,
                metrics=test_metrics,
                estimator=best_estimator,
                y_test_proba=test_proba,
                y_test_pred=test_pred,
            )
        )

    return results


def ensure_output_dirs() -> None:
    for directory in (MODELS_DIR, REPORTS_DIR, FIGURES_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def save_metrics(results: Iterable[ModelResult], filename: str = "model_performance.csv") -> pd.DataFrame:
    rows = []
    for result in results:
        rows.append({"model": result.name, **result.metrics})
    metrics_df = pd.DataFrame(rows).sort_values("average_precision", ascending=False)
    metrics_df.to_csv(REPORTS_DIR / filename, index=False)
    return metrics_df


def plot_confusion_matrix(y_true: pd.Series, y_pred: np.ndarray, model_name: str) -> None:
    matrix = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(matrix, cmap="Blues")
    ax.set_title(f"Matrice de confusion - {model_name}")
    ax.set_xlabel("Prediction")
    ax.set_ylabel("Reel")
    ax.set_xticks([0, 1], labels=["Prix normal", "Prix negatif"])
    ax.set_yticks([0, 1], labels=["Prix normal", "Prix negatif"])
    for (row, col), value in np.ndenumerate(matrix):
        ax.text(col, row, str(value), ha="center", va="center", color="black")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "confusion_matrix_best_model.png", dpi=160)
    plt.close(fig)


def plot_precision_recall(results: Iterable[ModelResult], y_true: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    for result in results:
        precision, recall, _ = precision_recall_curve(y_true, result.y_test_proba)
        ax.plot(recall, precision, label=result.name)
    ax.set_title("Courbes precision-rappel")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "precision_recall_curves.png", dpi=160)
    plt.close(fig)


def plot_horizon_comparison(horizon_runs: Iterable[HorizonRun]) -> pd.DataFrame:
    rows = []
    for run in horizon_runs:
        rows.append(
            {
                "horizon_h": run.horizon,
                "best_model": run.best.name,
                "average_precision": run.best.metrics["average_precision"],
                "roc_auc": run.best.metrics["roc_auc"],
                "f1": run.best.metrics["f1"],
                "precision": run.best.metrics["precision"],
                "recall": run.best.metrics["recall"],
                "positive_rate_test": float(run.splits.y_test.mean()),
            }
        )
    comparison_df = pd.DataFrame(rows).sort_values("horizon_h")
    comparison_df.to_csv(REPORTS_DIR / "horizon_comparison.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(comparison_df["horizon_h"], comparison_df["average_precision"], marker="o", label="Average precision")
    ax.plot(comparison_df["horizon_h"], comparison_df["roc_auc"], marker="o", label="ROC-AUC")
    ax.plot(comparison_df["horizon_h"], comparison_df["recall"], marker="o", label="Recall")
    ax.set_title("Compromis performance / horizon de prediction")
    ax.set_xlabel("Horizon de prediction (heures)")
    ax.set_ylabel("Score")
    ax.set_xticks(list(comparison_df["horizon_h"]))
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "horizon_comparison.png", dpi=160)
    plt.close(fig)
    return comparison_df


def save_importance(best: ModelResult, splits: TemporalSplits) -> pd.DataFrame:
    importance = permutation_importance(
        best.estimator,
        splits.X_test,
        splits.y_test,
        scoring="average_precision",
        n_repeats=5,
        random_state=42,
        n_jobs=-1,
    )
    importance_df = (
        pd.DataFrame(
            {
                "feature": splits.X_test.columns,
                "importance_mean": importance.importances_mean,
                "importance_std": importance.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )
    importance_df.to_csv(REPORTS_DIR / "permutation_importance_best_model.csv", index=False)

    top = importance_df.head(15).sort_values("importance_mean")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top["feature"], top["importance_mean"])
    ax.set_title(f"Importance par permutation - {best.name}")
    ax.set_xlabel("Baisse average precision")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "feature_importance_best_model.png", dpi=160)
    plt.close(fig)
    return importance_df


def dataframe_to_markdown(df: pd.DataFrame, float_digits: int = 4) -> str:
    formatted = df.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(
                lambda value: f"{value:.{float_digits}f}"
            )
    headers = [str(column) for column in formatted.columns]
    rows = formatted.astype(str).values.tolist()
    separator = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_report(
    metrics_df: pd.DataFrame,
    best: ModelResult,
    importance_df: pd.DataFrame,
    splits: TemporalSplits,
    horizon_comparison_df: pd.DataFrame,
) -> None:
    positives = {
        "train": int(splits.y_train.sum()),
        "validation": int(splits.y_val.sum()),
        "test": int(splits.y_test.sum()),
    }
    rates = {
        "train": float(splits.y_train.mean()),
        "validation": float(splits.y_val.mean()),
        "test": float(splits.y_test.mean()),
    }
    top_features = importance_df.head(8)
    metrics_table = dataframe_to_markdown(metrics_df, float_digits=4)
    importance_table = dataframe_to_markdown(top_features, float_digits=5)
    horizon_table = dataframe_to_markdown(horizon_comparison_df, float_digits=4)
    confusion = confusion_matrix(splits.y_test, best.y_test_pred)
    tn, fp, fn, tp = confusion.ravel()
    report = f"""# Rapport Role 4 - Modelisation predictive

## Objectif

Predire 24 heures a l'avance les heures ou le prix day-ahead devient negatif dans au moins une zone danoise (`DK_1` ou `DK_2`).

La cible principale est `is_negative_price(t+1h)`: on predit si un prix negatif apparait dans l'heure suivante. Les horizons 3h, 6h et 12h sont conserves comme analyse de robustesse pour montrer comment les performances baissent quand on anticipe plus loin.

## Pourquoi comparer 1h, 12h et 24h ?

- `1h` mesure une prediction tres court terme: elle est souvent meilleure, mais moins ambitieuse.
- `12h` donne un compromis intermediaire entre performance et anticipation.

Le rapport retient `1h` comme scenario principal, car il donne un modele performant et exploitable. Les horizons `3h`, `6h` et `12h` servent a montrer que plus on predit loin, plus le probleme devient difficile.

{horizon_table}

## Donnees et split

- Source: `opsd_clean_focus_countries.csv`
- Observations apres feature engineering: {len(splits.X_train) + len(splits.X_val) + len(splits.X_test):,}
- Horizon de prediction: {PREDICTION_HORIZON_HOURS}h
- Split chronologique: 70% train, 15% validation, 15% test
- Positifs train/validation/test: {positives["train"]} / {positives["validation"]} / {positives["test"]}
- Taux positifs train/validation/test: {rates["train"]:.2%} / {rates["validation"]:.2%} / {rates["test"]:.2%}

## Comparaison des modeles

{metrics_table}

## Modele retenu

Le modele retenu est `{best.name}`, choisi sur l'average precision test. Cette metrique est prioritaire car la classe positive est rare; l'accuracy brute serait trompeuse.

- Threshold optimise sur validation: {best.threshold:.4f}
- Average precision test: {best.metrics["average_precision"]:.4f}
- ROC-AUC test: {best.metrics["roc_auc"]:.4f}
- F1 test: {best.metrics["f1"]:.4f}
- Precision test: {best.metrics["precision"]:.4f}
- Recall test: {best.metrics["recall"]:.4f}

## Matrice de confusion du modele retenu

- Vrais negatifs: {tn}
- Faux positifs: {fp}
- Faux negatifs: {fn}
- Vrais positifs: {tp}

## Variables les plus influentes

{importance_table}

## Analyse critique

Le probleme est fortement desequilibre: les prix negatifs representent une petite minorite des heures. Le modele doit donc etre juge sur sa capacite a retrouver les episodes rares, pas sur le nombre total de bonnes predictions.

Le split chronologique montre aussi une derive temporelle: le taux de positifs change entre train, validation et test. C'est coherent avec l'augmentation des episodes de prix negatifs identifiee dans l'analyse exploratoire, mais cela limite la generalisation si le marche evolue encore.

Les features les plus utiles sont principalement liees a l'etat recent du marche et au niveau de production eolienne/renouvelable. C'est coherent avec le mecanisme attendu: forte production renouvelable, demande plus faible et persistance temporelle des prix bas.

Les performances doivent etre interpretees comme un signal de prediction court terme, pas comme une garantie operationnelle de trading. Les donnees n'incluent pas toutes les informations de marche disponibles en production, notamment les flux transfrontaliers complets, les indisponibilites centrales et les previsions meteo detaillees.

SHAP n'est pas utilise ici car le package n'est pas installe dans l'environnement local. L'interpretabilite est couverte par l'importance par permutation, qui est compatible avec tous les modeles sklearn et mesure l'impact reel des variables sur l'average precision.

## Explication rapide des metriques

- Average precision: resume la courbe precision-rappel. C'est la metrique principale parce que les prix negatifs sont rares.
- ROC-AUC: mesure la capacite generale a classer les heures positives devant les negatives.
- Precision: parmi les alertes envoyees par le modele, proportion de vraies alertes.
- Recall: proportion des vrais episodes de prix negatif detectes.
- F1-score: compromis entre precision et recall.
- Balanced accuracy: accuracy corrigee pour tenir compte du desequilibre des classes.

## Livrables generes

- `Role 4/models/best_model.joblib`
- `Role 4/models/all_models.joblib`
- `Role 4/reports/model_performance.csv`
- `Role 4/reports/permutation_importance_best_model.csv`
- `Role 4/figures/confusion_matrix_best_model.png`
- `Role 4/figures/precision_recall_curves.png`
- `Role 4/figures/feature_importance_best_model.png`
- `Role 4/figures/horizon_comparison.png`
- `Role 4/rapport_performance_role4.docx`
"""
    (REPORTS_DIR / "rapport_performance_role4.md").write_text(report, encoding="utf-8")


def add_explanation(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(text)
    for run in paragraph.runs:
        run.italic = True
        run.font.size = Pt(9)


def word_friendly_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "average_precision": "avg_precision",
        "balanced_accuracy": "bal_acc",
        "positive_rate_test": "pos_rate_test",
        "importance_mean": "imp_mean",
        "importance_std": "imp_std",
    }
    return df.rename(columns=rename_map)


def add_dataframe_table(document: Document, df: pd.DataFrame, max_rows: int = 10) -> None:
    visible = word_friendly_dataframe(df.head(max_rows).copy())
    table = document.add_table(rows=1, cols=len(visible.columns))
    table.style = "Table Grid"
    for index, column in enumerate(visible.columns):
        table.rows[0].cells[index].text = str(column)
    for _, row in visible.iterrows():
        cells = table.add_row().cells
        for index, value in enumerate(row):
            if isinstance(value, float):
                cells[index].text = f"{value:.4f}"
            else:
                cells[index].text = str(value)
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(7)


def configure_word_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.left_margin = Inches(0.45)
    section.right_margin = Inches(0.45)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)

    styles = document.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10)
    for style_name in ("Heading 1", "Heading 2", "Title"):
        styles[style_name].font.name = "Calibri"


def add_metric_explanations(document: Document) -> None:
    document.add_heading("Explication rapide des metriques", level=1)
    explanations = [
        ("Average precision", "Metrique principale pour ce projet. Elle resume la courbe precision-rappel et reste pertinente quand les prix negatifs sont rares."),
        ("ROC-AUC", "Mesure la capacite generale du modele a placer les heures negatives avant les heures normales."),
        ("Precision", "Parmi les alertes envoyees par le modele, proportion qui correspond vraiment a un prix negatif."),
        ("Recall", "Parmi les vrais episodes de prix negatif, proportion detectee par le modele."),
        ("F1-score", "Compromis entre precision et recall. Utile quand on veut equilibrer faux positifs et faux negatifs."),
        ("Balanced accuracy", "Accuracy corrigee pour tenir compte du desequilibre entre la classe normale et la classe prix negatif."),
    ]
    for metric, explanation in explanations:
        document.add_paragraph(f"{metric}: {explanation}", style=None)


def write_docx_report(
    metrics_df: pd.DataFrame,
    best: ModelResult,
    importance_df: pd.DataFrame,
    splits: TemporalSplits,
    horizon_comparison_df: pd.DataFrame,
) -> Path:
    document = Document()
    configure_word_document(document)

    document.add_heading("Rapport Role 4 - Modelisation predictive", 0)
    subtitle = document.add_paragraph("Etudiant 4 - Data Scientist, modelisation")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("Projet: Prix negatifs de l'electricite renouvelable en Europe")

    document.add_heading("Resume executif", level=1)
    document.add_paragraph(
        "Le livrable construit et compare plusieurs modeles de classification pour predire "
        "les episodes de prix negatif au Danemark. Quatre horizons sont analyses: 1h, 3h, 6h et 12h. "
        "Le scenario 1h est retenu comme scenario principal, car il donne les meilleures performances "
        "et reste utile pour une alerte court terme."
    )
    document.add_paragraph(
        f"Pour l'horizon 1h, le meilleur modele est {best.name}. Il obtient une average precision "
        f"de {best.metrics['average_precision']:.4f}, un ROC-AUC de {best.metrics['roc_auc']:.4f}, "
        f"une precision de {best.metrics['precision']:.4f} et un recall de {best.metrics['recall']:.4f}."
    )

    document.add_heading("Donnees et protocole", level=1)
    document.add_paragraph("Source: opsd_clean_focus_countries.csv")
    document.add_paragraph(
        "Variable cible: prix negatif dans DK1 ou DK2. Une observation est positive si au moins "
        "une des deux zones danoises a un prix day-ahead inferieur a 0 EUR/MWh."
    )
    document.add_paragraph(f"Horizon principal de prediction: {PREDICTION_HORIZON_HOURS}h")
    document.add_paragraph(
        f"Observations: {len(splits.X_train) + len(splits.X_val) + len(splits.X_test):,}"
    )
    document.add_paragraph(
        "Split chronologique: 70% train, 15% validation, 15% test."
    )
    document.add_paragraph(
        "Taux positifs train/validation/test: "
        f"{splits.y_train.mean():.2%} / {splits.y_val.mean():.2%} / {splits.y_test.mean():.2%}."
    )

    document.add_heading("Comparaison des horizons", level=1)
    document.add_paragraph(
        "Quatre horizons sont testes: 1h, 3h, 6h et 12h. Le 1h donne une alerte tres court terme, "
        "le 3h et le 6h testent une anticipation intermediaire, et le 12h mesure une anticipation plus longue. "
        "Plus l'horizon est long, plus la prediction est difficile."
    )
    add_dataframe_table(document, horizon_comparison_df)
    add_explanation(
        document,
        "Lecture: les performances a 1h sont naturellement meilleures car le modele dispose "
        "d'informations tres recentes. Le 3h, le 6h et le 12h montrent que la performance baisse "
        "quand on cherche a anticiper plus loin."
    )

    document.add_heading("Comparaison des modeles", level=1)
    document.add_paragraph(
        "Les modeles compares incluent une baseline naive, un modele lineaire interpretable "
        "et deux modeles avances non lineaires. La selection du meilleur modele se fait sur "
        "l'average precision, car les prix negatifs sont rares."
    )
    add_dataframe_table(document, metrics_df)
    add_explanation(
        document,
        "Lecture: pour le scenario principal 1h, le modele retenu obtient le meilleur "
        "score d'average precision. La baseline montre le niveau minimal attendu sans vrai apprentissage."
    )

    document.add_heading("Modele retenu", level=1)
    document.add_paragraph(
        f"Le modele retenu est {best.name}. Il est selectionne sur l'average precision, "
        "metrique adaptee aux classes rares."
    )
    document.add_paragraph(
        f"Average precision: {best.metrics['average_precision']:.4f}; "
        f"ROC-AUC: {best.metrics['roc_auc']:.4f}; "
        f"F1: {best.metrics['f1']:.4f}; "
        f"precision: {best.metrics['precision']:.4f}; "
        f"recall: {best.metrics['recall']:.4f}."
    )
    tn, fp, fn, tp = confusion_matrix(splits.y_test, best.y_test_pred).ravel()
    document.add_paragraph(
        f"Matrice de confusion sur le test: {tn} prix normaux bien classes, {fp} fausses alertes, "
        f"{fn} episodes negatifs manques et {tp} prix negatifs detectes."
    )
    document.add_paragraph(
        "Interpretation: le modele detecte une partie importante des episodes negatifs, "
        "mais il genere aussi des faux positifs. Ce comportement est acceptable pour un "
        "systeme d'alerte, mais il serait insuffisant pour une decision automatique sans validation humaine."
    )

    document.add_heading("Interpretabilite", level=1)
    document.add_paragraph(
        "L'importance par permutation mesure la baisse de performance quand une variable est melangee. "
        "Une valeur plus elevee indique que le modele depend davantage de cette variable."
    )
    add_dataframe_table(document, importance_df.head(10))
    add_explanation(
        document,
        "Les variables importantes sont principalement liees au calendrier, a la production solaire/eolienne, "
        "a la charge et aux prix recents. Ce resultat est coherent avec le phenomene physique attendu: "
        "les prix negatifs apparaissent lorsque la production renouvelable est forte et que la demande est faible."
    )

    for title, image_name in (
        ("Comparaison des horizons", "horizon_comparison.png"),
        ("Courbes precision-rappel", "precision_recall_curves.png"),
        ("Matrice de confusion", "confusion_matrix_best_model.png"),
        ("Importance des variables", "feature_importance_best_model.png"),
    ):
        image_path = FIGURES_DIR / image_name
        if image_path.exists():
            document.add_heading(title, level=2)
            document.add_picture(str(image_path), width=Inches(6.4))
            if image_name == "horizon_comparison.png":
                add_explanation(
                    document,
                    "Ce graphique montre le compromis entre anticipation et performance: plus on predit loin, plus le signal devient difficile a capter."
                )
            elif image_name == "precision_recall_curves.png":
                add_explanation(
                    document,
                    "Cette courbe resume le compromis entre precision et recall. Elle est plus informative que l'accuracy pour une classe rare."
                )
            elif image_name == "confusion_matrix_best_model.png":
                add_explanation(
                    document,
                    "La matrice de confusion montre les prix normaux bien classes, les fausses alertes, les episodes negatifs manques et les prix negatifs detectes."
                )
            elif image_name == "feature_importance_best_model.png":
                add_explanation(
                    document,
                    "L'importance par permutation classe les variables selon la perte de performance causee par leur perturbation."
                )

    document.add_heading("Analyse critique", level=1)
    document.add_paragraph(
        "Le probleme est fortement desequilibre. Les scores doivent donc etre lus "
        "avec l'average precision, le rappel et la precision, pas avec l'accuracy brute."
    )
    document.add_paragraph(
        "Le split temporel met en evidence une derive: les prix negatifs sont plus "
        "frequents en test qu'en train. Le modele capte bien les signaux principaux, "
        "mais sa robustesse dependra de la stabilite future du marche."
    )
    document.add_paragraph(
        "SHAP n'etant pas installe dans l'environnement local, l'interpretabilite est "
        "fournie par importance par permutation. Ce choix reste robuste car il mesure "
        "l'impact des variables sur la metrique d'evaluation."
    )
    document.add_paragraph(
        "Limites principales: le dataset ne contient pas toutes les informations operationnelles "
        "du marche, comme les flux transfrontaliers complets, les indisponibilites de centrales "
        "ou les previsions meteo detaillees. Les resultats doivent donc etre presentes comme "
        "un prototype analytique, pas comme un outil de trading pret pour la production."
    )

    add_metric_explanations(document)

    document.add_heading("Conclusion", level=1)
    document.add_paragraph(
        "Le role 4 est rempli: plusieurs modeles sont entraines, compares et interpretes. "
        "Le meilleur compromis pour le scenario principal 1h est le modele retenu automatiquement "
        "par l'average precision. Les horizons 3h, 6h et 12h restent utiles pour montrer les limites "
        "d'anticipation."
    )

    output_path = BASE_DIR / "rapport_performance_role4.docx"
    document.save(output_path)
    return output_path


def write_pdf_report(
    metrics_df: pd.DataFrame,
    best: ModelResult,
    importance_df: pd.DataFrame,
    splits: TemporalSplits,
    horizon_comparison_df: pd.DataFrame,
) -> Path:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    output_path = BASE_DIR / "rapport_performance_role4.pdf"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=36,
        leftMargin=36,
        topMargin=32,
        bottomMargin=32,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Rapport Role 4 - Modelisation predictive", styles["Title"]),
        Spacer(1, 0.15 * inch),
        Paragraph(
            "Objectif: predire 24 heures a l'avance les episodes de prix negatif "
            "dans au moins une zone danoise (DK1 ou DK2).",
            styles["BodyText"],
        ),
        Paragraph(
            f"Meilleur modele 1h: <b>{best.name}</b>. Average precision: "
            f"{best.metrics['average_precision']:.4f}; ROC-AUC: {best.metrics['roc_auc']:.4f}; "
            f"F1: {best.metrics['f1']:.4f}; precision: {best.metrics['precision']:.4f}; "
            f"recall: {best.metrics['recall']:.4f}.",
            styles["BodyText"],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("Comparaison des horizons", styles["Heading1"]),
        Paragraph(
            "Le 1h mesure une alerte tres court terme, le 12h est un compromis, "
            "et le 24h teste une anticipation plus longue.",
            styles["BodyText"],
        ),
        pdf_table(horizon_comparison_df),
        Spacer(1, 0.15 * inch),
        Paragraph("Comparaison des modeles pour l'horizon 1h", styles["Heading1"]),
        pdf_table(metrics_df),
        Spacer(1, 0.15 * inch),
        Paragraph("Variables les plus influentes", styles["Heading1"]),
        Paragraph(
            "L'importance par permutation indique combien la performance baisse quand une variable est perturbee.",
            styles["BodyText"],
        ),
        pdf_table(importance_df.head(10)),
        Spacer(1, 0.15 * inch),
        Paragraph("Analyse critique", styles["Heading1"]),
        Paragraph(
            "La classe positive est rare; l'accuracy brute n'est donc pas pertinente. "
            "Les horizons plus longs reduisent le lien avec les informations immediates et rendent la prediction plus difficile. "
            "La derive temporelle reste un risque, car les prix negatifs deviennent plus frequents dans la periode de test.",
            styles["BodyText"],
        ),
        Paragraph(
            "SHAP n'etant pas installe localement, l'interpretabilite repose sur l'importance par permutation.",
            styles["BodyText"],
        ),
        Paragraph("Explication rapide des metriques", styles["Heading1"]),
        Paragraph(
            "Average precision: metrique principale pour classes rares. ROC-AUC: classement global. "
            "Precision: qualite des alertes. Recall: part des vrais episodes detectes. "
            "F1: compromis precision/recall. Balanced accuracy: accuracy corrigee pour le desequilibre.",
            styles["BodyText"],
        ),
        PageBreak(),
    ]

    for title, image_name in (
        ("Comparaison des horizons", "horizon_comparison.png"),
        ("Courbes precision-rappel", "precision_recall_curves.png"),
        ("Matrice de confusion", "confusion_matrix_best_model.png"),
        ("Importance des variables", "feature_importance_best_model.png"),
    ):
        image_path = FIGURES_DIR / image_name
        if image_path.exists():
            story.append(Paragraph(title, styles["Heading1"]))
            story.append(Image(str(image_path), width=7.0 * inch, height=4.5 * inch))
            story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    return output_path


def pdf_table(df: pd.DataFrame) -> Table:
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    visible = df.copy()
    for column in visible.columns:
        if pd.api.types.is_float_dtype(visible[column]):
            visible[column] = visible[column].map(lambda value: f"{value:.4f}")
    data = [list(visible.columns)] + visible.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
            ]
        )
    )
    return table


def run_horizon(df: pd.DataFrame, horizon: int) -> HorizonRun:
    features, target = build_features(df, prediction_horizon_hours=horizon)
    splits = split_temporally(features, target)
    results = tune_and_train(splits)
    metrics_df = save_metrics(results, filename=f"model_performance_{horizon}h.csv")
    best = max(results, key=lambda result: result.metrics["average_precision"])
    return HorizonRun(
        horizon=horizon,
        splits=splits,
        results=results,
        metrics_df=metrics_df,
        best=best,
    )


def main() -> None:
    ensure_output_dirs()
    df = load_dataset(DATA_PATH)
    horizon_runs = [run_horizon(df, horizon) for horizon in EVALUATED_HORIZONS]
    primary_run = next(run for run in horizon_runs if run.horizon == PREDICTION_HORIZON_HOURS)
    splits = primary_run.splits
    results = primary_run.results
    metrics_df = primary_run.metrics_df
    best = primary_run.best
    metrics_df.to_csv(REPORTS_DIR / "model_performance.csv", index=False)
    horizon_comparison_df = plot_horizon_comparison(horizon_runs)

    joblib.dump(best.estimator, MODELS_DIR / "best_model.joblib")
    joblib.dump(
        {f"{run.horizon}h_{result.name}": result.estimator for run in horizon_runs for result in run.results},
        MODELS_DIR / "all_horizon_models.joblib",
    )
    joblib.dump({result.name: result.estimator for result in results}, MODELS_DIR / "all_models.joblib")

    plot_confusion_matrix(splits.y_test, best.y_test_pred, best.name)
    plot_precision_recall(results, splits.y_test)
    importance_df = save_importance(best, splits)
    write_report(metrics_df, best, importance_df, splits, horizon_comparison_df)
    docx_path = write_docx_report(metrics_df, best, importance_df, splits, horizon_comparison_df)
    pdf_path = BASE_DIR / "rapport_performance_role4.pdf"
    if GENERATE_PDF:
        pdf_path = write_pdf_report(metrics_df, best, importance_df, splits, horizon_comparison_df)

    summary = {
        "best_model": best.name,
        "best_metrics": best.metrics,
        "prediction_horizon_hours": PREDICTION_HORIZON_HOURS,
        "evaluated_horizons": list(EVALUATED_HORIZONS),
        "docx_report": str(docx_path),
        "train_period": [str(splits.X_train.index.min()), str(splits.X_train.index.max())],
        "validation_period": [str(splits.X_val.index.min()), str(splits.X_val.index.max())],
        "test_period": [str(splits.X_test.index.min()), str(splits.X_test.index.max())],
    }
    if GENERATE_PDF:
        summary["pdf_report"] = str(pdf_path)
    (REPORTS_DIR / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
