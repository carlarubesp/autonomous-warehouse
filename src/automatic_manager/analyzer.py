from __future__ import annotations
from typing import Dict, Any, List, Optional
import math
import statistics
import config
from knowledge.knowledge import Knowledge

class Analyzer:
    """Analyze: forecasting, volatility, service-level, anomaly detection."""

    def __init__(self, kb: Knowledge):
        self.kb = kb
        self.window = int(config.FORECAST_WINDOW_DAYS)
        self.z_thr = float(config.ANOMALY_Z_THRESHOLD)

    def _mean_std(self, xs: List[float]) -> (float, float):
        if not xs:
            return 0.0, 1.0
        if len(xs) == 1:
            return float(xs[0]), max(1.0, abs(float(xs[0])) * 0.25)
        m = float(statistics.mean(xs))
        s = float(statistics.pstdev(xs))
        return m, (s if s > 1e-6 else max(1.0, abs(m) * 0.25))

    def analyze(self) -> Dict[str, Any]:
        state = self.kb.get_system_state()
        day = int(state['day'])
        results: Dict[str, Any] = {'day': day, 'anomalies': {}}

        for sku, p in config.PRODUCTS.items():
            hist = self.kb.get_recent_history(sku, self.window)

            #Calculate Effective Demand (Sales + Lost Sales) to avoid censored data
            eff_demand = [float(r['sales'] + r['lost_sales']) for r in hist if 'sales' in r]
            mean, std = self._mean_std(eff_demand)

            self.kb.store_forecast(sku, mean=mean, std=std, model='moving_average')

            #Calculate Volatility and Service Level (Fill-Rate)
            vol = float(statistics.pstdev(eff_demand)) if len(eff_demand) > 1 else float(std)
            self.kb.store_volatility(sku, vol)

            sum_d = sum(int(r['demand']) for r in hist) if hist else 0
            sum_s = sum(int(r['sales']) for r in hist) if hist else 0
            sl = (sum_s / sum_d) if sum_d > 0 else 1.0
            self.kb.store_service_level(sku, sl)

            #Detect Anomalies (Z-Score Thresholding)
            anomaly: Optional[Dict[str, Any]] = None
            if hist:
                today = float(hist[-1]['sales'] + hist[-1]['lost_sales'])
                z = (today - mean) / (std if std > 1e-6 else 1.0)
                if z > self.z_thr:
                    anomaly = {'type': 'spike', 'z': float(z), 'today': today, 'mean': mean}
                elif z < -self.z_thr:
                    anomaly = {'type': 'drop', 'z': float(z), 'today': today, 'mean': mean}

            self.kb.store_anomaly(sku, anomaly)
            if anomaly:
                results['anomalies'][sku] = anomaly

        return results
