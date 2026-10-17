"""Bounded hyperparameter search policy and tuning engine for Rung D GBM models.

Adheres to Rules R-MD-04, R-MD-10, R-CD-01, and Profile B workstation resource constraints.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import catboost as cb
import lightgbm as lgb
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from sklearn.model_selection import KFold

from compintel.models.gbm.config import GBMModelType, SearchBudgetPolicy

if TYPE_CHECKING:
    import pandas as pd


class HyperparameterTrial(BaseModel):
    """Record of a single hyperparameter evaluation trial."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: int
    params: dict[str, Any]
    score: float
    duration_seconds: float


class TuningResult(BaseModel):
    """Aggregated output from hyperparameter tuning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    best_params: dict[str, Any]
    best_score: float
    total_evals: int = Field(ge=0)
    total_duration_seconds: float = Field(ge=0.0)
    trials: list[HyperparameterTrial] = Field(default_factory=list)


def sample_hyperparameters(
    model_type: GBMModelType,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Sample candidate hyperparameters from a bounded search space.

    Args:
        model_type: Algorithm family (LightGBM or CatBoost).
        rng: Deterministic numpy random generator.

    Returns:
        Dictionary of sampled hyperparameters.
    """
    learning_rate = float(rng.choice([0.02, 0.05, 0.10, 0.15]))
    n_estimators = int(rng.choice([30, 50, 100, 150]))
    max_depth = int(rng.choice([3, 4, 5, 6]))
    l2_reg = float(rng.choice([0.1, 1.0, 5.0, 10.0]))

    if model_type == GBMModelType.LIGHTGBM:
        num_leaves = min(int(2**max_depth - 1), int(rng.choice([15, 31, 63])))
        min_child_samples = int(rng.choice([2, 5, 10]))
        subsample = float(rng.choice([0.7, 0.85, 1.0]))
        colsample_bytree = float(rng.choice([0.7, 0.85, 1.0]))
        return {
            "learning_rate": learning_rate,
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "num_leaves": max(2, num_leaves),
            "reg_lambda": l2_reg,
            "min_child_samples": min_child_samples,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
        }

    # CatBoost
    return {
        "learning_rate": learning_rate,
        "iterations": n_estimators,
        "depth": max_depth,
        "l2_leaf_reg": l2_reg,
    }


def _evaluate_lightgbm_cv(
    features_df: pd.DataFrame,
    y: np.ndarray,
    params: dict[str, Any],
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
    seed: int,
) -> float:
    """Evaluate LightGBM parameter set across cross-validation splits."""
    clean_df = features_df.copy()
    for col in clean_df.select_dtypes(include=["object", "string"]).columns:
        clean_df[col] = clean_df[col].astype("category")

    scores: list[float] = []
    for train_idx, val_idx in cv_splits:
        x_tr, y_tr = clean_df.iloc[train_idx], y[train_idx]
        x_val, y_val = clean_df.iloc[val_idx], y[val_idx]

        # Adjust min_child_samples for small folds
        fold_min_child = min(params.get("min_child_samples", 5), max(1, len(train_idx) // 2))
        fold_params = dict(params)
        fold_params["min_child_samples"] = fold_min_child
        fold_params["verbose"] = -1
        fold_params["random_state"] = seed

        model = lgb.LGBMRegressor(**fold_params)
        model.fit(x_tr, y_tr)
        preds = model.predict(x_val)
        mae = float(np.mean(np.abs(y_val - preds)))
        scores.append(-mae)

    return float(np.mean(scores))


def _evaluate_catboost_cv(
    features_df: pd.DataFrame,
    y: np.ndarray,
    params: dict[str, Any],
    cat_features: list[str],
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
    seed: int,
) -> float:
    """Evaluate CatBoost parameter set across cross-validation splits."""
    scores: list[float] = []
    for train_idx, val_idx in cv_splits:
        x_tr, y_tr = features_df.iloc[train_idx], y[train_idx]
        x_val, y_val = features_df.iloc[val_idx], y[val_idx]

        fold_params = dict(params)
        fold_params["verbose"] = 0
        fold_params["random_seed"] = seed
        fold_params["allow_writing_files"] = False

        model = cb.CatBoostRegressor(**fold_params)
        model.fit(x_tr, y_tr, cat_features=cat_features)
        preds = model.predict(x_val)
        mae = float(np.mean(np.abs(y_val - preds)))
        scores.append(-mae)

    return float(np.mean(scores))


def tune_gbm_hyperparameters(
    model_type: GBMModelType,
    features_df: pd.DataFrame,
    y: np.ndarray,
    budget: SearchBudgetPolicy,
    cat_features: list[str] | None = None,
) -> TuningResult:
    """Execute bounded random search over hyperparameters respecting budget limits.

    Args:
        model_type: Algorithm family (LightGBM or CatBoost).
        features_df: Feature DataFrame with proper types.
        y: Target array (log compensation).
        budget: Search budget policy governing trials and timeout.
        cat_features: List of categorical column names.

    Returns:
        TuningResult containing best parameters, trial logs, and metrics.
    """
    start_time = time.perf_counter()
    rng = np.random.default_rng(budget.random_seed)
    n_samples = len(features_df)
    cat_cols = cat_features or []

    # Configure cross-validation splits
    effective_folds = min(budget.cv_folds, max(2, n_samples))
    if n_samples < 4:
        # Micro-dataset fallback: evaluate on training set directly
        cv_splits = [(np.arange(n_samples), np.arange(n_samples))]
    else:
        kf = KFold(n_splits=effective_folds, shuffle=True, random_state=budget.random_seed)
        cv_splits = list(kf.split(features_df))

    trials: list[HyperparameterTrial] = []
    best_params: dict[str, Any] = {}
    best_score: float = -float("inf")

    # Always evaluate default baseline configuration as trial 0
    if model_type == GBMModelType.LIGHTGBM:
        default_params: dict[str, Any] = {
            "learning_rate": 0.05,
            "n_estimators": 50,
            "max_depth": 4,
            "num_leaves": 15,
            "reg_lambda": 1.0,
            "min_child_samples": 5,
        }
    else:
        default_params = {
            "learning_rate": 0.05,
            "iterations": 50,
            "depth": 4,
            "l2_leaf_reg": 1.0,
        }

    candidate_params = [default_params]
    for _ in range(budget.max_evals - 1):
        candidate_params.append(sample_hyperparameters(model_type, rng))

    for idx, params in enumerate(candidate_params):
        elapsed = time.perf_counter() - start_time
        if elapsed >= budget.timeout_seconds:
            break

        trial_start = time.perf_counter()
        if model_type == GBMModelType.LIGHTGBM:
            score = _evaluate_lightgbm_cv(features_df, y, params, cv_splits, budget.random_seed)
        else:
            score = _evaluate_catboost_cv(
                features_df, y, params, cat_cols, cv_splits, budget.random_seed
            )

        trial_duration = time.perf_counter() - trial_start
        trials.append(
            HyperparameterTrial(
                trial_id=idx,
                params=params,
                score=score,
                duration_seconds=trial_duration,
            )
        )

        if score > best_score:
            best_score = score
            best_params = params

    total_duration = time.perf_counter() - start_time
    return TuningResult(
        best_params=best_params,
        best_score=best_score,
        total_evals=len(trials),
        total_duration_seconds=total_duration,
        trials=trials,
    )
