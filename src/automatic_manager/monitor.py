from __future__ import annotations
from typing import Dict, Any, List
from environment.environment import Environment
from knowledge.knowledge import Knowledge
from utils.logging import get_logger  # ← AÑADIR IMPORT


class Monitor:
    """Monitor: observes Environment and updates Knowledge."""

    def __init__(self, env: Environment, kb: Knowledge):
        self.env = env
        self.kb = kb
        self.logger = get_logger('monitor')  # ← CREAR LOGGER

    def observe(self) -> Dict[str, Any]:
        # Day and stock snapshot
        day = self.env.get_day()
        self.kb.update_day(day)
        stock_levels = self.env.get_stock()
        self.kb.update_stock_levels(stock_levels)

        # Pending orders snapshot
        pending = []
        for po in self.env.get_pending_orders():
            pending.append({
                'sku': po.sku, 
                'qty': int(po.quantity), 
                'arrival_day': int(po.arrival_day), 
                'unit_cost': float(po.unit_cost)
            })
        self.kb.set_pending_orders(pending)

        # Outcome from last day (demand/sales/lost/arrivals)
        outcome = self.env.get_last_outcome()
        self.kb.record_outcome(outcome)

        # Supply chain monitor signal
        supply_signal = self.env.get_supply_chain_signal()

        if day > 0:  
            total_stock = sum(stock_levels.values())
            total_sales = sum(outcome.get('sales', {}).values())
            total_demand = sum(outcome.get('demand', {}).values())
            
            self.logger.info(
                f"Day {day}: Stock={total_stock} units, "
                f"Sales={total_sales}/{total_demand}, "
                f"Pending orders={len(pending)}"
            )

        return {
            'day': day, 
            'stock': stock_levels,  
            'outcome': outcome, 
            'supply_signal': supply_signal
        }
