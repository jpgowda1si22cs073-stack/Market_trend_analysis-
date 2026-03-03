"""
State Machine for the Market Trend Analyzer Agent.
Manages explicit state transitions with full logging and history tracking.
"""

from enum import Enum
from typing import List, Tuple, Optional
from datetime import datetime


class AgentState(str, Enum):
    """All possible states for the Trend Analyzer agent."""
    IDLE = "IDLE"
    LOAD_CSV = "LOAD_CSV"
    ANALYZE_TREND = "ANALYZE_TREND"
    GENERATE_INSIGHT = "GENERATE_INSIGHT"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class TransitionRecord:
    """A single state transition record."""

    def __init__(self, previous_state: AgentState, event: str, next_state: AgentState):
        self.previous_state = previous_state
        self.event = event
        self.next_state = next_state
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "previous_state": self.previous_state.value,
            "event": self.event,
            "next_state": self.next_state.value,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return f"{self.previous_state.value} → {self.event} → {self.next_state.value}"


# ─── Valid Transition Map ────────────────────────────────────────────

VALID_TRANSITIONS = {
    AgentState.IDLE: {
        "start_analysis": AgentState.LOAD_CSV,
        "error": AgentState.ERROR,
    },
    AgentState.LOAD_CSV: {
        "csv_loaded": AgentState.ANALYZE_TREND,
        "error": AgentState.ERROR,
    },
    AgentState.ANALYZE_TREND: {
        "trend_analyzed": AgentState.GENERATE_INSIGHT,
        "error": AgentState.ERROR,
    },
    AgentState.GENERATE_INSIGHT: {
        "insight_generated": AgentState.COMPLETED,
        "error": AgentState.ERROR,
    },
    AgentState.COMPLETED: {
        "reset": AgentState.IDLE,
    },
    AgentState.ERROR: {
        "reset": AgentState.IDLE,
    },
}


class StateMachine:
    """
    Explicit state machine governing the agent's lifecycle.
    Enforces valid transitions and maintains full history.
    """

    def __init__(self):
        self._state: AgentState = AgentState.IDLE
        self._history: List[TransitionRecord] = []

    # ── Properties ────────────────────────────────────────────────

    @property
    def current_state(self) -> AgentState:
        return self._state

    @property
    def history(self) -> List[TransitionRecord]:
        return list(self._history)

    @property
    def history_dicts(self) -> List[dict]:
        return [r.to_dict() for r in self._history]

    # ── Transition ────────────────────────────────────────────────

    def transition(self, event: str) -> TransitionRecord:
        """
        Attempt a state transition triggered by *event*.

        Raises:
            ValueError: if the transition is not allowed from the current state.
        """
        allowed = VALID_TRANSITIONS.get(self._state, {})
        if event not in allowed:
            raise ValueError(
                f"Invalid transition: cannot apply event '{event}' "
                f"in state '{self._state.value}'. "
                f"Allowed events: {list(allowed.keys())}"
            )

        previous = self._state
        self._state = allowed[event]
        record = TransitionRecord(previous, event, self._state)
        self._history.append(record)
        return record

    def force_error(self, reason: str = "error") -> TransitionRecord:
        """Force transition to ERROR state from any state."""
        previous = self._state
        self._state = AgentState.ERROR
        record = TransitionRecord(previous, reason, AgentState.ERROR)
        self._history.append(record)
        return record

    def reset(self) -> TransitionRecord:
        """Reset back to IDLE from COMPLETED or ERROR."""
        if self._state in (AgentState.COMPLETED, AgentState.ERROR):
            return self.transition("reset")
        # Force reset from any other state
        previous = self._state
        self._state = AgentState.IDLE
        record = TransitionRecord(previous, "force_reset", AgentState.IDLE)
        self._history.append(record)
        self._history.clear()
        return record

    def clear_history(self):
        """Clear all transition history."""
        self._history.clear()
