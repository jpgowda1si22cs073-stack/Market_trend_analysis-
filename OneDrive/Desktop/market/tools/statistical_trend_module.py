"""
Statistical Trend Module — Performs linear regression, moving average,
standard deviation analysis, and trend classification on numeric time-series data.
"""

import numpy as np
import pandas as pd
from agent.schemas import TrendInput, TrendOutput, TrendClassification


TOOL_NAME = "StatisticalTrendModule"
TOOL_TIMEOUT = 30  # seconds

# Thresholds for trend classification
SLOPE_UPTREND_THRESHOLD = 0.001
SLOPE_DOWNTREND_THRESHOLD = -0.001


def analyze_trend(df: pd.DataFrame, input_data: TrendInput) -> TrendOutput:
    """
    Perform statistical trend analysis on a numeric column.

    Steps:
        1. Set numpy random seed for reproducibility
        2. Compute linear regression (slope + intercept)
        3. Compute moving average (window=5)
        4. Compute standard deviation
        5. Classify trend (UPTREND / DOWNTREND / SIDEWAYS)
        6. Compute confidence score

    Returns:
        TrendOutput with all computed metrics.
    """
    try:
        # ── Seed for reproducibility ──────────────────────────────
        np.random.seed(input_data.seed)

        col = input_data.column_name
        if col not in df.columns:
            return TrendOutput(
                success=False,
                error=f"Column '{col}' not found in DataFrame. Available: {df.columns.tolist()}",
            )

        series = df[col].dropna().astype(float)
        if len(series) < 5:
            return TrendOutput(
                success=False,
                error=f"Need at least 5 data points, got {len(series)}.",
            )

        values = series.values
        x = np.arange(len(values), dtype=float)

        # ── Linear Regression ─────────────────────────────────────
        slope, intercept = np.polyfit(x, values, 1)

        # ── Moving Average (window=5) ─────────────────────────────
        window = 5
        moving_avg = pd.Series(values).rolling(window=window, min_periods=1).mean().values

        # ── Standard Deviation ────────────────────────────────────
        std_dev = float(np.std(values))
        mean_val = float(np.mean(values))

        # ── Normalize slope relative to mean ──────────────────────
        norm_slope = slope / abs(mean_val) if mean_val != 0 else slope

        # ── Trend Classification ──────────────────────────────────
        if norm_slope > SLOPE_UPTREND_THRESHOLD:
            classification = TrendClassification.UPTREND
        elif norm_slope < SLOPE_DOWNTREND_THRESHOLD:
            classification = TrendClassification.DOWNTREND
        else:
            classification = TrendClassification.SIDEWAYS

        # ── Confidence Score ──────────────────────────────────────
        # Based on: how strong the slope is relative to noise (std dev)
        coefficient_of_variation = std_dev / abs(mean_val) if mean_val != 0 else 1.0
        slope_strength = min(abs(norm_slope) / 0.05, 1.0)  # normalize to [0, 1]
        noise_penalty = max(1.0 - coefficient_of_variation, 0.0)
        confidence = round(slope_strength * 0.6 + noise_penalty * 0.4, 4)
        confidence = min(max(confidence, 0.0), 1.0)

        return TrendOutput(
            success=True,
            slope=round(float(slope), 6),
            intercept=round(float(intercept), 4),
            trend_classification=classification,
            confidence_score=confidence,
            moving_average_window=window,
            standard_deviation=round(std_dev, 4),
            mean_value=round(mean_val, 4),
            data_points=len(values),
        )

    except Exception as e:
        return TrendOutput(success=False, error=f"Trend analysis failed: {str(e)}")


def get_moving_average(df: pd.DataFrame, column_name: str, window: int = 5) -> np.ndarray:
    """Return the moving average array for plotting."""
    series = df[column_name].dropna().astype(float)
    return pd.Series(series.values).rolling(window=window, min_periods=1).mean().values


def get_trend_line(df: pd.DataFrame, column_name: str) -> np.ndarray:
    """Return the fitted regression line values for plotting."""
    series = df[column_name].dropna().astype(float)
    x = np.arange(len(series), dtype=float)
    slope, intercept = np.polyfit(x, series.values, 1)
    return slope * x + intercept
