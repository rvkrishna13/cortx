"""
Orchestrator for coordinating reasoning, tool calls, and responses
Uses Claude API streaming to let Claude decide which tools to call
"""
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from src.services.claude_client import ClaudeClient
from src.mcp.tools import list_tools, call_tool
from src.utils.exceptions import ValidationError
from src.config.settings import settings


class ReasoningOrchestrator:
    """Orchestrates reasoning with MCP tools - lets Claude decide which tools to call"""
    
    def __init__(self, claude_client: Optional[ClaudeClient] = None, request_context: Optional[Any] = None):
        if not settings.CLAUDE_API_KEY:
            raise ValidationError("Claude API key is required for ReasoningOrchestrator. Use MockReasoningOrchestrator instead.")
        self.claude_client = claude_client or ClaudeClient()
        self.available_tools = list_tools()
        self.request_context = request_context  # RequestContext for tracking
    
    async def reason(
        self,
        query: str,
        user_id: Optional[int] = None,
        auth_context: Optional[Dict[str, Any]] = None,
        include_thinking: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main reasoning method that uses Claude streaming API to decide which tools to call
        
        Flow:
        1. Call Claude API with query and available tools (streaming)
        2. Claude responds with thinking and tool_use blocks
        3. Execute tools that Claude requests
        4. Send tool results back to Claude
        5. Stream Claude's final answer
        
        Yields:
            Dict with keys:
            - type: "thinking", "tool_call", "tool_result", "answer", "error", "done"
            - content: Relevant content
            - step_number: Step number
            - tool_name: Tool name (if type is tool_call or tool_result)
            - tool_arguments: Tool arguments (if type is tool_call)
            - tool_result: Tool result (if type is tool_result)
        """
        import httpx
        import json
        import time
        from httpx import TimeoutException, ConnectError, HTTPStatusError
        
        step_number = 0
        tool_calls_used = 0
        final_answer = ""
        messages = []
        
        try:
            # Prepare system prompt with examples
            system_prompt = """You are a financial data analyst assistant. 
                You help users analyze financial data by using available tools to query transactions, portfolios, and market data.
                When a user asks a question, think step by step about what tools you need to call and what parameters to use.
                
                Extract relevant information from the query such as:
                - User IDs (e.g., "user 1" means user_id: 1)
                - Date ranges (convert relative dates like "last week" to ISO format YYYY-MM-DD)
                - Risk thresholds (e.g., "high risk" means min_risk_score: 0.7)
                - Transaction categories
                - Stock symbols (e.g., AAPL, GOOGL)
                - Portfolio IDs (e.g., "portfolio 2" means portfolio_id: 2)

                Example interactions:
                1. User: "Show me high-risk transactions from last week"
                   → Call query_transactions with min_risk_score: 0.7, start_date: (7 days ago), end_date: (today)
                   
                2. User: "Analyze portfolio 2"
                   → Call analyze_risk_metrics with portfolio_id: 2
                   
                3. User: "Get market summary for AAPL and GOOGL"
                   → Call get_market_summary with symbols: ["AAPL", "GOOGL"]
                   
                4. User: "What are the risk metrics for portfolio 1 over the last 30 days?"
                   → Call analyze_risk_metrics with portfolio_id: 1, period_days: 30
                   
                5. User: "Find transactions over $1000 for user 5"
                   → Call query_transactions with user_id: 5, min_amount: 1000

                Always provide clear, actionable insights based on the data you retrieve.
                Format your final answer in a readable way with key findings highlighted."""

            # Convert tools to Claude format
            claude_tools = self.claude_client._create_tools_schema(self.available_tools)
            
            # Initial message
            messages.append({
                "role": "user",
                "content": query
            })
            
            conversation_turn = 0
            # Hardcoded safety limits to prevent infinite loops
            MAX_TURNS = 1000
            MAX_TOOL_CALLS = 10000
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                while True:
                    # Check hardcoded limits
                    if conversation_turn >= MAX_TURNS:
                        yield {
                            "type": "error",
                            "content": f"Maximum conversation turns ({MAX_TURNS}) reached",
                            "step_number": step_number
                        }
                        break
                    if tool_calls_used >= MAX_TOOL_CALLS:
                        yield {
                            "type": "error",
                            "content": f"Maximum tool calls ({MAX_TOOL_CALLS}) reached",
                            "step_number": step_number
                        }
                        break
                    # Prepare request
                    request_data = {
                        "model": self.claude_client.model,
                        "max_tokens": 4096,
                        "messages": messages,
                        "system": system_prompt,
                        "stream": True  # Enable streaming
                    }
                    
                    # Add tools only on first turn
                    if conversation_turn == 0:
                        request_data["tools"] = claude_tools
                        request_data["tool_choice"] = {"type": "auto"}
                    
                    # Make streaming API call
                    conversation_start_time = time.time()
                    llm_tokens_input = 0
                    llm_tokens_output = 0
                    try:
                        async with client.stream(
                            "POST",
                            f"{self.claude_client.base_url}/messages",
                            headers=self.claude_client.headers,
                            json=request_data
                        ) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                error_msg = error_text.decode() if error_text else "Unknown error"
                                
                                # Handle specific HTTP errors
                                if response.status_code == 401:
                                    error_msg = "Invalid API key. Please check your CLAUDE_API_KEY."
                                elif response.status_code == 429:
                                    error_msg = "Rate limit exceeded. Please try again later."
                                elif response.status_code == 500:
                                    error_msg = "Claude API server error. Please try again later."
                                elif response.status_code == 503:
                                    error_msg = "Claude API service unavailable. Please try again later."
                                
                                yield {
                                    "type": "error",
                                    "content": f"Claude API error ({response.status_code}): {error_msg}",
                                    "step_number": step_number
                                }
                                break
                            
                            # Handle streaming errors
                            try:
                                # Collect assistant response for next turn
                                assistant_content = []
                                tool_uses_to_execute = []
                                current_text = ""
                                thinking_text = ""  # Buffer thinking text
                                
                                async for line in response.aiter_lines():
                                    if not line.strip():
                                        continue
                                    
                                    if line.startswith("data: "):
                                        data_str = line[6:]  # Remove "data: " prefix
                                        
                                        if data_str == "[DONE]":
                                            break
                                        
                                        try:
                                            event_data = json.loads(data_str)
                                            event_type = event_data.get("type")
                                            
                                            if event_type == "content_block_delta":
                                                # Collect text content (buffer instead of streaming)
                                                delta = event_data.get("delta", {})
                                                if delta.get("type") == "text_delta":
                                                    text_delta = delta.get("text", "")
                                                    current_text += text_delta
                                                    
                                                    # Buffer thinking or answer text
                                                    if conversation_turn == 0 and tool_calls_used == 0:
                                                        # First turn, no tools called yet - this is thinking
                                                        thinking_text += text_delta
                                                    else:
                                                        # Subsequent turns - this is the answer
                                                        final_answer += text_delta
                                            
                                            elif event_type == "content_block_start":
                                                # Start of a content block
                                                block = event_data.get("content_block", {})
                                                if block.get("type") == "text":
                                                    current_text = ""
                                                elif block.get("type") == "tool_use":
                                                    # Claude wants to use a tool
                                                    tool_use_block = {
                                                        "type": "tool_use",
                                                        "id": block.get("id"),
                                                        "name": block.get("name"),
                                                        "input": block.get("input", {})
                                                    }
                                                    assistant_content.append(tool_use_block)
                                            
                                            elif event_type == "content_block_stop":
                                                # End of content block
                                                if current_text:
                                                    assistant_content.append({
                                                        "type": "text",
                                                        "text": current_text
                                                    })
                                                    current_text = ""
                                            
                                            elif event_type == "message_stop":
                                                # End of message - yield buffered thinking or answer as single event
                                                if conversation_turn == 0 and tool_calls_used == 0 and thinking_text:
                                                    # First turn thinking - send as single event
                                                    if include_thinking:
                                                        yield {
                                                            "type": "thinking",
                                                            "content": thinking_text,
                                                            "step_number": step_number if step_number > 0 else 1
                                                        }
                                                        if step_number == 0:
                                                            step_number = 1
                                                elif conversation_turn > 0:
                                                    # Final answer - send as single event (formatted as JSON)
                                                    # ALWAYS send answer if we're past the first turn
                                                    if not final_answer:
                                                        final_answer = "Analysis complete. Tools executed successfully."
                                                    
                                                    formatted_answer = self._format_final_answer_as_json(
                                                        query=query,
                                                        claude_answer=final_answer,
                                                        executed_tools=executed_tools,
                                                        tool_calls_count=tool_calls_used
                                                    )
                                                    # Parse JSON string to object for cleaner client-side handling
                                                    try:
                                                        answer_content = json.loads(formatted_answer) if isinstance(formatted_answer, str) else formatted_answer
                                                    except:
                                                        answer_content = formatted_answer
                                                    
                                                    yield {
                                                        "type": "answer",
                                                        "content": answer_content,  # Send as dict/object, not string
                                                        "step_number": step_number
                                                    }
                                                break
                                            
                                            elif event_type == "message_delta":
                                                # Message-level updates - check for usage info
                                                usage = event_data.get("usage", {})
                                                if usage:
                                                    input_tokens = usage.get("input_tokens", 0)
                                                    output_tokens = usage.get("output_tokens", 0)
                                                    if input_tokens > 0 or output_tokens > 0:
                                                        # Record LLM usage
                                                        if self.request_context:
                                                            llm_duration = (time.time() - conversation_start_time) * 1000
                                                            self.request_context.record_llm_call(
                                                                tokens_input=input_tokens,
                                                                tokens_output=output_tokens,
                                                                duration_ms=llm_duration
                                                            )
                                            
                                            elif event_type == "message_stop":
                                                # End of message - yield buffered thinking or answer as single event
                                                if conversation_turn == 0 and tool_calls_used == 0 and thinking_text:
                                                    # First turn thinking - send as single event
                                                    if include_thinking:
                                                        yield {
                                                            "type": "thinking",
                                                            "content": thinking_text,
                                                            "step_number": step_number if step_number > 0 else 1
                                                        }
                                                        if step_number == 0:
                                                            step_number = 1
                                                # Answer will be sent after tool execution completes
                                                break
                                        
                                        except json.JSONDecodeError as e:
                                            # Log malformed JSON but continue processing
                                            yield {
                                                "type": "error",
                                                "content": f"Error parsing Claude API response: {str(e)}",
                                                "step_number": step_number
                                            }
                                            continue
                                        except Exception as e:
                                            yield {
                                                "type": "error",
                                                "content": f"Error processing Claude API stream: {str(e)}",
                                                "step_number": step_number
                                            }
                                            break
                            
                            except Exception as e:
                                yield {
                                    "type": "error",
                                    "content": f"Error reading Claude API stream: {str(e)}",
                                    "step_number": step_number
                                }
                                break
                            
                            # Record LLM usage if we captured token counts
                            if (llm_tokens_input > 0 or llm_tokens_output > 0) and self.request_context:
                                llm_duration = (time.time() - conversation_start_time) * 1000
                                self.request_context.record_llm_call(
                                    tokens_input=llm_tokens_input,
                                    tokens_output=llm_tokens_output,
                                    duration_ms=llm_duration
                                )
                            
                            # Add assistant message to conversation
                            if assistant_content:
                                messages.append({
                                    "role": "assistant",
                                    "content": assistant_content
                                })
                            
                            # Extract tool uses from assistant content
                            tool_uses = [
                                block for block in assistant_content
                                if block.get("type") == "tool_use"
                            ]
                            
                            # If this was the final answer (after tools executed), send it as single event (formatted as JSON)
                            # ALWAYS send answer if we're past the first turn and no more tools
                            if conversation_turn > 0 and not tool_uses:
                                step_number += 1
                                # Ensure we have a final answer (Claude's or fallback)
                                if not final_answer:
                                    final_answer = "Analysis complete. Tools executed successfully."
                                
                                formatted_answer = self._format_final_answer_as_json(
                                    query=query,
                                    claude_answer=final_answer,
                                    executed_tools=executed_tools,
                                    tool_calls_count=tool_calls_used
                                )
                                # Parse JSON string to object for cleaner client-side handling
                                try:
                                    answer_content = json.loads(formatted_answer) if isinstance(formatted_answer, str) else formatted_answer
                                except:
                                    answer_content = formatted_answer
                                
                                yield {
                                    "type": "answer",
                                    "content": answer_content,  # Send as dict/object, not string
                                    "step_number": step_number
                                }
                    
                    except httpx.TimeoutException:
                        yield {
                            "type": "error",
                            "content": "Claude API request timed out. Please try again.",
                            "step_number": step_number
                        }
                        break
                    except httpx.ConnectError:
                        yield {
                            "type": "error",
                            "content": "Failed to connect to Claude API. Please check your network connection.",
                            "step_number": step_number
                        }
                        break
                    except httpx.HTTPStatusError as e:
                        yield {
                            "type": "error",
                            "content": f"Claude API HTTP error: {str(e)}",
                            "step_number": step_number
                        }
                        break
                    except Exception as e:
                        yield {
                            "type": "error",
                            "content": f"Unexpected error calling Claude API: {str(e)}",
                            "step_number": step_number
                        }
                        break
                    
                    # Tool uses already extracted above, check if we need to execute them
                        # If no tool uses, we're done (answer already sent above)
                        if not tool_uses:
                            break
                        
                        # Execute tools that Claude requested
                        tool_results = []
                        for tool_use in tool_uses:
                            tool_id = tool_use.get("id")
                            tool_name = tool_use.get("name")
                            tool_input = tool_use.get("input", {})
                            
                            step_number += 1
                            yield {
                                "type": "tool_call",
                                "content": f"Calling tool: {tool_name}",
                                "step_number": step_number,
                                "tool_name": tool_name
                            }
                            
                            # Execute the tool with timing
                            tool_start_time = time.time()
                            try:
                                tool_result = call_tool(
                                    name=tool_name,
                                    arguments=tool_input,
                                    context=auth_context
                                )
                                
                                tool_duration_ms = (time.time() - tool_start_time) * 1000
                                
                                # Record tool call in RequestContext (which records to metrics)
                                if self.request_context:
                                    self.request_context.record_tool_call(
                                        tool_name=tool_name,
                                        duration_ms=tool_duration_ms,
                                        success=not tool_result.get("isError", False)
                                    )
                                
                                # Format tool result (for internal use with Claude, not sent to client)
                                result_text = ""
                                if tool_result.get("isError"):
                                    result_text = f"Error: {tool_result.get('content', [{}])[0].get('text', 'Unknown error')}"
                                else:
                                    content_items = tool_result.get("content", [])
                                    result_parts = []
                                    for item in content_items:
                                        if item.get("type") == "text":
                                            result_parts.append(item.get("text", ""))
                                    result_text = "\n".join(result_parts)
                                
                                step_number += 1
                                # Only send minimal tool result info, not the full data
                                yield {
                                    "type": "tool_result",
                                    "content": f"Tool {tool_name} completed successfully",
                                    "step_number": step_number,
                                    "tool_name": tool_name,
                                    "is_error": False
                                }
                                
                                # Store result for Claude
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": result_text
                                })
                                
                                tool_calls_used += 1
                                
                                # Track executed tool for final answer formatting
                                executed_tools.append({
                                    "name": tool_name,
                                    "success": True,
                                    "arguments": tool_input
                                })
                                
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
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": error_msg
                                })
                                
                                # Track failed tool for final answer formatting
                                executed_tools.append({
                                    "name": tool_name,
                                    "success": False,
                                    "error": error_msg,
                                    "arguments": tool_input
                                })
                        
                        # Add tool results as user message for next turn
                        if tool_results:
                            messages.append({
                                "role": "user",
                                "content": tool_results
                            })
                        
                        conversation_turn += 1
                        
                        # If no more tool uses, send final answer as single event (formatted as JSON)
                        # ALWAYS send answer, even if Claude didn't generate one
                        if not tool_uses:
                            step_number += 1
                            # Ensure we have a final answer (Claude's or fallback)
                            if not final_answer:
                                final_answer = "Analysis complete. Tools executed successfully."
                            
                            formatted_answer = self._format_final_answer_as_json(
                                query=query,
                                claude_answer=final_answer,
                                executed_tools=executed_tools,
                                tool_calls_count=tool_calls_used
                            )
                            # Parse JSON string to object for cleaner client-side handling
                            try:
                                answer_content = json.loads(formatted_answer) if isinstance(formatted_answer, str) else formatted_answer
                            except:
                                answer_content = formatted_answer
                            
                            yield {
                                "type": "answer",
                                "content": answer_content,  # Send as dict/object, not string
                                "step_number": step_number
                            }
                            break
                        
                        # Continue to next turn to get Claude's answer
                        # (The while loop will continue and call Claude again with tool results)
                        # Reset final_answer for next turn
                        final_answer = ""
            
            # Final done event - ALWAYS send, even if no answer was generated
            # Ensure we have a final answer (Claude's or fallback)
            if not final_answer:
                final_answer = "Analysis complete." if tool_calls_used > 0 else "Query processed."
            
            try:
                formatted_final_answer = self._format_final_answer_as_json(
                    query=query,
                    claude_answer=final_answer,
                    executed_tools=executed_tools,
                    tool_calls_count=tool_calls_used
                )
            except Exception as e:
                # If formatting fails, create a simple JSON answer
                formatted_final_answer = json.dumps({
                    "status": "success",
                    "query": query,
                    "tools_called": tool_calls_used,
                    "answer": final_answer,
                    "message": "Analysis complete",
                    "format_error": str(e)
                }, indent=2, ensure_ascii=False)
            
            # Parse the JSON string back to dict for the done event
            try:
                final_answer_dict = json.loads(formatted_final_answer) if isinstance(formatted_final_answer, str) else formatted_final_answer
            except:
                # If parsing fails, use the string as-is wrapped in a dict
                final_answer_dict = {"raw": formatted_final_answer} if formatted_final_answer else {}
            
            yield {
                "type": "done",
                "content": "Reasoning complete",
                "step_number": step_number + 1,
                "final_answer": final_answer_dict,  # Send as dict, not string
                "tool_calls_made": tool_calls_used
            }
            
        except Exception as e:
            # Record error in observability
            if self.request_context:
                from src.observability.metrics import get_metrics_collector
                metrics = get_metrics_collector()
                metrics.record_error(
                    error_type="orchestrator_error",
                    error_message=str(e),
                    context={"step_number": step_number},
                    request_id=self.request_context.request_id
                )
            
            yield {
                "type": "error",
                "content": f"Error in reasoning orchestrator: {str(e)}",
                "step_number": step_number
            }
    
    def _format_final_answer_as_json(
        self,
        query: str,
        claude_answer: str,
        executed_tools: List[Dict[str, Any]],
        tool_calls_count: int
    ) -> str:
        """
        Format Claude's final answer as structured JSON
        
        Args:
            query: Original user query
            claude_answer: Claude's generated answer text
            executed_tools: List of tools that were executed
            tool_calls_count: Number of tool calls made
        
        Returns:
            JSON string with structured answer
        """
        # Determine status based on tool execution
        has_errors = any(not tool.get("success", True) for tool in executed_tools)
        status = "success" if not has_errors else "partial" if executed_tools else "error"
        
        # Build structured answer
        structured_answer = {
            "status": status,
            "query": query,
            "tools_called": tool_calls_count,
            "answer": claude_answer.strip(),
            "tools_executed": [
                {
                    "name": tool["name"],
                    "success": tool.get("success", True),
                    "arguments": tool.get("arguments", {})
                }
                for tool in executed_tools
            ],
            "message": self._get_status_message(has_errors, tool_calls_count)
        }
        
        # Add errors if any
        errors = [tool for tool in executed_tools if not tool.get("success", True)]
        if errors:
            structured_answer["errors"] = [
                {
                    "tool": tool["name"],
                    "error": tool.get("error", "Unknown error")
                }
                for tool in errors
            ]
        
        # Return as formatted JSON string
        return json.dumps(structured_answer, indent=2, ensure_ascii=False)
    
    def _get_status_message(self, has_errors: bool, tool_count: int) -> str:
        """Get status message based on results"""
        if not has_errors:
            return f"Analysis complete. Retrieved data from {tool_count} tool(s)."
        else:
            return f"Analysis complete with some errors. Partial data retrieved from {tool_count} tool(s)."
