"""
MCP tool definitions and implementations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from src.database.connection import database
from src.database.queries import (
    get_latest_prices_dict,
    get_transactions_with_filters,
    get_transaction_risk_distribution,
    get_portfolio_by_id,
    get_user_portfolios,
    get_portfolio_transaction_history,
    aggregate_by_symbol,
    aggregate_by_time_period,
    get_latest_market_data
)
from src.mcp.schemas import (
    QueryTransactionsInput,
    AnalyzeRiskMetricsInput,
    GetMarketSummaryInput
)
from src.services.risk_analyzer import RiskAnalyzer
from src.utils.exceptions import (
    MCPToolError,
    DatabaseConnectionError,
    DatabaseQueryError,
    ValidationError,
    NotFoundError
)
from src.auth.rbac import require_role, require_permission, enforce_user_access, check_user_access
from src.auth.permissions import Role, Permission


def list_tools() -> List[Dict[str, Any]]:
    """List all available MCP tools"""
    return [
        {
            "name": "query_transactions",
            "description": "Fetch transaction data with various filters (user, category, date range, amount, risk score)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "Filter by user ID"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by transaction category"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Filter by currency (USD, EUR, etc.)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO format (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO format (YYYY-MM-DD)"
                    },
                    "min_amount": {
                        "type": "number",
                        "description": "Minimum transaction amount"
                    },
                    "max_amount": {
                        "type": "number",
                        "description": "Maximum transaction amount"
                    },
                    "min_risk_score": {
                        "type": "number",
                        "description": "Minimum risk score (0.0-1.0)"
                    },
                    "max_risk_score": {
                        "type": "number",
                        "description": "Maximum risk score (0.0-1.0)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 100
                    }
                }
            }
        },
        {
            "name": "analyze_risk_metrics",
            "description": "Calculate comprehensive risk indicators for a portfolio including volatility, Sharpe ratio, Value at Risk (VaR), average returns, and risk classification. Analyzes both transaction history and portfolio holdings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "integer",
                        "description": "Portfolio ID to analyze"
                    },
                    "user_id": {
                        "type": "integer",
                        "description": "User ID to analyze all portfolios"
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 30
                    }
                }
            }
        },
        {
            "name": "get_market_summary",
            "description": "Retrieve aggregated market data including prices, volumes, and trends for specified symbols",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of symbols to include (default: all)"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["hour", "day", "week", "month"],
                        "description": "Aggregation period",
                        "default": "day"
                    }
                }
            }
        }
    ]


def call_tool(name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute an MCP tool by name with given arguments
    
    Args:
        name: Tool name to execute
        arguments: Tool arguments (clean, without auth context)
        context: Optional authentication context containing token/user info
    
    Returns:
        Dict with 'content' (list of result dicts) and 'isError' (bool)
    """
    db = None
    try:
        # Get database session
        db_gen = database.get_session()
        db = next(db_gen)
        
        # Pass context separately, not mixed with arguments
        if name == "query_transactions":
            return _query_transactions(db, arguments, context=context)
        elif name == "analyze_risk_metrics":
            return _analyze_risk_metrics(db, arguments, context=context)
        elif name == "get_market_summary":
            return _get_market_summary(db, arguments, context=context)
        else:
            raise MCPToolError(name, f"Unknown tool: {name}")
    
    except (DatabaseConnectionError, DatabaseQueryError) as e:
        return {
            "content": [{"type": "text", "text": f"Database error in tool '{name}': {e.message}"}],
            "isError": True
        }
    except ValidationError as e:
        return {
            "content": [{"type": "text", "text": f"Validation error in tool '{name}': {e.message}"}],
            "isError": True
        }
    except NotFoundError as e:
        return {
            "content": [{"type": "text", "text": f"Resource not found in tool '{name}': {e.message}"}],
            "isError": True
        }
    except MCPToolError as e:
        return {
            "content": [{"type": "text", "text": f"MCP tool error: {e.message}"}],
            "isError": True
        }
    except OperationalError as e:
        return {
            "content": [{"type": "text", "text": f"Database connection failed in tool '{name}': {str(e)}"}],
            "isError": True
        }
    except SQLAlchemyError as e:
        return {
            "content": [{"type": "text", "text": f"Database error in tool '{name}': {str(e)}"}],
            "isError": True
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Unexpected error in tool '{name}': {str(e)}"}],
            "isError": True
        }
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass  # Ignore errors during cleanup


@require_permission(Permission.READ_TRANSACTIONS, Permission.READ_USER_TRANSACTIONS)
def _query_transactions(db: Session, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Execute query_transactions tool
    
    RBAC Rules:
    - Admin: Can query all transactions
    - Analyst: Can only query transactions for assigned users (their own user_id)
    - Viewer: No access
    """
    try:
        # Parse input (clean arguments, no context mixing)
        input_data = QueryTransactionsInput(**arguments)
        
        # Get user info from kwargs (added by decorator)
        current_user = kwargs.get("current_user", {})
        user_roles = kwargs.get("user_roles", [])
        
        # Enforce user access if user_id is specified
        if input_data.user_id is not None:
            # Admin can access all, analyst can only access their own
            if Role.ADMIN not in user_roles:
                enforce_user_access(input_data.user_id, current_user, user_roles)
        
        # Parse dates if provided
        start_date = None
        end_date = None
        if input_data.start_date:
            try:
                start_date = datetime.fromisoformat(input_data.start_date)
            except ValueError as e:
                raise ValidationError(f"Invalid start_date format: {input_data.start_date}. Use ISO format (YYYY-MM-DD)", "start_date") from e
        
        if input_data.end_date:
            try:
                end_date = datetime.fromisoformat(input_data.end_date)
            except ValueError as e:
                raise ValidationError(f"Invalid end_date format: {input_data.end_date}. Use ISO format (YYYY-MM-DD)", "end_date") from e
        
        # Validate risk scores
        if input_data.min_risk_score is not None and (input_data.min_risk_score < 0 or input_data.min_risk_score > 1):
            raise ValidationError("min_risk_score must be between 0.0 and 1.0", "min_risk_score")
        if input_data.max_risk_score is not None and (input_data.max_risk_score < 0 or input_data.max_risk_score > 1):
            raise ValidationError("max_risk_score must be between 0.0 and 1.0", "max_risk_score")
        
        # Query transactions
        transactions = get_transactions_with_filters(
            db=db,
            user_id=input_data.user_id,
            category=input_data.category,
            currency=input_data.currency,
            start_date=start_date,
            end_date=end_date,
            min_amount=input_data.min_amount,
            max_amount=input_data.max_amount,
            min_risk_score=input_data.min_risk_score,
            max_risk_score=input_data.max_risk_score,
            limit=input_data.limit or 100
        )
        
        # Format results
        results = []
        for tx in transactions:
            results.append({
                "type": "text",
                "text": f"Transaction ID: {tx.id}, User: {tx.user_id}, Amount: {tx.amount} {tx.currency}, "
                       f"Category: {tx.category}, Risk: {tx.risk_score}, Date: {tx.timestamp.isoformat()}"
            })
        
        if not results:
            results.append({
                "type": "text",
                "text": "No transactions found matching the criteria"
            })
        
        return {
            "content": results,
            "isError": False
        }
    
    except (ValidationError, DatabaseConnectionError, DatabaseQueryError):
        # Re-raise custom exceptions to be handled by call_tool
        raise
    except Exception as e:
        raise MCPToolError("query_transactions", f"Unexpected error: {str(e)}", e) from e


@require_permission(Permission.READ_RISK_METRICS)
def _analyze_risk_metrics(db: Session, arguments: Dict[str, Any], context=None, **kwargs):
    input_data = AnalyzeRiskMetricsInput(**arguments)
    
    # Get portfolio
    portfolio = get_portfolio_by_id(db, input_data.portfolio_id)
    if not portfolio:
        return {"content": [{"type": "text", "text": "Portfolio not found"}], "isError": True}
    
    # Get transactions
    # If period_days is not specified, get ALL transactions (no date filter)
    if input_data.period_days:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=input_data.period_days)
        transactions = get_portfolio_transaction_history(db, input_data.portfolio_id, start_date, end_date)
        time_period_days = input_data.period_days
    else:
        # No period specified - get all transactions for the portfolio
        transactions = get_portfolio_transaction_history(db, input_data.portfolio_id, None, None)
        # Calculate period from actual transaction dates
        if transactions:
            time_period_days = (datetime.utcnow() - min(t.timestamp for t in transactions)).days or 1
        else:
            time_period_days = 30  # Default if no transactions
    
    # Get current prices for portfolio holdings
    import json
    assets = json.loads(portfolio.assets) if isinstance(portfolio.assets, str) else portfolio.assets
    symbols = list(assets.keys())
    current_prices = get_latest_prices_dict(db, symbols)  # Returns {symbol: price}
    
    # Calculate risk metrics using analytics
    analyzer = RiskAnalyzer()
    metrics = analyzer.calculate_all_metrics(
        portfolio=portfolio.__dict__,
        transactions=[t.__dict__ for t in transactions],
        current_prices=current_prices,
        time_period_days=time_period_days
    )
    
    if "error" in metrics:
        return {"content": [{"type": "text", "text": metrics["error"]}], "isError": True}
    
    # Format result
    period_text = f"{time_period_days} days" if input_data.period_days else "all available transactions"
    result_text = f"""Portfolio {input_data.portfolio_id} Risk Analysis:

        Portfolio Value: ${metrics['portfolio_value']:,.2f}
        Time Period: {period_text}

        Risk Metrics:
        - Volatility: {metrics['volatility']:.2%} (annualized)
        - Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
        - Value at Risk (95%): ${metrics['value_at_risk_95']:,.2f}
        - Average Return: {metrics['average_return']:.2%} (annualized)
        - Maximum Drawdown: {metrics['max_drawdown']:.2%}

        Overall Risk Level: {metrics['risk_level']}
        """
    
    return {"content": [{"type": "text", "text": result_text}], "isError": False}

@require_permission(Permission.READ_MARKET_DATA)
def _get_market_summary(db: Session, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Execute get_market_summary tool
    
    RBAC Rules:
    - All roles (viewer, analyst, admin): Can access public market data
    """
    try:
        # Parse input (clean arguments, no context mixing)
        input_data = GetMarketSummaryInput(**arguments)
        
        # Get aggregated data
        if input_data.symbols:
            # Aggregate specific symbols
            aggregated = aggregate_by_symbol(db)
            aggregated = [a for a in aggregated if a['symbol'] in input_data.symbols]
        else:
            # Aggregate all symbols
            aggregated = aggregate_by_symbol(db)
        
        # Get latest prices
        symbols_list = [a['symbol'] for a in aggregated] if input_data.symbols else None
        latest_data = get_latest_market_data(db, symbols=symbols_list)
        
        # Create price map
        price_map = {data.symbol: data.price for data in latest_data}
        
        # Format results
        results = []
        summary_text = "Market Summary:\n\n"
        
        for agg in aggregated[:20]:  # Limit to top 20 for readability
            symbol = agg['symbol']
            current_price = price_map.get(symbol, agg['avg_price'])
            summary_text += (
                f"{symbol}:\n"
                f"  Current Price: ${current_price:.2f}\n"
                f"  Average Price: ${agg['avg_price']:.2f}\n"
                f"  Price Range: ${agg['min_price']:.2f} - ${agg['max_price']:.2f}\n"
                f"  Average Volume: {agg['avg_volume']:,.0f}\n"
                f"  Data Points: {agg['count']}\n\n"
            )
        
        results.append({
            "type": "text",
            "text": summary_text
        })
        
        # Add aggregated time period data if requested
        if input_data.period and input_data.period != "day":
            # aggregate_by_time_period accepts symbol (singular), not symbols
            # If specific symbols requested, use first one; otherwise aggregate all
            symbol_filter = input_data.symbols[0] if input_data.symbols and len(input_data.symbols) > 0 else None
            time_agg = aggregate_by_time_period(
                db,
                period=input_data.period,
                symbol=symbol_filter
            )
            if time_agg:
                time_text = f"\nAggregated by {input_data.period}:\n"
                for period_data in time_agg[:10]:
                    time_text += (
                        f"Period: {period_data['period']}\n"
                        f"  Avg Price: ${period_data['avg_price']:.2f}\n"
                        f"  Total Volume: {period_data['total_volume']:,.0f}\n\n"
                    )
                results.append({
                    "type": "text",
                    "text": time_text
                })
        
        return {
            "content": results,
            "isError": False
        }
    
    except (ValidationError, DatabaseConnectionError, DatabaseQueryError):
        # Re-raise custom exceptions to be handled by call_tool
        raise
    except Exception as e:
        raise MCPToolError("get_market_summary", f"Unexpected error: {str(e)}", e) from e

