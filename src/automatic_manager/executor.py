from __future__ import annotations
from typing import Dict, Any
import config
from environment.environment import Environment
from knowledge.knowledge import Knowledge

class Executor:
    """Execute: applies the plan using effectors (place orders, update budget)."""

    def __init__(self, env: Environment, kb: Knowledge):
        self.env = env
        self.kb = kb

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        day = int(plan.get('day', self.env.get_day()))
        actions = {'orders_placed': [], 'spend': 0.0}

        # Apply orders
        for sku, od in plan['orders'].items():
            qty = int(od.get('qty', 0))
            if qty <= 0:
                continue

            p = config.PRODUCTS[sku]
            unit_cost = float(p['unit_cost'])
            fixed = float(p['order_fixed_cost'])
            spend = qty * unit_cost + fixed

            # budget constraint also enforced here (hard safety)
            if spend > config.DAILY_BUDGET_LIMIT - self.kb.daily_budget_spent:
                continue

            lead_time = self.env.place_order(sku, qty)
            self.kb.budget -= spend
            self.kb.record_order(sku, qty, spend)

            actions['orders_placed'].append({'sku': sku, 'qty': qty, 'lead_time': lead_time, 'spend': spend})
            actions['spend'] += spend

        actions['spend'] = round(actions['spend'], 2)
        return actions
