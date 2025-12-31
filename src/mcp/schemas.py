"""
MCP tool input/output schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryTransactionsInput(BaseModel):
    """Input schema for query_transactions tool"""
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    category: Optional[str] = Field(None, description="Filter by transaction category")
    currency: Optional[str] = Field(None, description="Filter by currency (USD, EUR, etc.)")
    start_date: Optional[str] = Field(None, description="Start date in ISO format (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date in ISO format (YYYY-MM-DD)")
    min_amount: Optional[float] = Field(None, description="Minimum transaction amount")
    max_amount: Optional[float] = Field(None, description="Maximum transaction amount")
    min_risk_score: Optional[float] = Field(None, description="Minimum risk score (0.0-1.0)")
    max_risk_score: Optional[float] = Field(None, description="Maximum risk score (0.0-1.0)")
    limit: Optional[int] = Field(100, description="Maximum number of results to return")


class AnalyzeRiskMetricsInput(BaseModel):
    """Input schema for analyze_risk_metrics tool"""
    portfolio_id: Optional[int] = Field(None, description="Portfolio ID to analyze")
    user_id: Optional[int] = Field(None, description="User ID to analyze all portfolios")
    period_days: Optional[int] = Field(30, description="Number of days to analyze")


class GetMarketSummaryInput(BaseModel):
    """Input schema for get_market_summary tool"""
    symbols: Optional[List[str]] = Field(None, description="List of symbols to include (default: all)")
    period: Optional[str] = Field("day", description="Aggregation period: hour, day, week, month")


class ToolOutput(BaseModel):
    """Standard MCP tool output"""
    content: List[Dict[str, Any]]
    isError: bool = False

