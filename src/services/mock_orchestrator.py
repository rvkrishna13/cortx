"""
Mock orchestrator for reasoning without Claude API
Uses simple query parsing to determine which tools to call

Supported Query Patterns:

Portfolio Analysis:
- "Analyze portfolio 1"
- "What's the risk of portfolio 2?"
- "Show me portfolio 3 metrics"
- "Calculate risk for portfolio 1 over 60 days"
- "Risk analysis for portfolio 2"
- "Portfolio 1 risk metrics"

Transactions:
- "Show transactions for user 5"
- "Get high risk transactions from last week"
- "Find transactions over $1000"
- "Show me user 2 transactions under $500"
- "Get low risk transactions from last month"
- "Recent transactions for user 1"
- "Find recent 5 transactions"
- "High risk transactions from last 7 days"

Market Data:
- "Get market summary for AAPL"
- "Show me GOOGL and TSLA prices"
- "Market data for AAPL, MSFT, and NVDA"
- "What's the price of Apple stock?"
- "Market summary for AAPL and GOOGL"
- "Get prices for TSLA, META, NVDA"

Combined Queries:
- "Analyze portfolio 1 and show market data"
- "Show high risk transactions and portfolio 2 risk"
- "Get portfolio 2 risk and AAPL market data"
"""
import re
import json
import time
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime, timedelta
from src.mcp.tools import list_tools, call_tool


class MockReasoningOrchestrator:
    """Mock orchestrator that parses queries and calls tools directly without Claude API"""
    
    def __init__(self, request_context: Optional[Any] = None):
        self.available_tools = list_tools()
        self.request_context = request_context
    
    async def reason(
        self,
        query: str,
        user_id: Optional[int] = None,
        auth_context: Optional[Dict[str, Any]] = None,
        include_thinking: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Mock reasoning method that parses queries and calls tools directly
        Now supports tool chaining: can use results from one tool to call another
        
        Args:
            query: Natural language query from user
            user_id: Default user ID (if not specified in query)
            auth_context: Authentication context for RBAC
            include_thinking: Whether to include thinking steps
        
        Yields:
            Dict with keys:
            - type: "thinking", "tool_call", "tool_result", "answer", "error", "done"
            - content: Relevant content
            - step_number: Step number
            - tool_name: Tool name (if type is tool_call or tool_result)
            - tool_arguments: Tool arguments (if type is tool_call)
            - tool_result: Tool result (if type is tool_result)
        """
        step_number = 0
        tool_calls_used = 0
        final_answer = ""
        conversation_turn = 0
        MAX_TURNS = 5  # Safety limit for chaining
        all_tool_results = []  # Accumulate all tool results across turns
        tools_executed = []  # Track which tools were executed for answer generation
        
        try:
            # Parse query to determine which tools to call
            query_lower = query.lower()
            
            # Yield initial thinking step
            if include_thinking:
                step_number += 1
                thinking_text = self._generate_thinking_text(query)
                yield {
                    "type": "thinking",
                    "content": thinking_text,
                    "step_number": step_number
                }
                await self._async_sleep(0.05)
            
            # CONVERSATION LOOP: Support tool chaining
            while conversation_turn < MAX_TURNS:
                conversation_turn += 1
                
                # Determine which tools to call based on query and previous results
                tools_to_call = self._parse_query_to_tools(
                    query, 
                    user_id, 
                    previous_results=all_tool_results if conversation_turn > 1 else None
                )
                
                # If no specific tools identified, provide helpful message (only on first turn)
                if not tools_to_call:
                    if conversation_turn == 1:
                        step_number += 1
                        yield {
                            "type": "thinking",
                            "content": "I'm not sure which tools to use for this query. Let me provide some guidance...",
                            "step_number": step_number
                        }
                        
                        final_answer = self._generate_help_message(query)
                        
                        # Stream final answer
                        for chunk in self._chunk_text(final_answer, chunk_size=50):
                            step_number += 1
                            yield {
                                "type": "answer",
                                "content": chunk,
                                "step_number": step_number
                            }
                            await self._async_sleep(0.01)
                        
                        yield {
                            "type": "done",
                            "content": "Query processed (no tools called)",
                            "step_number": step_number + 1,
                            "final_answer": final_answer,
                            "tool_calls_made": 0
                        }
                        return
                    else:
                        # No more tools needed, break out of loop
                        break
                
                # Execute tools for this turn
                turn_tool_results = []
                for tool_call in tools_to_call:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["arguments"]
                
                step_number += 1
                yield {
                    "type": "tool_call",
                    "content": f"Calling tool: {tool_name}",
                    "step_number": step_number,
                    "tool_name": tool_name
                }
                await self._async_sleep(0.02)
                
                # Execute the tool with timing
                tool_start_time = time.time()
                try:
                    tool_result = call_tool(
                        name=tool_name,
                        arguments=tool_args,
                        context=auth_context
                    )
                    
                    tool_duration_ms = (time.time() - tool_start_time) * 1000
                    
                    # Record tool call in RequestContext
                    if self.request_context:
                        self.request_context.record_tool_call(
                            tool_name=tool_name,
                            duration_ms=tool_duration_ms,
                            success=not tool_result.get("isError", False)
                        )
                    
                    # Format tool result (store for final answer, but don't send full data)
                    result_text = self._format_tool_result(tool_result)
                    
                    step_number += 1
                    # Only send minimal tool result info, not the full data
                    yield {
                        "type": "tool_result",
                        "content": f"Tool {tool_name} completed successfully",
                        "step_number": step_number,
                        "tool_name": tool_name,
                        "is_error": False
                    }
                    await self._async_sleep(0.02)
                    
                    turn_tool_results.append({
                        "tool_name": tool_name,
                        "result": result_text,
                        "is_error": tool_result.get("isError", False),
                        "arguments": tool_args
                    })
                    
                    tools_executed.append({"name": tool_name, "success": True})
                    tool_calls_used += 1
                    
                except Exception as e:
                    step_number += 1
                    tool_duration_ms = (time.time() - tool_start_time) * 1000
                    error_msg = f"Error: {str(e)}"
                    
                    # Record failed tool call
                    if self.request_context:
                        self.request_context.record_tool_call(
                            tool_name=tool_name,
                            duration_ms=tool_duration_ms,
                            success=False,
                            error=error_msg
                        )
                    
                    yield {
                        "type": "tool_result",
                        "content": f"Tool {tool_name} encountered an error",
                        "step_number": step_number,
                        "tool_name": tool_name,
                        "is_error": True
                    }
                    await self._async_sleep(0.02)
                    
                    turn_tool_results.append({
                        "tool_name": tool_name,
                        "result": error_msg,
                        "is_error": True,
                        "arguments": tool_args
                    })
                    
                    tools_executed.append({"name": tool_name, "success": False})
                
                # Add turn results to all results
                all_tool_results.extend(turn_tool_results)
                
                # Check if we need to chain more tools based on results
                if conversation_turn < MAX_TURNS:
                    next_tools = self._determine_chained_tools(query, turn_tool_results, all_tool_results)
                    if next_tools:
                        # More tools needed, update tools_to_call for next iteration
                        tools_to_call = next_tools
                        continue
                
                # No more chaining needed, break out
                break
            
            # Generate final answer from all tool results - ALWAYS send answer even if generation fails
            final_answer = ""
            try:
                if all_tool_results:
                    final_answer = self._generate_final_answer(query, all_tool_results)
                else:
                    # No tools executed, create a simple answer
                    final_answer = json.dumps({
                        "status": "success",
                        "query": query,
                        "tools_called": 0,
                        "results": {},
                        "message": "Query processed but no tools were called"
                    }, indent=2, ensure_ascii=False)
            except Exception as e:
                # If JSON formatting fails, fall back to simple text
                try:
                    final_answer = json.dumps({
                        "status": "error",
                        "query": query,
                        "tools_called": tool_calls_used,
                        "answer": f"Error formatting response: {str(e)}",
                        "message": "Analysis completed but response formatting failed",
                        "tools_executed": tools_executed
                    }, indent=2, ensure_ascii=False)
                except:
                    # Last resort: plain text
                    final_answer = json.dumps({
                        "status": "error",
                        "query": query,
                        "answer": f"Error: {str(e)}"
                    })
            
            # ALWAYS send answer event - no exceptions
            # Parse JSON string to object for cleaner client-side handling
            step_number += 1
            try:
                answer_content = json.loads(final_answer) if isinstance(final_answer, str) else final_answer
            except:
                # If parsing fails, use the string as-is
                answer_content = final_answer
            
            yield {
                "type": "answer",
                "content": answer_content,  # Send as dict/object, not string
                "step_number": step_number
            }
            
            # ALWAYS send done event with parsed JSON final_answer
            try:
                # Parse the JSON string back to dict for the done event
                final_answer_dict = json.loads(final_answer) if isinstance(final_answer, str) else final_answer
            except:
                # If parsing fails, use the string as-is
                final_answer_dict = {"raw": final_answer}
            
            yield {
                "type": "done",
                "content": "Reasoning complete",
                "step_number": step_number + 1,
                "final_answer": final_answer_dict,  # Send as dict, not string
                "tool_calls_made": tool_calls_used
            }
            
            return  # Explicit return to ensure we exit properly
            
        except Exception as e:
            # Record error in observability
            if self.request_context:
                try:
                    from src.observability.metrics import get_metrics_collector
                    metrics = get_metrics_collector()
                    metrics.record_error(
                        error_type="mock_orchestrator_error",
                        error_message=str(e),
                        context={"step_number": step_number, "query": query},
                        request_id=self.request_context.request_id if self.request_context else None
                    )
                except Exception:
                    pass  # Ignore metrics errors
            
            # Always send an answer event, even on error
            try:
                error_answer = json.dumps({
                    "status": "error",
                    "query": query,
                    "tools_called": tool_calls_used,
                    "answer": f"An error occurred while processing your query: {str(e)}",
                    "message": "Error during analysis",
                    "error": str(e)
                }, indent=2, ensure_ascii=False)
                
                step_number += 1
                yield {
                    "type": "answer",
                    "content": error_answer,
                    "step_number": step_number
                }
                
                yield {
                    "type": "done",
                    "content": "Reasoning complete with errors",
                    "step_number": step_number + 1,
                    "final_answer": error_answer,
                    "tool_calls_made": tool_calls_used
                }
            except Exception as format_error:
                # If even error formatting fails, send plain text error
                yield {
                    "type": "error",
                    "content": f"Error in mock reasoning orchestrator: {str(e)} (format error: {str(format_error)})",
                    "step_number": step_number + 1
                }
    
    def _parse_query_to_tools(
        self, 
        query: str, 
        default_user_id: Optional[int] = None,
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse query and determine which tools to call with what arguments
        Can use previous tool results for chaining
        
        Args:
            query: Original user query
            default_user_id: Default user ID if not in query
            previous_results: Results from previous tool calls (for chaining)
        
        Returns:
            List of tool calls with name and arguments
        """
        query_lower = query.lower()
        tools_to_call = []
        
        # If we have previous results, check if we need to chain
        if previous_results:
            # Extract data from previous results for chaining
            extracted_data = self._extract_data_from_results(previous_results)
            
            # If query asks for market data and we have portfolio symbols, use them
            if extracted_data.get("portfolio_symbols") and any(kw in query_lower for kw in ["market", "price", "holdings", "stock"]):
                symbols = extracted_data["portfolio_symbols"]
                if symbols:
                    # Check if we already have market data for these symbols
                    market_tools = [r for r in previous_results if r.get("tool_name") == "get_market_summary"]
                    if market_tools:
                        market_args = market_tools[-1].get("arguments", {})
                        existing_symbols = market_args.get("symbols", [])
                        if set(symbols) == set(existing_symbols):
                            # Already have market data, don't chain again
                            return []
                    
                    tools_to_call.append({
                        "name": "get_market_summary",
                        "arguments": {"symbols": symbols, "period": "day"}
                    })
                    return tools_to_call  # Return early, we're chaining
        
        # Normal parsing (first turn or no chaining needed)
        # Check for risk analysis queries
        if any(keyword in query_lower for keyword in ["risk", "portfolio", "analyze", "metrics", "volatility", "sharpe"]):
            portfolio_id = self._extract_portfolio_id(query)
            if portfolio_id:
                args = {"portfolio_id": portfolio_id}
                
                # Extract period if specified
                period = self._extract_period_days(query)
                if period:
                    args["period_days"] = period
                
                tools_to_call.append({
                    "name": "analyze_risk_metrics",
                    "arguments": args
                })
        
        # Check for transaction queries
        # Only call query_transactions if explicitly about transactions, not when it's about portfolio/market data
        # Exclude "show" when it's part of "show me market prices" or "show portfolio"
        is_portfolio_query = any(keyword in query_lower for keyword in ["portfolio", "risk", "analyze", "metrics"])
        is_market_query = any(keyword in query_lower for keyword in ["market", "price", "stock", "symbol", "holdings"])
        
        # Only add transaction query if explicitly about transactions AND not about portfolio/market
        transaction_keywords = ["transaction", "transactions", "trade", "trades", "spending", "purchase"]
        has_explicit_transaction_keyword = any(keyword in query_lower for keyword in transaction_keywords)
        
        # Check for patterns like "recent N transactions" or "find transactions"
        has_transaction_pattern = (
            ("recent" in query_lower and ("transaction" in query_lower or "transactions" in query_lower)) or
            ("find" in query_lower and ("transaction" in query_lower or "transactions" in query_lower))
        )
        
        # Only call query_transactions if:
        # 1. Explicitly about transactions, OR
        # 2. Has transaction pattern, AND
        # 3. NOT primarily about portfolio/market (unless explicitly asking for transactions)
        if (has_explicit_transaction_keyword or has_transaction_pattern) and not (is_portfolio_query and is_market_query and not has_explicit_transaction_keyword):
            tx_args = self._extract_transaction_args(query, default_user_id)
            tools_to_call.append({
                "name": "query_transactions",
                "arguments": tx_args
            })
        
        # Check for market data queries
        # BUT: If we have a portfolio query and it asks for "its holdings" or "holdings",
        # skip the initial market call - we'll chain it after getting portfolio symbols
        portfolio_id = self._extract_portfolio_id(query) if not previous_results else None
        is_portfolio_holdings_query = (
            portfolio_id is not None and 
            any(kw in query_lower for kw in ["holdings", "its holdings", "portfolio holdings"])
        )
        
        if any(keyword in query_lower for keyword in ["market", "price", "stock", "symbol", "trading", "volume", "performing"]):
            market_args = self._extract_market_args(query)
            # Only add market query if:
            # 1. Not a portfolio holdings query (will be chained), OR
            # 2. Has explicit symbols in query, OR
            # 3. Explicitly asks for market data without portfolio context
            if not is_portfolio_holdings_query or market_args.get("symbols"):
                if market_args or "market" in query_lower or "performing" in query_lower:
                    tools_to_call.append({
                        "name": "get_market_summary",
                        "arguments": market_args if market_args else {}
                    })
        
        return tools_to_call
    
    def _extract_portfolio_id(self, query: str) -> Optional[int]:
        """Extract portfolio ID from query"""
        patterns = [
            r'portfolio\s+(\d+)',
            r'portfolio\s+id\s+(\d+)',
            r'portfolio\s+#(\d+)',
            r'portfolio\s+number\s+(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def _extract_period_days(self, query: str) -> Optional[int]:
        """Extract time period in days from query"""
        # Look for explicit day mentions
        day_match = re.search(r'(\d+)\s*days?', query, re.IGNORECASE)
        if day_match:
            return int(day_match.group(1))
        
        # Common periods
        if "last week" in query.lower() or "past week" in query.lower():
            return 7
        elif "last month" in query.lower() or "past month" in query.lower():
            return 30
        elif "last year" in query.lower() or "past year" in query.lower():
            return 365
        
        return None
    
    def _extract_transaction_args(self, query: str, default_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Extract transaction query arguments from query"""
        args = {}
        
        # Extract user ID
        user_match = re.search(r'user\s+(\d+)', query, re.IGNORECASE)
        if user_match:
            args["user_id"] = int(user_match.group(1))
        elif default_user_id:
            args["user_id"] = default_user_id
        
        # Extract date ranges
        if "yesterday" in query.lower():
            yesterday = datetime.utcnow() - timedelta(days=1)
            args["start_date"] = yesterday.strftime("%Y-%m-%d")
            args["end_date"] = yesterday.strftime("%Y-%m-%d")
        elif "today" in query.lower():
            today = datetime.utcnow()
            args["start_date"] = today.strftime("%Y-%m-%d")
            args["end_date"] = today.strftime("%Y-%m-%d")
        elif "last week" in query.lower() or "past week" in query.lower():
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            args["start_date"] = start_date.strftime("%Y-%m-%d")
            args["end_date"] = end_date.strftime("%Y-%m-%d")
        elif "last month" in query.lower() or "past month" in query.lower():
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            args["start_date"] = start_date.strftime("%Y-%m-%d")
            args["end_date"] = end_date.strftime("%Y-%m-%d")
        
        # Extract amount ranges
        over_match = re.search(r'(?:over|above|more than)\s+\$?(\d+)', query, re.IGNORECASE)
        if over_match:
            args["min_amount"] = float(over_match.group(1))
        
        under_match = re.search(r'(?:under|below|less than)\s+\$?(\d+)', query, re.IGNORECASE)
        if under_match:
            args["max_amount"] = float(under_match.group(1))
        
        # Extract risk keywords
        if "high risk" in query.lower() or "high-risk" in query.lower() or "risky" in query.lower():
            args["min_risk_score"] = 0.7
        elif "low risk" in query.lower() or "low-risk" in query.lower() or "safe" in query.lower():
            args["max_risk_score"] = 0.3
        elif "medium risk" in query.lower() or "moderate risk" in query.lower():
            args["min_risk_score"] = 0.3
            args["max_risk_score"] = 0.7
        
        # Extract category
        category_keywords = ["groceries", "entertainment", "utilities", "transportation", "healthcare", "shopping", "dining", "travel", "education", "investment"]
        for category in category_keywords:
            if category in query.lower():
                args["category"] = category
                break
        
        # Extract limit - handle patterns like "recent 5", "5 transactions", "top 10", "first 3"
        limit_match = re.search(r'(?:limit|top|first|recent)\s+(\d+)', query, re.IGNORECASE)
        if limit_match:
            args["limit"] = int(limit_match.group(1))
        else:
            # Also check for "N transactions" pattern (e.g., "5 transactions")
            num_transactions_match = re.search(r'(\d+)\s+transactions?', query, re.IGNORECASE)
            if num_transactions_match:
                args["limit"] = int(num_transactions_match.group(1))
        
        # If "recent" is mentioned without specific date, default to last 30 days
        if "recent" in query.lower() and "start_date" not in args:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            args["start_date"] = start_date.strftime("%Y-%m-%d")
            args["end_date"] = end_date.strftime("%Y-%m-%d")
        
        return args
    
    def _extract_market_args(self, query: str) -> Dict[str, Any]:
        """Extract market summary arguments from query"""
        args = {}
        
        # Extract symbols (e.g., "AAPL", "GOOGL and MSFT")
        # Look for 2-5 uppercase letters that are likely stock symbols
        symbol_pattern = r'\b([A-Z]{2,5})\b'
        potential_symbols = re.findall(symbol_pattern, query)
        
        if potential_symbols:
            # Filter out common words that might match the pattern
            common_words = {
                "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT", 
                "ARE", "WAS", "WERE", "BEEN", "HAVE", "HAS", "HAD",
                "BUT", "NOT", "CAN", "WILL", "ALL", "YOU", "YOUR"
            }
            symbols = [s for s in potential_symbols if s not in common_words]
            
            # Only include if we're in a market context
            if symbols and any(kw in query.lower() for kw in ["market", "stock", "price", "symbol", "trading"]):
                args["symbols"] = symbols[:10]  # Limit to 10 symbols
        
        # Extract period
        if "hour" in query.lower():
            args["period"] = "hour"
        elif "week" in query.lower():
            args["period"] = "week"
        elif "month" in query.lower():
            args["period"] = "month"
        else:
            args["period"] = "day"
        
        return args
    
    def _extract_data_from_results(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract useful data from tool results for chaining
        
        Returns:
            Dict with extracted data like:
            - portfolio_symbols: List of symbols from portfolio analysis
            - transaction_user_ids: List of user IDs from transactions
            - market_symbols: List of symbols from market data
        """
        extracted = {
            "portfolio_symbols": [],
            "transaction_user_ids": [],
            "market_symbols": []
        }
        
        for result in tool_results:
            tool_name = result.get("tool_name")
            result_text = result.get("result", "")
            
            if tool_name == "analyze_risk_metrics" and not result.get("is_error"):
                # Try to extract symbols from portfolio analysis
                # The portfolio data might be in the result text or we need to query it
                symbols = self._extract_symbols_from_portfolio_result(result_text)
                if symbols:
                    extracted["portfolio_symbols"] = symbols
            
            elif tool_name == "query_transactions" and not result.get("is_error"):
                # Extract user IDs from transaction results
                user_ids = self._extract_user_ids_from_transactions(result_text)
                if user_ids:
                    extracted["transaction_user_ids"] = user_ids
            
            elif tool_name == "get_market_summary" and not result.get("is_error"):
                # Extract symbols from market data results
                symbols = self._extract_symbols_from_market_result(result_text)
                if symbols:
                    extracted["market_symbols"] = symbols
        
        return extracted
    
    def _extract_symbols_from_portfolio_result(self, result_text: str) -> List[str]:
        """
        Extract stock symbols from portfolio risk analysis result
        
        The portfolio result doesn't directly show symbols, so we need to:
        1. Extract portfolio_id from the result text
        2. Query the database to get portfolio assets
        3. Extract symbols from assets
        """
        import re
        
        # Extract portfolio ID from result text
        # Format: "Portfolio 1 Risk Analysis:"
        portfolio_match = re.search(r'Portfolio\s+(\d+)', result_text, re.IGNORECASE)
        if not portfolio_match:
            return []
        
        portfolio_id = int(portfolio_match.group(1))
        
        # Query database to get portfolio assets
        try:
            from src.database.connection import database
            from src.database.queries import get_portfolio_by_id
            
            db = database.get_session()
            try:
                portfolio = get_portfolio_by_id(db, portfolio_id)
                if portfolio and portfolio.assets:
                    import json
                    assets = json.loads(portfolio.assets) if isinstance(portfolio.assets, str) else portfolio.assets
                    if isinstance(assets, dict):
                        return list(assets.keys())
            finally:
                db.close()
        except Exception:
            # If database query fails, return empty list
            # This is expected in some test scenarios
            pass
        
        return []
    
    def _extract_user_ids_from_transactions(self, result_text: str) -> List[int]:
        """Extract user IDs from transaction result text"""
        import re
        user_ids = []
        # Pattern: "User: 7" or "user_id: 5"
        matches = re.findall(r'(?:User|user_id):\s*(\d+)', result_text, re.IGNORECASE)
        for match in matches:
            try:
                user_ids.append(int(match))
            except ValueError:
                continue
        return list(set(user_ids))  # Remove duplicates
    
    def _extract_symbols_from_market_result(self, result_text: str) -> List[str]:
        """Extract symbols from market data result text"""
        import re
        symbols = []
        # Pattern: Symbol names at start of lines (uppercase, 2-5 chars)
        lines = result_text.split('\n')
        for line in lines:
            # Match lines like "AAPL:" or "GOOGL:"
            match = re.match(r'^([A-Z]{2,5}):', line.strip())
            if match:
                symbol = match.group(1)
                # Filter out common words
                if symbol not in ["THE", "AND", "FOR", "WITH", "FROM"]:
                    symbols.append(symbol)
        return list(set(symbols))  # Remove duplicates
    
    def _determine_chained_tools(
        self, 
        query: str, 
        current_turn_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Determine if we need to chain more tools based on current results and query
        
        Returns:
            List of additional tool calls needed, or empty list if no chaining needed
        """
        query_lower = query.lower()
        next_tools = []
        
        # Check if we have portfolio analysis results and query asks for market data
        portfolio_tools = [r for r in current_turn_results if r.get("tool_name") == "analyze_risk_metrics"]
        if portfolio_tools and any(kw in query_lower for kw in ["market", "price", "holdings", "stock", "symbol"]):
            # Extract symbols from portfolio
            extracted = self._extract_data_from_results(all_results)
            symbols = extracted.get("portfolio_symbols", [])
            
            # Check if we already called get_market_summary with these symbols
            market_tools = [r for r in all_results if r.get("tool_name") == "get_market_summary"]
            if market_tools:
                # Check if we already have market data for these symbols
                market_args = market_tools[-1].get("arguments", {})
                existing_symbols = market_args.get("symbols", [])
                if set(symbols) == set(existing_symbols):
                    # Already have market data for these symbols, no need to chain
                    return []
            
            if symbols:
                # Chain: Get market data for portfolio symbols
                next_tools.append({
                    "name": "get_market_summary",
                    "arguments": {"symbols": symbols, "period": "day"}
                })
        
        return next_tools
    
    def _generate_thinking_text(self, query: str) -> str:
        """Generate thinking text based on query"""
        thinking = f"Analyzing your query: '{query}'\n\n"
        
        query_lower = query.lower()
        
        if "portfolio" in query_lower or "risk" in query_lower:
            thinking += "I'll analyze the portfolio risk metrics for you.\n"
        
        if "transaction" in query_lower:
            thinking += "I'll query the transaction database with your filters.\n"
        
        if "market" in query_lower or "price" in query_lower or "stock" in query_lower:
            thinking += "I'll retrieve market data and price information.\n"
        
        thinking += "\nLet me call the appropriate tools to get this information..."
        
        return thinking
    
    def _format_tool_result(self, tool_result: Dict[str, Any]) -> str:
        """Format tool result for display"""
        if tool_result.get("isError"):
            content_items = tool_result.get("content", [])
            if content_items:
                return content_items[0].get("text", "Unknown error")
            return "Unknown error occurred"
        
        content_items = tool_result.get("content", [])
        result_parts = []
        for item in content_items:
            if item.get("type") == "text":
                result_parts.append(item.get("text", ""))
        
        return "\n".join(result_parts) if result_parts else "No results"
    
    def _generate_final_answer(self, query: str, tool_results: List[Dict[str, Any]]) -> str:
        """Generate structured final answer from tool results as JSON"""
        import json
        
        has_errors = False
        has_success = False
        summary_data = {}
        errors = []
        
        for tr in tool_results:
            tool_name = tr['tool_name']
            result = tr['result']
            is_error = tr.get('is_error', False)
            
            if is_error:
                has_errors = True
                errors.append({
                    "tool": tool_name,
                    "error": result
                })
            else:
                has_success = True
                # Generate structured summary based on tool type
                try:
                    summary = self._summarize_tool_result_structured(tool_name, result)
                    summary_data[tool_name] = summary
                except Exception as e:
                    # If structured parsing fails, use simple text summary
                    summary_data[tool_name] = {
                        "type": "text",
                        "content": result[:500] if len(result) > 500 else result,
                        "parse_error": str(e)
                    }
        
        # Extract portfolio ID from query for context
        portfolio_id = self._extract_portfolio_id(query)
        
        # Build final answer structure
        final_answer = {
            "status": "success" if has_success and not has_errors else "partial" if has_success else "error",
            "query": query,
            "tools_called": len(tool_results),
            "results": summary_data,
            "message": self._get_status_message(has_success, has_errors, len(tool_results))
        }
        
        # Add portfolio context if available
        if portfolio_id:
            final_answer["portfolio_id"] = portfolio_id
        
        if errors:
            final_answer["errors"] = errors
        
        # Return as formatted JSON string
        return json.dumps(final_answer, indent=2, ensure_ascii=False)
    
    def _get_status_message(self, has_success: bool, has_errors: bool, tool_count: int) -> str:
        """Get status message based on results"""
        if has_success and not has_errors:
            return f"Analysis complete. Retrieved data from {tool_count} tool(s)."
        elif has_success and has_errors:
            return f"Analysis complete with some errors. Partial data retrieved from {tool_count} tool(s)."
        else:
            return f"Unable to retrieve data. All {tool_count} tool(s) encountered errors."
    
    def _summarize_tool_result(self, tool_name: str, result: str) -> str:
        """Generate concise summary of tool result instead of raw data dump (legacy text format)"""
        if tool_name == "query_transactions":
            # Count transactions and show summary
            lines = result.strip().split('\n')
            transaction_count = len([l for l in lines if l.startswith('Transaction ID:')])
            
            if transaction_count == 0:
                return "📊 Transactions: No transactions found matching the criteria.\n\n"
            
            # Show first 3 transactions as examples
            example_lines = [l for l in lines if l.startswith('Transaction ID:')][:3]
            examples = '\n'.join(example_lines)
            
            summary = f"📊 Transactions: Found {transaction_count} transaction(s).\n"
            if transaction_count > 3:
                summary += f"Showing first 3 examples:\n{examples}\n"
                summary += f"... and {transaction_count - 3} more transaction(s).\n\n"
            else:
                summary += f"{examples}\n\n"
            
            return summary
        
        elif tool_name == "analyze_risk_metrics":
            # Risk metrics are already well-formatted, return as-is
            return f"📊 Risk Analysis:\n{result}\n\n"
        
        elif tool_name == "get_market_summary":
            # Count symbols and show summary
            lines = result.strip().split('\n')
            symbol_count = len([l for l in lines if ':' in l and not l.startswith('Market Summary') and not l.startswith('Aggregated')])
            
            if symbol_count == 0:
                return "📊 Market Data: No market data found.\n\n"
            
            # Show first 5 symbols
            symbol_lines = [l for l in lines if ':' in l and not l.startswith('Market Summary') and not l.startswith('Aggregated')][:5]
            examples = '\n'.join(symbol_lines)
            
            summary = f"📊 Market Data: Retrieved data for {symbol_count} symbol(s).\n"
            if symbol_count > 5:
                summary += f"Showing first 5:\n{examples}\n"
                summary += f"... and {symbol_count - 5} more symbol(s).\n\n"
            else:
                summary += f"{examples}\n\n"
            
            # Include aggregated data if present
            agg_lines = [l for l in lines if l.startswith('Aggregated') or 'Period:' in l]
            if agg_lines:
                summary += '\n'.join(agg_lines) + '\n\n'
            
            return summary
        
        else:
            # For unknown tools, return first 500 chars as summary
            if len(result) > 500:
                return f"📊 {tool_name}:\n{result[:500]}...\n(truncated)\n\n"
            return f"📊 {tool_name}:\n{result}\n\n"
    
    def _summarize_tool_result_structured(self, tool_name: str, result: str) -> Dict[str, Any]:
        """Generate structured summary of tool result as dictionary"""
        if tool_name == "query_transactions":
            lines = result.strip().split('\n')
            transaction_lines = [l for l in lines if l.startswith('Transaction ID:')]
            transaction_count = len(transaction_lines)
            
            if transaction_count == 0:
                return {
                    "type": "transactions",
                    "count": 0,
                    "message": "No transactions found matching the criteria"
                }
            
            # Parse example transactions
            examples = []
            for line in transaction_lines[:3]:
                # Parse: "Transaction ID: 30, User: 7, Amount: 2995.48 GBP, Category: Options Trade, Risk: 1.0, Date: 2025-12-28T20:21:49.834332"
                parts = line.replace('Transaction ID: ', '').split(', ')
                tx_data = {}
                for part in parts:
                    if ':' in part:
                        key, value = part.split(': ', 1)
                        tx_data[key.lower().replace(' ', '_')] = value
                examples.append(tx_data)
            
            summary = {
                "type": "transactions",
                "count": transaction_count,
                "examples": examples
            }
            
            if transaction_count > 3:
                summary["remaining"] = transaction_count - 3
            
            return summary
        
        elif tool_name == "analyze_risk_metrics":
            # Try to parse risk metrics into structured format
            lines = result.strip().split('\n')
            metrics = {}
            
            # Extract portfolio ID from result text
            import re
            portfolio_match = re.search(r'Portfolio\s+(\d+)', result, re.IGNORECASE)
            portfolio_id_in_result = int(portfolio_match.group(1)) if portfolio_match else None
            
            for line in lines:
                if ':' in line and not line.startswith('Portfolio'):
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    # Try to convert numeric values
                    try:
                        if '.' in value:
                            metrics[key] = float(value.replace(',', '').replace('$', '').replace('%', ''))
                        else:
                            metrics[key] = int(value.replace(',', ''))
                    except:
                        metrics[key] = value
            
            result_dict = {
                "type": "risk_metrics",
                "metrics": metrics,
                "raw": result
            }
            
            # Add portfolio ID if found
            if portfolio_id_in_result:
                result_dict["portfolio_id"] = portfolio_id_in_result
            
            return result_dict
        
        elif tool_name == "get_market_summary":
            lines = result.strip().split('\n')
            symbol_data = {}
            symbol_count = 0
            
            current_symbol = None
            for line in lines:
                if ':' in line and not line.startswith('Market Summary') and not line.startswith('Aggregated'):
                    if not line.startswith('  '):  # New symbol
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            current_symbol = parts[0].strip()
                            symbol_data[current_symbol] = {}
                            symbol_count += 1
                    else:  # Symbol data
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2 and current_symbol:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            symbol_data[current_symbol][key] = value
            
            summary = {
                "type": "market_data",
                "symbol_count": symbol_count,
                "symbols": {k: v for k, v in list(symbol_data.items())[:5]}
            }
            
            if symbol_count > 5:
                summary["remaining_symbols"] = symbol_count - 5
            
            return summary
        
        else:
            # For unknown tools, return text summary
            return {
                "type": "text",
                "content": result[:500] + "..." if len(result) > 500 else result
            }
    
    def _generate_help_message(self, query: str) -> str:
        """Generate helpful message when no tools match"""
        help_text = f"I couldn't determine which tools to use for: '{query}'\n\n"
        help_text += "Here are some example queries I can help with:\n\n"
        help_text += "📊 Portfolio Analysis:\n"
        help_text += "  • 'Analyze portfolio 1'\n"
        help_text += "  • 'What's the risk of portfolio 2?'\n"
        help_text += "  • 'Calculate risk for portfolio 1 over 60 days'\n\n"
        help_text += "💳 Transactions:\n"
        help_text += "  • 'Show transactions for user 5'\n"
        help_text += "  • 'Get high risk transactions from last week'\n"
        help_text += "  • 'Find transactions over $1000'\n\n"
        help_text += "📈 Market Data:\n"
        help_text += "  • 'Get market summary for AAPL'\n"
        help_text += "  • 'Show me GOOGL and TSLA prices'\n"
        help_text += "  • 'Market data for tech stocks'\n\n"
        help_text += "Try rephrasing your query using these patterns!"
        
        return help_text
    
    def _chunk_text(self, text: str, chunk_size: int = 50) -> List[str]:
        """Split text into chunks for streaming simulation"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    async def _async_sleep(self, seconds: float):
        """Async sleep helper for streaming simulation"""
        import asyncio
        await asyncio.sleep(seconds)