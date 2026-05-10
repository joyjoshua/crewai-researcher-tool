"""
Event models — structured events emitted by callbacks during crew execution.
These are serialised to JSON and pushed to the SSE stream.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_THOUGHT = "agent_thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_COMPLETE = "agent_complete"
    TASK_COMPLETE = "task_complete"
    FLOW_COMPLETE = "flow_complete"
    ERROR = "error"


class AgentEvent(BaseModel):
    type: EventType
    agent: str = ""
    task: str = ""
    message: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
