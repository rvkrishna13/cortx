"""
Unit tests for streaming service
"""
import pytest
import json
from unittest.mock import AsyncMock
from src.services.streaming import format_sse_event, stream_reasoning_results


class TestFormatSSEEvent:
    """Tests for format_sse_event function"""
    
    def test_format_sse_event_thinking(self):
        """Test formatting thinking event"""
        result = format_sse_event("thinking", {"content": "Analyzing..."})
        
        assert result.startswith("data: ")
        assert "\n\n" in result
        
        # Parse the JSON
        json_str = result.replace("data: ", "").strip()
        data = json.loads(json_str)
        assert data["type"] == "thinking"
        assert data["data"]["content"] == "Analyzing..."
    
    def test_format_sse_event_tool_call(self):
        """Test formatting tool_call event"""
        result = format_sse_event("tool_call", {
            "tool_name": "get_market_summary",
            "message": "Calling tool"
        })
        
        json_str = result.replace("data: ", "").strip()
        data = json.loads(json_str)
        assert data["type"] == "tool_call"
        assert data["data"]["tool_name"] == "get_market_summary"
    
    def test_format_sse_event_answer(self):
        """Test formatting answer event"""
        result = format_sse_event("answer", {"content": "Final answer"})
        
        json_str = result.replace("data: ", "").strip()
        data = json.loads(json_str)
        assert data["type"] == "answer"
        assert data["data"]["content"] == "Final answer"
    
    def test_format_sse_event_error(self):
        """Test formatting error event"""
        result = format_sse_event("error", {"message": "Error occurred"})
        
        json_str = result.replace("data: ", "").strip()
        data = json.loads(json_str)
        assert data["type"] == "error"
        assert data["data"]["message"] == "Error occurred"
    
    def test_format_sse_event_done(self):
        """Test formatting done event"""
        result = format_sse_event("done", {
            "final_answer": "Complete",
            "tool_calls_made": 2
        })
        
        json_str = result.replace("data: ", "").strip()
        data = json.loads(json_str)
        assert data["type"] == "done"
        assert data["data"]["tool_calls_made"] == 2


class TestStreamReasoningResults:
    """Tests for stream_reasoning_results function"""
    
    @pytest.mark.asyncio
    async def test_stream_reasoning_results_success(self):
        """Test successful streaming of reasoning results"""
        async def mock_orchestrator():
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            yield {"type": "tool_call", "tool_name": "get_market_summary", "content": "Calling", "step_number": 2}
            yield {"type": "tool_result", "tool_name": "get_market_summary", "content": "Done", "step_number": 3}
            yield {"type": "answer", "content": "Result", "step_number": 4}
            yield {"type": "done", "final_answer": "Result", "tool_calls_made": 1, "step_number": 5}
        
        events = []
        async for event in stream_reasoning_results(mock_orchestrator()):
            events.append(event)
        
        assert len(events) >= 5
        assert any("start" in e for e in events)
        assert any("thinking" in e for e in events)
        assert any("tool_call" in e for e in events)
        assert any("answer" in e for e in events)
        assert any("done" in e for e in events)
    
    @pytest.mark.asyncio
    async def test_stream_reasoning_results_with_error(self):
        """Test streaming with error event"""
        async def mock_orchestrator():
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            yield {"type": "error", "content": "Error occurred", "step_number": 2}
        
        events = []
        async for event in stream_reasoning_results(mock_orchestrator()):
            events.append(event)
        
        assert len(events) >= 2
        assert any("error" in e for e in events)
    
    @pytest.mark.asyncio
    async def test_stream_reasoning_results_exception(self):
        """Test streaming with exception"""
        async def mock_orchestrator():
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            raise Exception("Streaming error")
        
        events = []
        async for event in stream_reasoning_results(mock_orchestrator()):
            events.append(event)
        
        # Should have start event and error event
        assert len(events) >= 2
        assert any("error" in e for e in events)
    
    @pytest.mark.asyncio
    async def test_stream_reasoning_results_empty(self):
        """Test streaming with empty orchestrator"""
        async def mock_orchestrator():
            return
            yield  # Make it a generator
        
        events = []
        async for event in stream_reasoning_results(mock_orchestrator()):
            events.append(event)
        
        # Should at least have start event
        assert len(events) >= 1
        assert any("start" in e for e in events)

