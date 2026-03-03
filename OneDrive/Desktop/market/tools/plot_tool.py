"""
Plot Tool — Generates Matplotlib trend visualizations.
"""

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for Streamlit

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from typing import Optional
from agent.schemas import PlotInput, PlotOutput, TrendOutput


TOOL_NAME = "PlotTool"
TOOL_TIMEOUT = 30  # seconds

# ─── Premium color palette ───────────────────────────────────────────
COLORS = {
    "background": "#0E1117",
    "card_bg": "#1A1D23",
    "primary_line": "#00D4FF",
    "trend_line": "#FF6B6B",
    "moving_avg": "#FFD93D",
    "grid": "#2A2D35",
    "text": "#E8E8E8",
    "accent": "#6C63FF",
}


def generate_trend_plot(
    df: pd.DataFrame,
    input_data: PlotInput,
    trend_data: Optional[TrendOutput] = None,
) -> plt.Figure:
    """
    Generate a premium-styled trend chart with original data,
    regression trend line, and moving average overlay.
    """
    try:
        col = input_data.column_name
        series = df[col].dropna().astype(float)
        values = series.values
        x = np.arange(len(values))

        # ── Compute overlays ──────────────────────────────────────
        # Trend line
        slope, intercept = np.polyfit(x, values, 1)
        trend_line = slope * x + intercept

        # Moving average
        moving_avg = pd.Series(values).rolling(window=5, min_periods=1).mean().values

        # ── Create figure ─────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(COLORS["background"])
        ax.set_facecolor(COLORS["card_bg"])

        # Data line
        ax.plot(x, values, color=COLORS["primary_line"], linewidth=1.5,
                label="Price Data", alpha=0.9, zorder=3)
        ax.fill_between(x, values, alpha=0.08, color=COLORS["primary_line"])

        # Trend line
        ax.plot(x, trend_line, color=COLORS["trend_line"], linewidth=2,
                linestyle="--", label=f"Trend (slope={slope:.4f})", zorder=4)

        # Moving average
        ax.plot(x, moving_avg, color=COLORS["moving_avg"], linewidth=1.5,
                linestyle="-.", label="Moving Avg (w=5)", alpha=0.8, zorder=3)

        # ── Styling ───────────────────────────────────────────────
        ax.set_title(input_data.title, color=COLORS["text"], fontsize=16,
                     fontweight="bold", pad=20)
        ax.set_xlabel("Time Period", color=COLORS["text"], fontsize=12, labelpad=10)
        ax.set_ylabel(col, color=COLORS["text"], fontsize=12, labelpad=10)

        ax.tick_params(colors=COLORS["text"], labelsize=10)
        ax.grid(True, color=COLORS["grid"], alpha=0.3, linestyle="--")

        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])
            spine.set_linewidth(0.5)

        legend = ax.legend(loc="upper left", fontsize=10,
                           facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"],
                           labelcolor=COLORS["text"])

        # ── Annotation for trend info ─────────────────────────────
        if trend_data and trend_data.success:
            info_text = (
                f"Classification: {trend_data.trend_classification.value}\n"
                f"Confidence: {trend_data.confidence_score:.2%}\n"
                f"Std Dev: {trend_data.standard_deviation:.2f}"
            )
            ax.text(
                0.98, 0.02, info_text,
                transform=ax.transAxes, fontsize=9,
                verticalalignment="bottom", horizontalalignment="right",
                color=COLORS["text"], alpha=0.8,
                bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS["card_bg"],
                          edgecolor=COLORS["grid"], alpha=0.9),
            )

        fig.tight_layout()
        return fig

    except Exception as e:
        # Return an error figure
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor(COLORS["background"])
        ax.set_facecolor(COLORS["card_bg"])
        ax.text(0.5, 0.5, f"Plot Error: {str(e)}",
                transform=ax.transAxes, ha="center", va="center",
                color="#FF6B6B", fontsize=14)
        ax.set_axis_off()
        return fig
