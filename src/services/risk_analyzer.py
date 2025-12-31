import numpy as np
from typing import Dict, List

class RiskAnalyzer:
    def calculate_all_metrics(
        self,
        portfolio: Dict,
        transactions: List[Dict],
        current_prices: Dict[str, float],
        time_period_days: int
    ) -> Dict:
        """Calculate comprehensive risk metrics"""
        
        # Extract portfolio assets
        import json
        assets = json.loads(portfolio['assets']) if isinstance(portfolio['assets'], str) else portfolio['assets']
        
        # Calculate current portfolio value
        # Assets structure: {"SYMBOL": {"shares": X, "price": Y, "value": Z}}
        portfolio_value = 0.0
        for symbol, asset_data in assets.items():
            if isinstance(asset_data, dict):
                shares = asset_data.get('shares', 0)
                # Use current price if available, otherwise fall back to stored price
                price = current_prices.get(symbol, asset_data.get('price', 0))
                portfolio_value += shares * price
            else:
                # Fallback for simple structure: {"SYMBOL": shares}
                shares = asset_data if isinstance(asset_data, (int, float)) else 0
                price = current_prices.get(symbol, 0)
                portfolio_value += shares * price
        
        # Calculate returns from transaction amounts
        amounts = [t['amount'] for t in transactions]
        if len(amounts) < 2:
            return {"error": "Not enough data"}
        
        returns = np.diff(amounts) / amounts[:-1]
        
        # 1. Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252)
        
        # 2. Average return (annualized)
        mean_return = np.mean(returns) * 252
        
        # 3. Sharpe ratio
        risk_free_rate = 0.02
        sharpe_ratio = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 4. Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5) * portfolio_value
        
        # 5. Maximum drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        return {
            "portfolio_id": portfolio['id'],
            "portfolio_value": portfolio_value,
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe_ratio),
            "value_at_risk_95": float(var_95),
            "average_return": float(mean_return),
            "max_drawdown": float(max_drawdown),
            "risk_level": self._classify_risk(volatility, sharpe_ratio)
        }
    
    def _classify_risk(self, volatility, sharpe_ratio):
        if volatility < 0.15 and sharpe_ratio > 1.5:
            return "LOW"
        elif volatility > 0.30 or sharpe_ratio < 0.5:
            return "HIGH"
        else:
            return "MODERATE"