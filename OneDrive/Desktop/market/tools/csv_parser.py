"""
CSV Parser Tool — Validates and loads CSV files into pandas DataFrames.
"""

import pandas as pd
import io
import time
from typing import Tuple, Optional
from agent.schemas import CSVParserInput, CSVParserOutput


TOOL_NAME = "CSV_Parser"
TOOL_TIMEOUT = 30  # seconds


def parse_csv(input_data: CSVParserInput) -> Tuple[CSVParserOutput, Optional[pd.DataFrame]]:
    """
    Parse a CSV file from disk path or raw bytes.

    Returns:
        Tuple of (structured output, DataFrame or None on failure)
    """
    try:
        df: Optional[pd.DataFrame] = None

        if input_data.file_bytes is not None:
            df = pd.read_csv(io.BytesIO(input_data.file_bytes))
        elif input_data.file_path is not None:
            df = pd.read_csv(input_data.file_path)
        else:
            return CSVParserOutput(
                success=False,
                error="No file path or bytes provided.",
            ), None

        if df.empty:
            return CSVParserOutput(
                success=False,
                error="CSV file is empty.",
            ), None

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        if not numeric_cols:
            return CSVParserOutput(
                success=False,
                error="CSV contains no numeric columns. At least one numeric column is required for trend analysis.",
            ), None

        return CSVParserOutput(
            success=True,
            row_count=len(df),
            column_count=len(df.columns),
            columns=df.columns.tolist(),
            numeric_columns=numeric_cols,
        ), df

    except pd.errors.EmptyDataError:
        return CSVParserOutput(success=False, error="CSV file is empty or malformed."), None
    except pd.errors.ParserError as e:
        return CSVParserOutput(success=False, error=f"CSV parsing error: {str(e)}"), None
    except FileNotFoundError:
        return CSVParserOutput(success=False, error="File not found."), None
    except Exception as e:
        return CSVParserOutput(success=False, error=f"Unexpected error: {str(e)}"), None
