"""
Pydantic schemas for tool inputs/outputs and logging.
Provides structured validation for all tool communication in the agentic pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ─── Trend Classification ───────────────────────────────────────────

class TrendClassification(str, Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"


# ─── CSV Parser Schemas ─────────────────────────────────────────────

class CSVParserInput(BaseModel):
    """Input schema for the CSV Parser tool."""
    file_path: Optional[str] = Field(None, description="Path to CSV file on disk")
    file_bytes: Optional[bytes] = Field(None, description="Raw bytes of uploaded CSV file")
    file_name: Optional[str] = Field(None, description="Original filename for logging")

    class Config:
        arbitrary_types_allowed = True


class CSVParserOutput(BaseModel):
    """Output schema for the CSV Parser tool."""
    success: bool
    row_count: int = 0
    column_count: int = 0
    columns: List[str] = []
    numeric_columns: List[str] = []
    error: Optional[str] = None


# ─── Statistical Trend Module Schemas ────────────────────────────────

class TrendInput(BaseModel):
    """Input schema for the Statistical Trend Module."""
    column_name: str = Field(..., description="Name of the numeric column to analyze")
    seed: int = Field(42, description="Random seed for reproducibility")


class TrendOutput(BaseModel):
    """Output schema for the Statistical Trend Module."""
    success: bool
    slope: float = 0.0
    intercept: float = 0.0
    trend_classification: TrendClassification = TrendClassification.SIDEWAYS
    confidence_score: float = 0.0
    moving_average_window: int = 5
    standard_deviation: float = 0.0
    mean_value: float = 0.0
    data_points: int = 0
    error: Optional[str] = None


# ─── Plot Tool Schemas ───────────────────────────────────────────────

class PlotInput(BaseModel):
    """Input schema for the Plot Tool."""
    column_name: str = Field(..., description="Column name used for the trend line")
    title: str = Field("Market Trend Analysis", description="Chart title")


class PlotOutput(BaseModel):
    """Output schema for the Plot Tool."""
    success: bool
    error: Optional[str] = None


# ─── Tool Call Logging Schema ────────────────────────────────────────

class ToolCallLog(BaseModel):
    """Structured log entry for a single tool call."""
    tool_name: str
    input_data: dict
    output_data: dict
    duration_seconds: float
    success: bool
    error: Optional[str] = None
