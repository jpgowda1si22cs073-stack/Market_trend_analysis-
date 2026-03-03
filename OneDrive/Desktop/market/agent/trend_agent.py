"""
TrendAgent — Central orchestrator for the Market Trend Analyzer.
Controls state transitions, calls tools in order, handles errors, and enforces guardrails.
"""

import uuid
import time
import json
from typing import Optional, List, Dict, Any

import pandas as pd
import numpy as np

from agent.state_machine import StateMachine, AgentState
from agent.schemas import (
    CSVParserInput, CSVParserOutput,
    TrendInput, TrendOutput,
    PlotInput, PlotOutput,
    ToolCallLog,
)
from database.logger import DBLogger
from tools.csv_parser import parse_csv
from tools.statistical_trend_module import analyze_trend
from tools.plot_tool import generate_trend_plot


# ─── Tool Allowlist (Guardrail) ──────────────────────────────────────
ALLOWED_TOOLS = {"CSV_Parser", "StatisticalTrendModule", "PlotTool"}

# ─── Guardrails ──────────────────────────────────────────────────────
MAX_STEPS = 10
DEFAULT_TIMEOUT = 30  # seconds per tool call


class TrendAgent:
    """
    Agentic controller that:
    - Manages the state machine lifecycle
    - Calls tools in the correct order
    - Logs every action to SQLite
    - Generates a unique Run ID
    - Enforces seed-based reproducibility
    - Implements guardrails (max steps, timeout, allowlist)
    """

    def __init__(self):
        self.run_id: str = str(uuid.uuid4())
        self.db_logger = DBLogger()
        self.seed: int = self.db_logger.get_next_seed()
        self.state_machine = StateMachine()

        # Artifacts produced during the run
        self.dataframe: Optional[pd.DataFrame] = None
        self.csv_output: Optional[CSVParserOutput] = None
        self.trend_output: Optional[TrendOutput] = None
        self.figure = None

        # Metrics
        self.processing_time: float = 0.0
        self.step_count: int = 0
        self.tool_logs: List[ToolCallLog] = []

        # Error tracking
        self.error_message: Optional[str] = None

    # ── Properties ────────────────────────────────────────────────

    @property
    def current_state(self) -> AgentState:
        return self.state_machine.current_state

    @property
    def transition_history(self) -> List[dict]:
        return self.state_machine.history_dicts

    @property
    def tool_logs_dicts(self) -> List[dict]:
        return [log.model_dump() for log in self.tool_logs]

    # ── Run Orchestration ─────────────────────────────────────────

    def run(self, file_bytes: bytes, file_name: str = "upload.csv") -> bool:
        """
        Execute the full analysis pipeline.

        Returns True on success, False on error.
        """
        start_time = time.time()
        self.db_logger.start_run(self.run_id, self.seed)

        # Set global seeds for reproducibility
        np.random.seed(self.seed)

        try:
            # ── Step 1: IDLE → LOAD_CSV ───────────────────────────
            self._transition("start_analysis")
            self._step_guard()

            csv_input = CSVParserInput(file_bytes=file_bytes, file_name=file_name)
            self.csv_output, self.dataframe = self._call_tool(
                "CSV_Parser",
                lambda: parse_csv(csv_input),
                csv_input.model_dump(exclude={"file_bytes"}),
            )

            if not self.csv_output.success or self.dataframe is None:
                raise RuntimeError(f"CSV parsing failed: {self.csv_output.error}")

            # ── Step 2: LOAD_CSV → ANALYZE_TREND ──────────────────
            self._transition("csv_loaded")
            self._step_guard()

            # Pick the first numeric column for analysis
            target_col = self.csv_output.numeric_columns[0]
            trend_input = TrendInput(column_name=target_col, seed=self.seed)
            self.trend_output = self._call_tool(
                "StatisticalTrendModule",
                lambda: analyze_trend(self.dataframe, trend_input),
                trend_input.model_dump(),
            )

            if not self.trend_output.success:
                raise RuntimeError(f"Trend analysis failed: {self.trend_output.error}")

            # ── Step 3: ANALYZE_TREND → GENERATE_INSIGHT ──────────
            self._transition("trend_analyzed")
            self._step_guard()

            plot_input = PlotInput(column_name=target_col, title=f"Trend Analysis — {target_col}")
            self.figure = self._call_tool(
                "PlotTool",
                lambda: generate_trend_plot(self.dataframe, plot_input, self.trend_output),
                plot_input.model_dump(),
            )

            # ── Step 4: GENERATE_INSIGHT → COMPLETED ──────────────
            self._transition("insight_generated")

            self.processing_time = round(time.time() - start_time, 4)
            self.db_logger.finish_run(self.run_id, "COMPLETED")
            return True

        except Exception as e:
            self.error_message = str(e)
            self.state_machine.force_error(reason=f"error: {str(e)}")
            self.db_logger.log_transition(
                self.run_id,
                self.state_machine.history[-2].previous_state.value if len(self.state_machine.history) > 1 else "UNKNOWN",
                "error",
                AgentState.ERROR.value,
            )
            self.processing_time = round(time.time() - start_time, 4)
            self.db_logger.finish_run(self.run_id, "ERROR")
            return False

    # ── Tool Calling with Guardrails ──────────────────────────────

    def _call_tool(self, tool_name: str, tool_fn, input_data: dict):
        """
        Call a tool with allowlist check, timeout, and logging.
        """
        # Guardrail: allowlist
        if tool_name not in ALLOWED_TOOLS:
            raise RuntimeError(f"Tool '{tool_name}' is not in the allowlist: {ALLOWED_TOOLS}")

        self.step_count += 1
        start = time.time()

        try:
            result = tool_fn()
            duration = round(time.time() - start, 4)

            # Determine output dict
            if hasattr(result, "model_dump"):
                output_dict = result.model_dump()
            elif isinstance(result, tuple):
                # csv_parser returns (output, df)
                output_obj = result[0]
                output_dict = output_obj.model_dump() if hasattr(output_obj, "model_dump") else {"result": str(output_obj)}
            else:
                output_dict = {"result": "Figure generated" if tool_name == "PlotTool" else str(result)}

            log = ToolCallLog(
                tool_name=tool_name,
                input_data=input_data,
                output_data=output_dict,
                duration_seconds=duration,
                success=True,
            )
            self.tool_logs.append(log)

            self.db_logger.log_tool_call(
                self.run_id, tool_name, input_data, output_dict, duration, True
            )

            # Handle tuple returns (csv_parser)
            if isinstance(result, tuple):
                return result
            return result

        except Exception as e:
            duration = round(time.time() - start, 4)
            log = ToolCallLog(
                tool_name=tool_name,
                input_data=input_data,
                output_data={"error": str(e)},
                duration_seconds=duration,
                success=False,
                error=str(e),
            )
            self.tool_logs.append(log)
            self.db_logger.log_tool_call(
                self.run_id, tool_name, input_data, {"error": str(e)}, duration, False, str(e)
            )
            raise

    # ── State Transition Helper ───────────────────────────────────

    def _transition(self, event: str):
        record = self.state_machine.transition(event)
        self.db_logger.log_transition(
            self.run_id,
            record.previous_state.value,
            record.event,
            record.next_state.value,
        )
        self.step_count += 1

    # ── Step Guardrail ────────────────────────────────────────────

    def _step_guard(self):
        if self.step_count >= MAX_STEPS:
            raise RuntimeError(
                f"Max steps ({MAX_STEPS}) exceeded. Aborting run to prevent runaway execution."
            )

    # ── Reset ─────────────────────────────────────────────────────

    def reset(self):
        """Reset the agent to IDLE state for a new run."""
        self.state_machine.reset()
        self.state_machine.clear_history()
        self.run_id = str(uuid.uuid4())
        self.dataframe = None
        self.csv_output = None
        self.trend_output = None
        self.figure = None
        self.processing_time = 0.0
        self.step_count = 0
        self.tool_logs.clear()
        self.error_message = None
