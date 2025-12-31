"""
Request/response schemas for reasoning endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ReasoningRequest(BaseModel):
    """Request schema for reasoning endpoint"""
    query: str = Field(..., description="Natural language query about financial data")
    user_id: Optional[int] = Field(None, description="User ID for context (optional)")
    include_thinking: bool = Field(True, description="Include reasoning steps in response")


class ReasoningStep(BaseModel):
    """Schema for a reasoning step"""
    step_number: int
    type: str = Field(..., description="Type: thinking, tool_call, result")
    content: str
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None


class ReasoningResponse(BaseModel):
    """Response schema for reasoning endpoint"""
    query: str
    answer: str
    steps: List[ReasoningStep] = []
    tool_calls_used: int = 0
    tokens_used: Optional[int] = None
    execution_time_ms: Optional[float] = None

