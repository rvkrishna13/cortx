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
            
            # Determine which tools to call based on query
            tools_to_call = self._parse_query_to_tools(query, user_id)
            
            # If no specific tools identified, provide helpful message
            if not tools_to_call:
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
            
            # Execute tools
            tool_results = []
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
                    
                    tool_results.append({
                        "tool_name": tool_name,
                        "result": result_text,
                        "is_error": tool_result.get("isError", False)
                    })
                    
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
                    
                    tool_results.append({
                        "tool_name": tool_name,
                        "result": error_msg,
                        "is_error": True
                    })
            
            # Generate final answer from tool results
            final_answer = self._generate_final_answer(query, tool_results)
            
            # Send single final answer event (not chunked)
            step_number += 1
            yield {
                "type": "answer",
                "content": final_answer,
                "step_number": step_number
            }
            
            # Final done event
            yield {
                "type": "done",
                "content": "Reasoning complete",
                "step_number": step_number + 1,
                "final_answer": final_answer,
                "tool_calls_made": tool_calls_used
            }
            
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
            
            yield {
                "type": "error",
                "content": f"Error in mock reasoning orchestrator: {str(e)}",
                "step_number": step_number + 1
            }
    
    def _parse_query_to_tools(self, query: str, default_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Parse query and determine which tools to call with what arguments
        
        Returns:
            List of tool calls with name and arguments
        """
        query_lower = query.lower()
        tools_to_call = []
        
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
        transaction_keywords = ["transaction", "transactions", "trade", "trades", "spending", "purchase", "recent", "find", "show", "get"]
        has_transaction_keyword = any(keyword in query_lower for keyword in transaction_keywords)
        # Also check for patterns like "recent N transactions" or "find transactions"
        has_transaction_pattern = (
            ("recent" in query_lower and ("transaction" in query_lower or "transactions" in query_lower)) or
            ("find" in query_lower and ("transaction" in query_lower or "transactions" in query_lower)) or
            ("show" in query_lower and ("transaction" in query_lower or "transactions" in query_lower))
        )
        
        if has_transaction_keyword or has_transaction_pattern:
            tx_args = self._extract_transaction_args(query, default_user_id)
            # Always call query_transactions if transaction keywords are present
            tools_to_call.append({
                "name": "query_transactions",
                "arguments": tx_args
            })
        
        # Check for market data queries
        if any(keyword in query_lower for keyword in ["market", "price", "stock", "symbol", "trading", "volume"]):
            market_args = self._extract_market_args(query)
            if market_args or "market" in query_lower:
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
        """Generate concise final answer from tool results - summaries only, not raw data"""
        answer_parts = []
        
        has_errors = False
        has_success = False
        
        for tr in tool_results:
            tool_name = tr['tool_name']
            result = tr['result']
            is_error = tr.get('is_error', False)
            
            if is_error:
                has_errors = True
                answer_parts.append(f"⚠️ {tool_name} encountered an error: {result}\n\n")
            else:
                has_success = True
                # Generate concise summary based on tool type
                summary = self._summarize_tool_result(tool_name, result)
                answer_parts.append(summary)
        
        # Add final status
        answer_parts.append("\n---\n")
        if has_success and not has_errors:
            answer_parts.append(f"✅ Analysis complete. Retrieved data from {len(tool_results)} tool(s).")
        elif has_success and has_errors:
            answer_parts.append(f"⚠️ Analysis complete with some errors. Partial data retrieved from {len(tool_results)} tool(s).")
        else:
            answer_parts.append(f"❌ Unable to retrieve data. All {len(tool_results)} tool(s) encountered errors.")
        
        return "".join(answer_parts)
    
    def _summarize_tool_result(self, tool_name: str, result: str) -> str:
        """Generate concise summary of tool result instead of raw data dump"""
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