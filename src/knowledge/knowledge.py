from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import config

@dataclass
class OrderRecord:
    day: int
    sku: str
    qty: int
    spend: float

class Knowledge:
    """MAPE-K Knowledge base (in-memory).

    Stores:
    - current day
    - stock levels (last observed)
    - sales history (demand/sales/lost)
    - order history (for bullwhip metrics)
    - pending orders snapshot (for stock position)
    - policies and dynamic parameters (safety stock z, blocks, etc.)
    - analysis outputs (forecast, volatility, service level, anomalies)
    """

    def __init__(self):
        self.day: int = 0
        self.budget: float = float(config.INITIAL_BUDGET)

        self.stock_levels: Dict[str, int] = {sku: int(p.get('initial_stock',0)) for sku,p in config.PRODUCTS.items()}
        self.pending_orders: List[Dict[str, Any]] = []  # [{'sku','qty','arrival_day','unit_cost'}]

        # histories
        self.history: Dict[str, List[Dict[str, int]]] = {sku: [] for sku in config.PRODUCTS}  # day, demand, sales, lost
        self.orders: Dict[str, List[OrderRecord]] = {sku: [] for sku in config.PRODUCTS}

        # analysis outputs
        self.forecast: Dict[str, Dict[str, float]] = {}
        self.volatility: Dict[str, float] = {}
        self.service_level: Dict[str, float] = {}
        self.anomalies: Dict[str, Dict[str, Any]] = {}

        # policies / dynamic state
        self.policies: Dict[str, Any] = {
            'service_level_target': float(config.SERVICE_LEVEL_TARGET),
            'daily_budget_limit': float(config.DAILY_BUDGET_LIMIT),
        }
        self.daily_budget_spent = 0.0
        self.safety_z: Dict[str, float] = {sku: float(config.Z_BASE) for sku in config.PRODUCTS}

        # StopOrders blocks: sku -> blocked_until_day (inclusive)
        self.blocks: Dict[str, int] = {}

    def update_day(self, day: int) -> None:
        self.day = int(day)
        self.daily_budget_spent = 0.0

    def update_stock_levels(self, stock: Dict[str, int]) -> None:
        self.stock_levels = dict(stock)

    def set_pending_orders(self, pending: List[Dict[str, Any]]) -> None:
        self.pending_orders = list(pending)

    def record_outcome(self, outcome: Dict[str, Dict[str, int]]) -> None:
        """Store daily outcome per SKU."""
        for sku in self.history:
            rec = {
                'day': self.day,
                'demand': int(outcome['demand'].get(sku, 0)),
                'sales': int(outcome['sales'].get(sku, 0)),
                'lost_sales': int(outcome['lost_sales'].get(sku, 0)),
            }
            self.history[sku].append(rec)

    def record_order(self, sku: str, qty: int, spend: float) -> None:
        self.orders[sku].append(OrderRecord(day=self.day, sku=sku, qty=int(qty), spend=float(spend)))

    # queries
    def get_recent_history(self, sku: str, window_days: int) -> List[Dict[str, int]]:
        h = self.history[sku]
        if window_days <= 0:
            return h
        return h[-window_days:]

    def get_stock(self, sku: str) -> int:
        return int(self.stock_levels.get(sku, 0))

    def get_stock_position(self, sku: str) -> int:
        on_hand = self.get_stock(sku)
        in_transit = sum(int(o['qty']) for o in self.pending_orders if o['sku'] == sku)
        return int(on_hand + in_transit)

    def get_last_order_qty(self, sku: str) -> int:
        if not self.orders[sku]:
            return 0
        return int(self.orders[sku][-1].qty)

    def is_blocked(self, sku: str) -> bool:
        until = self.blocks.get(sku)
        if until is None:
            return False
        return self.day <= int(until)

    def block_orders(self, sku: str, days: int) -> None:
        self.blocks[sku] = int(self.day + max(0, int(days)))

    # analysis storage 
    def store_forecast(self, sku: str, mean: float, std: float, model: str) -> None:
        self.forecast[sku] = {'mean': float(mean), 'std': float(std), 'model': str(model)}

    def store_volatility(self, sku: str, vol: float) -> None:
        self.volatility[sku] = float(vol)

    def store_service_level(self, sku: str, sl: float) -> None:
        self.service_level[sku] = float(sl)

    def store_anomaly(self, sku: str, anomaly: Optional[Dict[str, Any]]) -> None:
        if anomaly is None:
            self.anomalies.pop(sku, None)
        else:
            self.anomalies[sku] = dict(anomaly)

    def set_safety_z(self, sku: str, z: float) -> None:
        self.safety_z[sku] = float(z)

    def get_system_state(self) -> Dict[str, Any]:
        return {
            'day': self.day,
            'budget': self.budget,
            'stock_levels': dict(self.stock_levels),
            'pending_orders': list(self.pending_orders),
            'forecast': dict(self.forecast),
            'volatility': dict(self.volatility),
            'service_level': dict(self.service_level),
            'anomalies': dict(self.anomalies),
            'safety_z': dict(self.safety_z),
            'blocks': dict(self.blocks),
        }
