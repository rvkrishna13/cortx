"""
Unit tests for metrics route
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from src.api.main import app
from src.observability.metrics import MetricsCollector


class TestMetricsEndpoint:
    """Tests for /metrics endpoint"""
    
    def test_metrics_endpoint_success(self):
        """Test successful metrics endpoint"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_prometheus_format.return_value = "# HELP test_metric Test metric\n# TYPE test_metric counter\ntest_metric 1.0\n"
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics")
            
            assert response.status_code == 200
            # FastAPI adds charset=utf-8 automatically
            assert "text/plain; version=0.0.4" in response.headers["content-type"]
            assert "test_metric" in response.text
    
    def test_metrics_endpoint_empty_metrics(self):
        """Test metrics endpoint with empty metrics"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_prometheus_format.return_value = ""
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics")
            
            assert response.status_code == 200
            assert response.text == ""


class TestMetricsJSONEndpoint:
    """Tests for /metrics/json endpoint"""
    
    def test_metrics_json_endpoint_success(self):
        """Test successful metrics JSON endpoint"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_metrics.return_value = {
                "test_metric": {
                    "count": 10,
                    "total_latency_ms": 100.0,
                    "errors": 2,
                    "last_updated": "2024-01-01T00:00:00"
                }
            }
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics/json")
            
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert "summary" in data
            assert "test_metric" in data["metrics"]
            assert data["metrics"]["test_metric"]["count"] == 10
            assert data["metrics"]["test_metric"]["average_latency_ms"] == 10.0
            assert data["metrics"]["test_metric"]["success_rate"] == 80.0
    
    def test_metrics_json_endpoint_with_llm_metrics(self):
        """Test metrics JSON endpoint with LLM-specific metrics"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_metrics.return_value = {
                "llm_usage_reasoning": {
                    "count": 5,
                    "total_latency_ms": 500.0,
                    "errors": 0,
                    "last_updated": "2024-01-01T00:00:00",
                    "tokens_input": 1000,
                    "tokens_output": 500
                }
            }
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics/json")
            
            assert response.status_code == 200
            data = response.json()
            assert "llm_usage_reasoning" in data["metrics"]
            assert data["metrics"]["llm_usage_reasoning"]["tokens_input"] == 1000
            assert data["metrics"]["llm_usage_reasoning"]["tokens_output"] == 500
            assert data["metrics"]["llm_usage_reasoning"]["total_tokens"] == 1500
    
    def test_metrics_json_endpoint_zero_count(self):
        """Test metrics JSON endpoint with zero count"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_metrics.return_value = {
                "test_metric": {
                    "count": 0,
                    "total_latency_ms": 0.0,
                    "errors": 0,
                    "last_updated": "2024-01-01T00:00:00"
                }
            }
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics/json")
            
            assert response.status_code == 200
            data = response.json()
            assert data["metrics"]["test_metric"]["average_latency_ms"] == 0
            assert data["metrics"]["test_metric"]["success_rate"] == 100.0
    
    def test_metrics_json_endpoint_empty_metrics(self):
        """Test metrics JSON endpoint with empty metrics"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_metrics.return_value = {}
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics/json")
            
            assert response.status_code == 200
            data = response.json()
            assert data["summary"]["total_metrics"] == 0
            assert data["summary"]["total_invocations"] == 0
            assert data["summary"]["overall_success_rate"] == 100.0
    
    def test_metrics_json_endpoint_multiple_metrics(self):
        """Test metrics JSON endpoint with multiple metrics"""
        client = TestClient(app)
        
        with patch('src.api.routes.metrics.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_metrics.return_value = {
                "metric1": {
                    "count": 10,
                    "total_latency_ms": 100.0,
                    "errors": 1,
                    "last_updated": "2024-01-01T00:00:00"
                },
                "metric2": {
                    "count": 20,
                    "total_latency_ms": 200.0,
                    "errors": 2,
                    "last_updated": "2024-01-01T00:00:00"
                }
            }
            mock_get.return_value = mock_collector
            
            response = client.get("/api/v1/metrics/json")
            
            assert response.status_code == 200
            data = response.json()
            assert data["summary"]["total_metrics"] == 2
            assert data["summary"]["total_invocations"] == 30
            assert data["summary"]["total_errors"] == 3
            assert data["summary"]["overall_success_rate"] == 90.0

