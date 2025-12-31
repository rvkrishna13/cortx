"""
Unit tests for RiskAnalyzer service
"""
import pytest
from unittest.mock import Mock, patch
from src.services.risk_analyzer import RiskAnalyzer


class TestRiskAnalyzer:
    """Tests for RiskAnalyzer class"""
    
    def test_calculate_all_metrics_success(self):
        """Test successful calculation of all risk metrics"""
        analyzer = RiskAnalyzer()
        
        portfolio = {
            "id": 1,
            "assets": {
                "AAPL": {"shares": 100, "price": 175.0, "value": 17500.0},
                "GOOGL": {"shares": 50, "price": 140.0, "value": 7000.0}
            }
        }
        
        transactions = [
            {"amount": 10000.0},
            {"amount": 11000.0},
            {"amount": 10500.0},
            {"amount": 12000.0},
            {"amount": 11500.0}
        ]
        
        current_prices = {"AAPL": 180.0, "GOOGL": 145.0}
        
        result = analyzer.calculate_all_metrics(
            portfolio=portfolio,
            transactions=transactions,
            current_prices=current_prices,
            time_period_days=30
        )
        
        assert "portfolio_value" in result
        assert "volatility" in result
        assert "sharpe_ratio" in result
        assert "value_at_risk_95" in result
        assert "average_return" in result
        assert "max_drawdown" in result
        assert "risk_level" in result
        assert result["portfolio_id"] == 1
        assert result["portfolio_value"] > 0
    
    def test_calculate_all_metrics_with_string_assets(self):
        """Test calculation with JSON string assets"""
        analyzer = RiskAnalyzer()
        
        import json
        portfolio = {
            "id": 2,
            "assets": json.dumps({
                "AAPL": {"shares": 100, "price": 175.0}
            })
        }
        
        transactions = [
            {"amount": 10000.0},
            {"amount": 11000.0},
            {"amount": 10500.0}
        ]
        
        current_prices = {"AAPL": 180.0}
        
        result = analyzer.calculate_all_metrics(
            portfolio=portfolio,
            transactions=transactions,
            current_prices=current_prices,
            time_period_days=30
        )
        
        assert result["portfolio_id"] == 2
        assert result["portfolio_value"] > 0
    
    def test_calculate_all_metrics_insufficient_data(self):
        """Test calculation with insufficient transaction data"""
        analyzer = RiskAnalyzer()
        
        portfolio = {
            "id": 3,
            "assets": {"AAPL": {"shares": 100, "price": 175.0}}
        }
        
        transactions = [{"amount": 10000.0}]  # Only one transaction
        
        current_prices = {"AAPL": 180.0}
        
        result = analyzer.calculate_all_metrics(
            portfolio=portfolio,
            transactions=transactions,
            current_prices=current_prices,
            time_period_days=30
        )
        
        # With insufficient data, the function now returns estimated metrics with a warning
        # instead of an error
        assert "warning" in result or "error" in result
        if "warning" in result:
            assert "Limited transaction history" in result["warning"]
        elif "error" in result:
            assert result["error"] == "Not enough data"
    
    def test_calculate_all_metrics_simple_asset_structure(self):
        """Test calculation with simple asset structure (just shares)"""
        analyzer = RiskAnalyzer()
        
        portfolio = {
            "id": 4,
            "assets": {"AAPL": 100}  # Simple structure
        }
        
        transactions = [
            {"amount": 10000.0},
            {"amount": 11000.0},
            {"amount": 10500.0}
        ]
        
        current_prices = {"AAPL": 180.0}
        
        result = analyzer.calculate_all_metrics(
            portfolio=portfolio,
            transactions=transactions,
            current_prices=current_prices,
            time_period_days=30
        )
        
        assert result["portfolio_id"] == 4
        assert result["portfolio_value"] > 0
    
    def test_classify_risk_low(self):
        """Test risk classification for low risk portfolio"""
        analyzer = RiskAnalyzer()
        
        # Low volatility, high Sharpe ratio
        risk_level = analyzer._classify_risk(volatility=0.10, sharpe_ratio=2.0)
        assert risk_level == "LOW"
    
    def test_classify_risk_high(self):
        """Test risk classification for high risk portfolio"""
        analyzer = RiskAnalyzer()
        
        # High volatility
        risk_level = analyzer._classify_risk(volatility=0.35, sharpe_ratio=1.0)
        assert risk_level == "HIGH"
        
        # Low Sharpe ratio
        risk_level = analyzer._classify_risk(volatility=0.20, sharpe_ratio=0.3)
        assert risk_level == "HIGH"
    
    def test_classify_risk_moderate(self):
        """Test risk classification for moderate risk portfolio"""
        analyzer = RiskAnalyzer()
        
        # Moderate volatility and Sharpe ratio
        risk_level = analyzer._classify_risk(volatility=0.20, sharpe_ratio=1.0)
        assert risk_level == "MODERATE"
    
    def test_calculate_all_metrics_zero_volatility(self):
        """Test calculation with zero volatility (all returns same)"""
        analyzer = RiskAnalyzer()
        
        portfolio = {
            "id": 5,
            "assets": {"AAPL": {"shares": 100, "price": 175.0}}
        }
        
        transactions = [
            {"amount": 10000.0},
            {"amount": 10000.0},
            {"amount": 10000.0}
        ]
        
        current_prices = {"AAPL": 180.0}
        
        result = analyzer.calculate_all_metrics(
            portfolio=portfolio,
            transactions=transactions,
            current_prices=current_prices,
            time_period_days=30
        )
        
        assert result["sharpe_ratio"] == 0  # Should handle zero volatility
        assert result["volatility"] == 0

