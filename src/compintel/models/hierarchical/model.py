"""Rung C baseline: Hierarchical partial pooling model with Empirical Bayes shrinkage (T6.02a).

Decomposes guaranteed cash compensation on the log scale across nested occupational,
geographic, and employer hierarchies:
- Level 0 Global Baseline: Global mean and Mincerian quadratic tenure curve.
- Level 1 & 0 Occupational Hierarchy: Empirical Bayes shrinkage (Role -> Seniority -> Cell).
- Level 1 Employer Archetype: Organizational tier random effects with shrinkage.
- Level 2 Employer Cluster: Enterprise cluster shrinkage with k_min >= 5 floor (Rule R-DA-10).

Adheres to:
- Rule R-MD-01: Benchmark ladder; Rung C parametric partial pooling competing against Rung A/B.
- Rule R-MD-04: Feature scaling and transformation parameters fit inside training folds.
- Rule R-MD-06: Log pay target transformation (log guaranteed_cash_annual).
- Rule R-MD-08: Thin evidence abstention (THIN_EVIDENCE) for severe out-of-distribution inputs.
- Rule R-MD-10: Pinned dependencies and reproducible random seed.
- Rule R-UQ-01: No lone numbers; outputs P10, P50, P90 with sample sizes and shrinkage metadata.
- Rule R-UQ-05: Quantile monotonicity guaranteed (zero crossing rate after monotone repair).
- Rule R-UQ-06: Prior and posterior predictive distributions auditable with variance components.
- Rule R-CD-01: Strict typing and complete mypy compliance.
- Rule R-CD-02: Pure functions and deterministic inference without hidden state.
- Rule R-CD-03 & Import Linter: Zero imports of evaluation, serving, ingestion, or quality.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import NormalDist
from typing import Any, Self

import numpy as np
import polars as pl
import structlog

from compintel.models.hierarchical.config import HierarchicalConfig
from compintel.models.hierarchical.prediction import HierarchicalPrediction

logger = structlog.get_logger(__name__)

STATUTORY_MIN_ANNUAL_LPA: float = 0.50


@dataclass(frozen=True)
class GroupNode:
    """Audit node representing a single node in the shrinkage hierarchy."""

    group_key: str
    sample_size: int
    raw_mean: float
    shrunk_mean: float
    shrinkage_factor: float
    parent_mean: float

    def to_dict(self) -> dict[str, Any]:
        """Convert group node to dictionary."""
        return asdict(self)


class HierarchicalPartialPoolingModel:
    """Rung C hierarchical Bayesian partial pooling model on log pay."""

    def __init__(self, config: HierarchicalConfig | None = None) -> None:
        """Initialize hierarchical model with configuration."""
        self.config: HierarchicalConfig = config or HierarchicalConfig()
        self.is_fitted: bool = False

        # Global fixed parameters
        self.global_mean_: float = 0.0
        self.beta_experience_linear_: float = 0.0
        self.beta_experience_quadratic_: float = 0.0
        self.residual_std_: float = 0.0
        self.train_sample_size_: int = 0

        # Variance components (between-group variances tau^2)
        self.tau_role_: float = 0.0
        self.tau_role_sen_: float = 0.0
        self.tau_cell_: float = 0.0
        self.tau_tier_: float = 0.0
        self.tau_emp_: float = 0.0

        # Hierarchy nodes: mapping group_key -> GroupNode
        self.nodes_role_: dict[str, GroupNode] = {}
        self.nodes_role_sen_: dict[str, GroupNode] = {}
        self.nodes_cell_: dict[str, GroupNode] = {}
        self.nodes_tier_: dict[str, GroupNode] = {}
        self.nodes_emp_: dict[str, GroupNode] = {}

    def fit(self, df: pl.DataFrame) -> Self:
        """Fit hierarchical partial pooling model on training partition.

        Args:
            df: Polars DataFrame containing training observations. Must include:
                'guaranteed_cash_annual', 'years_experience', 'role_family',
                'seniority', 'location'. Optional: 'employer_tier', 'employer_cluster_id'.

        Returns:
            Self: Fitted model instance.
        """
        required_cols = [
            "guaranteed_cash_annual",
            "years_experience",
            "role_family",
            "seniority",
            "location",
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            msg = f"Training DataFrame missing required columns: {missing}"
            raise ValueError(msg)

        # Filter valid records strictly
        valid_df = df.filter(
            pl.col("guaranteed_cash_annual").is_not_null()
            & (pl.col("guaranteed_cash_annual") > 0.0)
            & pl.col("years_experience").is_not_null()
            & (pl.col("years_experience") >= 0.0)
            & (pl.col("years_experience") <= self.config.max_experience_bound)
            & pl.col("role_family").is_not_null()
            & pl.col("seniority").is_not_null()
            & pl.col("location").is_not_null()
        )

        n_samples = len(valid_df)
        self.train_sample_size_ = n_samples

        if n_samples < self.config.global_thin_evidence_threshold:
            logger.warning(
                "hierarchical_model_insufficient_samples",
                n_samples=n_samples,
                threshold=self.config.global_thin_evidence_threshold,
            )
            self.is_fitted = False
            return self

        # Extract numpy arrays for log pay and experience
        y_nom = valid_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        y_log = np.log(y_nom)
        x_exp = valid_df["years_experience"].to_numpy().astype(np.float64)

        # 1. Fit Global Fixed Effects: Base intercept + Mincerian experience curve
        if self.config.experience_polynomial_degree == 2:
            x_mat = np.column_stack([np.ones(n_samples), x_exp, x_exp**2])
            coeffs, residuals, _, _ = np.linalg.lstsq(x_mat, y_log, rcond=None)
            self.global_mean_ = float(coeffs[0])
            self.beta_experience_linear_ = float(coeffs[1])
            self.beta_experience_quadratic_ = float(coeffs[2])
        else:
            x_mat = np.column_stack([np.ones(n_samples), x_exp])
            coeffs, residuals, _, _ = np.linalg.lstsq(x_mat, y_log, rcond=None)
            self.global_mean_ = float(coeffs[0])
            self.beta_experience_linear_ = float(coeffs[1])
            self.beta_experience_quadratic_ = 0.0

        # Compute fixed predictions and residuals
        pred_fixed = (
            self.global_mean_
            + self.beta_experience_linear_ * x_exp
            + self.beta_experience_quadratic_ * (x_exp**2)
        )
        r_all = y_log - pred_fixed
        self.residual_std_ = max(float(np.std(r_all, ddof=1)), 1e-4)
        sigma2_res = self.residual_std_**2

        # Attach residuals to valid_df
        fit_df = valid_df.with_columns(pl.Series("residual_log_pay", r_all))

        # 2. Level 0A / 1: Role Family partial pooling
        self.tau_role_, self.nodes_role_ = self._fit_shrinkage_layer(
            df=fit_df,
            group_col="role_family",
            parent_means={},
            default_parent=0.0,
            sigma2=sigma2_res,
        )

        # 3. Level 0B: Seniority within Role Family
        role_sen_df = fit_df.with_columns(
            (pl.col("role_family") + "::" + pl.col("seniority")).alias("role_sen_key")
        )
        role_parent_map = {
            f"{role}::{sen}": self.nodes_role_[role].shrunk_mean
            for role in self.nodes_role_
            for sen in valid_df["seniority"].unique().to_list()
        }
        self.tau_role_sen_, self.nodes_role_sen_ = self._fit_shrinkage_layer(
            df=role_sen_df,
            group_col="role_sen_key",
            parent_means=role_parent_map,
            default_parent=0.0,
            sigma2=sigma2_res,
        )

        # 4. Level 0C: Full Cell (Role x Seniority x Location)
        cell_df = role_sen_df.with_columns(
            (pl.col("role_family") + "::" + pl.col("seniority") + "::" + pl.col("location")).alias(
                "cell_key"
            )
        )
        cell_parent_map = {
            f"{role}::{sen}::{loc}": (
                self.nodes_role_sen_[f"{role}::{sen}"].shrunk_mean
                if f"{role}::{sen}" in self.nodes_role_sen_
                else 0.0
            )
            for role in self.nodes_role_
            for sen in valid_df["seniority"].unique().to_list()
            for loc in valid_df["location"].unique().to_list()
        }
        self.tau_cell_, self.nodes_cell_ = self._fit_shrinkage_layer(
            df=cell_df,
            group_col="cell_key",
            parent_means=cell_parent_map,
            default_parent=0.0,
            sigma2=sigma2_res,
        )

        # 5. Employer Tier Layer (if enabled and present)
        if self.config.enable_employer_tier and "employer_tier" in fit_df.columns:
            tier_df = fit_df.filter(pl.col("employer_tier").is_not_null())
            if len(tier_df) > 0:
                self.tau_tier_, self.nodes_tier_ = self._fit_shrinkage_layer(
                    df=tier_df,
                    group_col="employer_tier",
                    parent_means={},
                    default_parent=0.0,
                    sigma2=sigma2_res,
                )

        # 6. Employer Cluster Layer with k_min threshold (if enabled and present)
        if self.config.enable_employer_cluster and "employer_cluster_id" in fit_df.columns:
            emp_df = fit_df.filter(pl.col("employer_cluster_id").is_not_null())
            if len(emp_df) > 0:
                emp_parent_map: dict[str, float] = {}
                if "employer_tier" in emp_df.columns:
                    for row in (
                        emp_df.select(["employer_cluster_id", "employer_tier"])
                        .unique()
                        .iter_rows(named=True)
                    ):
                        cid = str(row["employer_cluster_id"])
                        tier = str(row["employer_tier"])
                        tier_mean = (
                            self.nodes_tier_[tier].shrunk_mean if tier in self.nodes_tier_ else 0.0
                        )
                        emp_parent_map[cid] = tier_mean

                self.tau_emp_, self.nodes_emp_ = self._fit_shrinkage_layer(
                    df=emp_df,
                    group_col="employer_cluster_id",
                    parent_means=emp_parent_map,
                    default_parent=0.0,
                    sigma2=sigma2_res,
                    k_min=self.config.k_min_employer,
                )

        self.is_fitted = True
        logger.info(
            "hierarchical_model_fitted",
            n_samples=n_samples,
            n_cells=len(self.nodes_cell_),
            residual_std=self.residual_std_,
            tau_cell=self.tau_cell_,
            tau_tier=self.tau_tier_,
            tau_emp=self.tau_emp_,
        )
        return self

    def _fit_shrinkage_layer(
        self,
        df: pl.DataFrame,
        group_col: str,
        parent_means: dict[str, float],
        default_parent: float,
        sigma2: float,
        k_min: int = 1,
    ) -> tuple[float, dict[str, GroupNode]]:
        """Fit empirical Bayes variance component and shrinkage factors for a hierarchy layer."""
        group_agg = (
            df.group_by(group_col)
            .agg(
                [
                    pl.len().alias("count"),
                    pl.col("residual_log_pay").mean().alias("raw_mean"),
                ]
            )
            .sort("count", descending=True)
        )

        n_groups = len(group_agg)
        if n_groups == 0:
            return 0.0, {}

        counts = group_agg["count"].to_numpy().astype(np.float64)
        raw_means = group_agg["raw_mean"].to_numpy().astype(np.float64)
        keys = [str(k) for k in group_agg[group_col].to_list()]

        # Empirical Bayes between-group variance estimation (DerSimonian-Laird method of moments)
        grand_mean = float(np.average(raw_means, weights=counts))
        if n_groups > 1:
            q_stat = float(np.sum(counts * (raw_means - grand_mean) ** 2))
            c_factor = float(np.sum(counts) - (np.sum(counts**2) / np.sum(counts)))
            tau2_est = max(0.0, (q_stat - (n_groups - 1) * sigma2) / max(c_factor, 1.0))
        else:
            tau2_est = self.config.prior_variance_damping

        tau_est = math.sqrt(tau2_est + self.config.prior_variance_damping)

        # Compute shrinkage for each group node
        nodes: dict[str, GroupNode] = {}
        for key, count, raw_mean in zip(keys, counts, raw_means, strict=True):
            parent_mean = parent_means.get(key, default_parent)
            int_count = int(count)

            # If sample size below k_min floor (R-DA-10), shrink entirely to parent prior
            if int_count < k_min:
                nodes[key] = GroupNode(
                    group_key=key,
                    sample_size=int_count,
                    raw_mean=float(raw_mean),
                    shrunk_mean=float(parent_mean),
                    shrinkage_factor=0.0,
                    parent_mean=float(parent_mean),
                )
                continue

            # James-Stein / Empirical Bayes shrinkage factor: lambda = tau^2 / (tau^2 + sigma^2 / n)
            denom = tau2_est + (sigma2 / count)
            lambda_factor = float(tau2_est / denom) if denom > 0.0 else 0.0
            lambda_factor = min(max(lambda_factor, 0.0), 1.0)

            shrunk_mean = float(lambda_factor * raw_mean + (1.0 - lambda_factor) * parent_mean)

            nodes[key] = GroupNode(
                group_key=key,
                sample_size=int_count,
                raw_mean=float(raw_mean),
                shrunk_mean=shrunk_mean,
                shrinkage_factor=lambda_factor,
                parent_mean=float(parent_mean),
            )

        return tau_est, nodes

    def predict_single(
        self,
        years_experience: float,
        role_family: str,
        seniority: str,
        location: str,
        employer_tier: str | None = None,
        employer_cluster_id: str | None = None,
    ) -> HierarchicalPrediction:
        """Produce conditional quantile prediction for a single career profile."""
        if not self.is_fitted:
            return HierarchicalPrediction(
                p10=None,
                p50=None,
                p90=None,
                point_estimate=None,
                log_mean=None,
                log_std=None,
                is_abstained=True,
                abstention_reason="MODEL_NOT_FITTED",
            )

        # Check experience range (Rule R-MD-08 thin evidence abstention)
        if years_experience < 0.0 or years_experience > self.config.max_experience_bound:
            return HierarchicalPrediction(
                p10=None,
                p50=None,
                p90=None,
                point_estimate=None,
                log_mean=None,
                log_std=None,
                is_abstained=True,
                abstention_reason="THIN_EVIDENCE",
            )

        # 1. Global fixed experience curve
        yoe = float(years_experience)
        exp_linear = self.beta_experience_linear_ * yoe
        exp_quad = self.beta_experience_quadratic_ * (yoe**2)
        fixed_mean = self.global_mean_ + exp_linear + exp_quad

        # 2. Occupational cell hierarchy lookup
        cell_key = f"{role_family}::{seniority}::{location}"
        role_sen_key = f"{role_family}::{seniority}"
        role_key = role_family

        lambda_cell = 0.0
        n_cell = 0
        if cell_key in self.nodes_cell_:
            node_cell = self.nodes_cell_[cell_key]
            shrunk_cell = node_cell.shrunk_mean
            lambda_cell = node_cell.shrinkage_factor
            n_cell = node_cell.sample_size
        elif role_sen_key in self.nodes_role_sen_:
            node_rs = self.nodes_role_sen_[role_sen_key]
            shrunk_cell = node_rs.shrunk_mean
            lambda_cell = node_rs.shrinkage_factor
            n_cell = node_rs.sample_size
        elif role_key in self.nodes_role_:
            node_role = self.nodes_role_[role_key]
            shrunk_cell = node_role.shrunk_mean
            lambda_cell = node_role.shrinkage_factor
            n_cell = node_role.sample_size
        else:
            shrunk_cell = 0.0

        # 3. Employer tier lookup
        shrunk_tier = 0.0
        lambda_tier = 0.0
        n_tier = 0
        if employer_tier and employer_tier in self.nodes_tier_:
            node_tier = self.nodes_tier_[employer_tier]
            shrunk_tier = node_tier.shrunk_mean
            lambda_tier = node_tier.shrinkage_factor
            n_tier = node_tier.sample_size

        # 4. Employer cluster lookup (with tier fallback)
        shrunk_emp = 0.0
        lambda_emp = 0.0
        n_emp = 0
        if employer_cluster_id and employer_cluster_id in self.nodes_emp_:
            node_emp = self.nodes_emp_[employer_cluster_id]
            shrunk_emp = node_emp.shrunk_mean
            lambda_emp = node_emp.shrinkage_factor
            n_emp = node_emp.sample_size
        elif employer_tier:
            shrunk_emp = shrunk_tier

        # Combine effects: cell + employer
        emp_effect = shrunk_emp if employer_cluster_id else shrunk_tier
        log_mean = fixed_mean + shrunk_cell + emp_effect

        # Predictive uncertainty on log scale:
        # Incorporates residual variance plus parameter uncertainty
        var_est = (self.residual_std_**2) / max(self.train_sample_size_, 1)
        var_cell = (self.tau_cell_**2) * (1.0 - lambda_cell) if n_cell > 0 else (self.tau_cell_**2)

        log_var = (self.residual_std_**2) + var_est + var_cell
        log_std = math.sqrt(max(log_var, 1e-4))

        # Quantile predictions on nominal INR LPA scale
        quantiles_dict: dict[float, float] = {}
        for q in self.config.quantiles:
            z_score = float(NormalDist().inv_cdf(q))
            nom_val = math.exp(log_mean + log_std * z_score)
            quantiles_dict[q] = max(nom_val, STATUTORY_MIN_ANNUAL_LPA)

        raw_p10 = quantiles_dict.get(0.10)
        raw_p50 = quantiles_dict.get(0.50)
        raw_p90 = quantiles_dict.get(0.90)

        # Monotone crossing detection and rearrangement repair (Rule R-UQ-05)
        is_repaired = False
        p10, p50, p90 = raw_p10, raw_p50, raw_p90
        if p10 is not None and p50 is not None and p90 is not None and (p10 > p50 or p50 > p90):
            sorted_vals = sorted([p10, p50, p90])
            p10, p50, p90 = sorted_vals[0], sorted_vals[1], sorted_vals[2]
            is_repaired = True

        return HierarchicalPrediction(
            p10=p10,
            p50=p50,
            p90=p90,
            point_estimate=p50,
            log_mean=log_mean,
            log_std=log_std,
            shrinkage_weights={
                "cell": lambda_cell,
                "tier": lambda_tier,
                "emp": lambda_emp,
            },
            shrunk_components={
                "global_intercept": self.global_mean_,
                "experience_curve": exp_linear + exp_quad,
                "cell_effect": shrunk_cell,
                "tier_effect": shrunk_tier,
                "emp_effect": shrunk_emp,
            },
            effective_sample_sizes={
                "cell": n_cell,
                "tier": n_tier,
                "emp": n_emp,
            },
            is_crossing_repaired=is_repaired,
            is_abstained=False,
            abstention_reason=None,
        )

    def predict(self, df: pl.DataFrame) -> pl.DataFrame:
        """Vectorized batch prediction returning DataFrame with quantiles and metadata."""
        if len(df) == 0:
            return pl.DataFrame(
                schema={
                    "p10": pl.Float64,
                    "p50": pl.Float64,
                    "p90": pl.Float64,
                    "point_estimate": pl.Float64,
                    "is_crossing_repaired": pl.Boolean,
                    "is_abstained": pl.Boolean,
                    "abstention_reason": pl.String,
                    "shrinkage_cell": pl.Float64,
                    "shrinkage_tier": pl.Float64,
                    "shrinkage_emp": pl.Float64,
                }
            )

        has_tier = "employer_tier" in df.columns
        has_emp = "employer_cluster_id" in df.columns

        p10_list: list[float | None] = []
        p50_list: list[float | None] = []
        p90_list: list[float | None] = []
        point_list: list[float | None] = []
        repaired_list: list[bool] = []
        abstained_list: list[bool] = []
        reason_list: list[str | None] = []
        shrunk_cell_list: list[float] = []
        shrunk_tier_list: list[float] = []
        shrunk_emp_list: list[float] = []

        for row in df.iter_rows(named=True):
            pred = self.predict_single(
                years_experience=float(row.get("years_experience", 0.0)),
                role_family=str(row.get("role_family", "")),
                seniority=str(row.get("seniority", "")),
                location=str(row.get("location", "")),
                employer_tier=(
                    str(row["employer_tier"]) if has_tier and row["employer_tier"] else None
                ),
                employer_cluster_id=(
                    str(row["employer_cluster_id"])
                    if has_emp and row["employer_cluster_id"]
                    else None
                ),
            )
            p10_list.append(pred.p10)
            p50_list.append(pred.p50)
            p90_list.append(pred.p90)
            point_list.append(pred.point_estimate)
            repaired_list.append(pred.is_crossing_repaired)
            abstained_list.append(pred.is_abstained)
            reason_list.append(pred.abstention_reason)
            shrunk_cell_list.append(pred.shrinkage_weights.get("cell", 0.0))
            shrunk_tier_list.append(pred.shrinkage_weights.get("tier", 0.0))
            shrunk_emp_list.append(pred.shrinkage_weights.get("emp", 0.0))

        return pl.DataFrame(
            {
                "p10": pl.Series(p10_list, dtype=pl.Float64),
                "p50": pl.Series(p50_list, dtype=pl.Float64),
                "p90": pl.Series(p90_list, dtype=pl.Float64),
                "point_estimate": pl.Series(point_list, dtype=pl.Float64),
                "is_crossing_repaired": pl.Series(repaired_list, dtype=pl.Boolean),
                "is_abstained": pl.Series(abstained_list, dtype=pl.Boolean),
                "abstention_reason": pl.Series(reason_list, dtype=pl.String),
                "shrinkage_cell": pl.Series(shrunk_cell_list, dtype=pl.Float64),
                "shrinkage_tier": pl.Series(shrunk_tier_list, dtype=pl.Float64),
                "shrinkage_emp": pl.Series(shrunk_emp_list, dtype=pl.Float64),
            }
        )

    def get_shrinkage_summary(self) -> dict[str, Any]:
        """Return global variance components and shrinkage factor distributions."""
        cell_lambdas = [n.shrinkage_factor for n in self.nodes_cell_.values()]
        tier_lambdas = [n.shrinkage_factor for n in self.nodes_tier_.values()]
        emp_lambdas = [n.shrinkage_factor for n in self.nodes_emp_.values()]

        return {
            "is_fitted": self.is_fitted,
            "train_sample_size": self.train_sample_size_,
            "global_mean": self.global_mean_,
            "beta_experience_linear": self.beta_experience_linear_,
            "beta_experience_quadratic": self.beta_experience_quadratic_,
            "residual_std": self.residual_std_,
            "variance_components": {
                "tau_role": self.tau_role_,
                "tau_role_sen": self.tau_role_sen_,
                "tau_cell": self.tau_cell_,
                "tau_tier": self.tau_tier_,
                "tau_emp": self.tau_emp_,
            },
            "node_counts": {
                "roles": len(self.nodes_role_),
                "role_sen": len(self.nodes_role_sen_),
                "cells": len(self.nodes_cell_),
                "tiers": len(self.nodes_tier_),
                "employers": len(self.nodes_emp_),
            },
            "median_shrinkage": {
                "cell": float(np.median(cell_lambdas)) if cell_lambdas else 0.0,
                "tier": float(np.median(tier_lambdas)) if tier_lambdas else 0.0,
                "emp": float(np.median(emp_lambdas)) if emp_lambdas else 0.0,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete model state to dictionary representation."""
        return {
            "config": self.config.to_dict(),
            "is_fitted": self.is_fitted,
            "train_sample_size": self.train_sample_size_,
            "global_mean": self.global_mean_,
            "beta_experience_linear": self.beta_experience_linear_,
            "beta_experience_quadratic": self.beta_experience_quadratic_,
            "residual_std": self.residual_std_,
            "tau_role": self.tau_role_,
            "tau_role_sen": self.tau_role_sen_,
            "tau_cell": self.tau_cell_,
            "tau_tier": self.tau_tier_,
            "tau_emp": self.tau_emp_,
            "nodes_role": {k: v.to_dict() for k, v in self.nodes_role_.items()},
            "nodes_role_sen": {k: v.to_dict() for k, v in self.nodes_role_sen_.items()},
            "nodes_cell": {k: v.to_dict() for k, v in self.nodes_cell_.items()},
            "nodes_tier": {k: v.to_dict() for k, v in self.nodes_tier_.items()},
            "nodes_emp": {k: v.to_dict() for k, v in self.nodes_emp_.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HierarchicalPartialPoolingModel:
        """Instantiate model from dictionary representation."""
        config_data = data.get("config", {})
        config = HierarchicalConfig(
            min_cell_sample_size=config_data.get("min_cell_sample_size", 5),
            global_thin_evidence_threshold=config_data.get("global_thin_evidence_threshold", 5),
            max_experience_bound=config_data.get("max_experience_bound", 40.0),
            quantiles=config_data.get("quantiles", [0.10, 0.50, 0.90]),
            experience_polynomial_degree=config_data.get("experience_polynomial_degree", 2),
            prior_variance_damping=config_data.get("prior_variance_damping", 1e-4),
            k_min_employer=config_data.get("k_min_employer", 5),
            enable_employer_tier=config_data.get("enable_employer_tier", True),
            enable_employer_cluster=config_data.get("enable_employer_cluster", True),
            random_seed=config_data.get("random_seed", 42),
        )
        model = cls(config=config)
        model.is_fitted = bool(data.get("is_fitted", False))
        model.train_sample_size_ = int(data.get("train_sample_size", 0))
        model.global_mean_ = float(data.get("global_mean", 0.0))
        model.beta_experience_linear_ = float(data.get("beta_experience_linear", 0.0))
        model.beta_experience_quadratic_ = float(data.get("beta_experience_quadratic", 0.0))
        model.residual_std_ = float(data.get("residual_std", 0.0))
        model.tau_role_ = float(data.get("tau_role", 0.0))
        model.tau_role_sen_ = float(data.get("tau_role_sen", 0.0))
        model.tau_cell_ = float(data.get("tau_cell", 0.0))
        model.tau_tier_ = float(data.get("tau_tier", 0.0))
        model.tau_emp_ = float(data.get("tau_emp", 0.0))

        def _rebuild_nodes(raw_map: dict[str, Any]) -> dict[str, GroupNode]:
            return {
                k: GroupNode(
                    group_key=str(v["group_key"]),
                    sample_size=int(v["sample_size"]),
                    raw_mean=float(v["raw_mean"]),
                    shrunk_mean=float(v["shrunk_mean"]),
                    shrinkage_factor=float(v["shrinkage_factor"]),
                    parent_mean=float(v["parent_mean"]),
                )
                for k, v in raw_map.items()
            }

        model.nodes_role_ = _rebuild_nodes(data.get("nodes_role", {}))
        model.nodes_role_sen_ = _rebuild_nodes(data.get("nodes_role_sen", {}))
        model.nodes_cell_ = _rebuild_nodes(data.get("nodes_cell", {}))
        model.nodes_tier_ = _rebuild_nodes(data.get("nodes_tier", {}))
        model.nodes_emp_ = _rebuild_nodes(data.get("nodes_emp", {}))

        return model
