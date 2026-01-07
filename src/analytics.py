"""Module d'analyse technique"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime


class StockAnalytics:
    """Calcule des indicateurs techniques"""
    
    def __init__(self):
        self.history: list = []
    
    def add_to_history(self, data: Dict[str, Any]):
        """Ajoute une donnée à l'historique"""
        self.history.append(data)
        if len(self.history) > 100:
            self.history.pop(0)
    
    def calculate_sma(self, period: int, price_column: str = "Close") -> Optional[float]:
        """Calcule la Simple Moving Average (SMA)"""
        if len(self.history) < period:
            return None
        
        recent_prices = [float(h.get(price_column, 0)) for h in self.history[-period:]]
        return sum(recent_prices) / len(recent_prices)
    
    def calculate_ema(self, period: int, price_column: str = "Close") -> Optional[float]:
        """Calcule l'Exponential Moving Average (EMA)"""
        if len(self.history) < period:
            return None
        
        recent_prices = [float(h.get(price_column, 0)) for h in self.history[-period:]]
        multiplier = 2 / (period + 1)
        ema = recent_prices[0]
        for price in recent_prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, period: int = 14, price_column: str = "Close") -> Optional[float]:
        """Calcule le Relative Strength Index (RSI)"""
        if len(self.history) < period + 1:
            return None
        
        prices = [float(h.get(price_column, 0)) for h in self.history[-(period + 1):]]
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_volatility(self, period: int = 20, price_column: str = "Close") -> Optional[float]:
        """Calcule la volatilité (écart-type des rendements)"""
        if len(self.history) < period + 1:
            return None
        
        prices = [float(h.get(price_column, 0)) for h in self.history[-period:]]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        if not returns:
            return None
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = np.sqrt(variance) * 100
        
        return volatility
    
    def calculate_price_change_percent(self, current_price: float, 
                                      previous_price: Optional[float] = None,
                                      price_column: str = "Close") -> Optional[float]:
        """Calcule le pourcentage de changement de prix"""
        if previous_price is None:
            if len(self.history) < 1:
                return None
            previous_price = float(self.history[-1].get(price_column, 0))
        
        if previous_price == 0:
            return None
        
        change_percent = ((current_price - previous_price) / previous_price) * 100
        return change_percent
    
    def calculate_volume_average(self, period: int = 20) -> Optional[float]:
        """Calcule le volume moyen sur une période"""
        if len(self.history) < period:
            return None
        
        volumes = [float(h.get("Volume", 0)) for h in self.history[-period:]]
        return sum(volumes) / len(volumes)
    
    def enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrichit les données avec les indicateurs calculés"""
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
        
        self.add_to_history(data)
        enriched = data.copy()
        enriched["indicators"] = {}
        
        sma_20 = self.calculate_sma(20)
        sma_50 = self.calculate_sma(50)
        if sma_20:
            enriched["indicators"]["sma_20"] = sma_20
        if sma_50:
            enriched["indicators"]["sma_50"] = sma_50
        
        ema_12 = self.calculate_ema(12)
        if ema_12:
            enriched["indicators"]["ema_12"] = ema_12
        
        rsi_14 = self.calculate_rsi(14)
        if rsi_14:
            enriched["indicators"]["rsi_14"] = rsi_14
        
        volatility = self.calculate_volatility(20)
        if volatility:
            enriched["indicators"]["volatility"] = volatility
        
        current_price = float(data.get("Close", 0))
        price_change = self.calculate_price_change_percent(current_price)
        if price_change:
            enriched["indicators"]["price_change_percent"] = price_change
        
        volume_avg = self.calculate_volume_average(20)
        if volume_avg:
            enriched["indicators"]["volume_avg_20"] = volume_avg
        
        return enriched
    
    def check_alerts(self, data: Dict[str, Any], 
                    price_threshold: float = 5.0,
                    volume_threshold: float = 200.0) -> list:
        """Vérifie les conditions d'alerte"""
        alerts = []
        indicators = data.get("indicators", {})
        
        price_change = indicators.get("price_change_percent")
        if price_change and abs(price_change) > price_threshold:
            alerts.append({
                "type": "price_change",
                "severity": "high" if abs(price_change) > 10 else "medium",
                "message": f"Changement de prix significatif: {price_change:.2f}%",
                "value": price_change
            })
        
        current_volume = float(data.get("Volume", 0))
        volume_avg = indicators.get("volume_avg_20")
        if volume_avg and current_volume > 0:
            volume_ratio = (current_volume / volume_avg) * 100
            if volume_ratio > volume_threshold:
                alerts.append({
                    "type": "volume_spike",
                    "severity": "high",
                    "message": f"Pic de volume: {volume_ratio:.2f}% de la moyenne",
                    "value": volume_ratio
                })
        
        rsi = indicators.get("rsi_14")
        if rsi:
            if rsi > 70:
                alerts.append({
                    "type": "rsi_overbought",
                    "severity": "medium",
                    "message": f"RSI en surachat: {rsi:.2f}",
                    "value": rsi
                })
            elif rsi < 30:
                alerts.append({
                    "type": "rsi_oversold",
                    "severity": "medium",
                    "message": f"RSI en survente: {rsi:.2f}",
                    "value": rsi
                })
        
        return alerts

