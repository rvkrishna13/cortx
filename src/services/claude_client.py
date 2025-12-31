"""
Claude API client for natural language reasoning
"""
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx
from src.config.settings import settings
from src.utils.exceptions import ValidationError


class ClaudeClient:
    """Client for interacting with Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.CLAUDE_API_KEY
        # Don't raise error here - let orchestrator handle missing API key
        # The orchestrator will use mock orchestrator if API key is missing
        
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-3-5-sonnet-20241022"
        self.headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _create_tools_schema(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Claude API tool format"""
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"]
            })
        return claude_tools
    
    async def reason_with_tools(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tool_calls: int = 5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Reason about a query using Claude with tool calling
        
        Yields:
            Dict with keys:
            - type: "thinking", "tool_use", "tool_result", "answer", "error"
            - content: Relevant content based on type
            - tool_name: (if type is tool_use or tool_result)
            - tool_arguments: (if type is tool_use)
            - tool_result: (if type is tool_result)
        """
        if not system_prompt:
            system_prompt = """You are a financial data analyst assistant. 
You help users analyze financial data by using available tools to query transactions, portfolios, and market data.
When a user asks a question, think step by step about what tools you need to call and what parameters to use.
Extract relevant information from the query such as:
- User IDs
- Date ranges (convert relative dates like "last week" to ISO format)
- Risk thresholds
- Transaction categories
- Stock symbols

Always provide clear, actionable insights based on the data you retrieve."""

        claude_tools = self._create_tools_schema(tools)
        
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        
        tool_calls_made = 0
        conversation_turn = 0
        max_turns = 10  # Prevent infinite loops
        tool_results_to_send = []  # Store tool results for next API call
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            while conversation_turn < max_turns and tool_calls_made < max_tool_calls:
                try:
                    # Prepare request
                    request_data = {
                        "model": self.model,
                        "max_tokens": 4096,
                        "messages": messages,
                        "system": system_prompt,
                    }
                    
                    # Add tools only on first turn
                    if conversation_turn == 0:
                        request_data["tools"] = claude_tools
                        request_data["tool_choice"] = {"type": "auto"}
                    
                    # Make API call
                    response = await client.post(
                        f"{self.base_url}/messages",
                        headers=self.headers,
                        json=request_data
                    )
                    
                    if response.status_code != 200:
                        error_msg = f"Claude API error: {response.status_code} - {response.text}"
                        yield {"type": "error", "content": error_msg}
                        break
                    
                    response_data = response.json()
                    
                    # Get assistant message content
                    assistant_message = {
                        "role": "assistant",
                        "content": response_data.get("content", [])
                    }
                    messages.append(assistant_message)
                    
                    # Process response content
                    tool_uses = []
                    for content_block in response_data.get("content", []):
                        block_type = content_block.get("type")
                        
                        if block_type == "text":
                            # Thinking or answer text
                            text = content_block.get("text", "")
                            if conversation_turn == 0 and tool_calls_made == 0:
                                yield {"type": "thinking", "content": text}
                            else:
                                yield {"type": "answer", "content": text}
                        
                        elif block_type == "tool_use":
                            # Claude wants to use a tool
                            tool_name = content_block.get("name")
                            tool_input = content_block.get("input", {})
                            tool_id = content_block.get("id")
                            
                            tool_uses.append({
                                "type": "tool_use",
                                "id": tool_id,
                                "name": tool_name,
                                "input": tool_input
                            })
                            
                            yield {
                                "type": "tool_use",
                                "tool_name": tool_name,
                                "tool_arguments": tool_input,
                                "tool_id": tool_id
                            }
                            
                            tool_calls_made += 1
                    
                    # If no tool uses, we're done
                    if not tool_uses:
                        break
                    
                    # Yield tool results placeholder - orchestrator will fill these
                    # We need to wait for orchestrator to call tools and provide results
                    # For now, yield a signal that we need tool results
                    yield {
                        "type": "tool_results_needed",
                        "tool_uses": tool_uses
                    }
                    
                    # Wait for orchestrator to provide tool results
                    # This is handled by the orchestrator calling tools and providing results
                    conversation_turn += 1
                    
                except httpx.TimeoutException:
                    yield {"type": "error", "content": "Request to Claude API timed out"}
                    break
                except Exception as e:
                    yield {"type": "error", "content": f"Error calling Claude API: {str(e)}"}
                    break
    
    async def continue_with_tool_results(
        self,
        messages: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Continue conversation with tool results
        
        Args:
            messages: Previous conversation messages
            tool_results: List of tool results with format:
                [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]
            system_prompt: System prompt
        """
        # Add tool results as a new message
        messages.append({
            "role": "user",
            "content": tool_results
        })
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "max_tokens": 4096,
                        "messages": messages,
                        "system": system_prompt or "You are a helpful assistant."
                    }
                )
                
                if response.status_code != 200:
                    yield {"type": "error", "content": f"Claude API error: {response.status_code}"}
                    return
                
                response_data = response.json()
                
                # Process response
                for content_block in response_data.get("content", []):
                    if content_block.get("type") == "text":
                        yield {
                            "type": "answer",
                            "content": content_block.get("text", "")
                        }
                
            except Exception as e:
                yield {"type": "error", "content": f"Error: {str(e)}"}
    
    async def reason_simple(
        self,
        query: str,
        context: Optional[str] = None
    ) -> str:
        """
        Simple reasoning without tool calling (for fallback)
        
        Returns:
            Answer string
        """
        system_prompt = "You are a helpful financial data analyst assistant."
        
        messages = [{"role": "user", "content": query}]
        if context:
            messages.insert(0, {"role": "user", "content": f"Context: {context}"})
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "max_tokens": 2048,
                        "messages": messages,
                        "system": system_prompt
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"API error: {response.status_code}")
                
                response_data = response.json()
                text_blocks = [
                    block.get("text", "")
                    for block in response_data.get("content", [])
                    if block.get("type") == "text"
                ]
                
                return " ".join(text_blocks)
                
            except Exception as e:
                raise Exception(f"Error calling Claude API: {str(e)}")

