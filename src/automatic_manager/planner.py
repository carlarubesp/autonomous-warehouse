from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import math
import pulp
import config
from knowledge.knowledge import Knowledge
from utils.logging import get_logger  


@dataclass
class Candidate:
    qty: int
    utility: float
    spend: float


class Planner:
    """Plan: centralized utility-based planning with service level priority."""

    def __init__(self, kb: Knowledge):
        self.kb = kb
        self.logger = get_logger('planner')  

    @staticmethod
    def _norm_cdf(z: float) -> float:
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    @staticmethod
    def _norm_pdf(z: float) -> float:
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * z * z)

    def _expected_sales_stockout(self, mu: float, sigma: float, available: float) -> Tuple[float, float]:
        if sigma <= 1e-6:
            sold = min(mu, available)
            stockout = max(0.0, mu - sold)
            return float(max(0.0, sold)), float(stockout)

        z = (available - mu) / sigma
        Phi = self._norm_cdf(z)
        phi = self._norm_pdf(z)

        expected_sales = mu * Phi + available * (1 - Phi) - sigma * phi
        expected_sales = max(0.0, min(float(available), float(expected_sales)))
        expected_stockout = max(0.0, mu - expected_sales)
        return float(expected_sales), float(expected_stockout)

    def _dynamic_z(self, sku: str) -> float:
        vol = float(self.kb.volatility.get(sku, 1.0))
        z = float(config.Z_BASE + config.VOL_TO_Z_SCALE * vol)
        z = max(float(config.Z_MIN), min(float(config.Z_MAX), z))
        self.kb.set_safety_z(sku, z)
        return z

    def _is_overstock(self, sku: str, mean_demand: float, stock_pos: int) -> bool:
        if mean_demand <= 1.0:
            return False
        days_cover = stock_pos / mean_demand
        return days_cover > float(config.OVERSTOCK_DAYS_OF_COVER)

    def candidate_utility(self, sku: str, qty: int) -> Candidate:
        p = config.PRODUCTS[sku]
        mean = float(self.kb.forecast.get(sku, {}).get('mean', 0.0))
        std = float(self.kb.forecast.get(sku, {}).get('std', 1.0))
        ltmin, ltmax = p['lead_time_days']
        lt = max(1, int(round((ltmin + ltmax) / 2)))
        
        anomaly = self.kb.anomalies.get(sku)
        rapid = bool(anomaly and anomaly.get('type') == 'spike')
        
        z = float(self.kb.safety_z.get(sku, config.Z_BASE))
        mult = mean * lt
        sigma_lt = std * math.sqrt(lt)
        
        stockpos = self.kb.get_stock_position(sku)
        available = float(stockpos + qty)
        
        mu = mult * (1.5 if rapid else 1.0)
        sigma = sigma_lt
        
        expected_sales, expected_stockout = self._expected_sales_stockout(mu, sigma, available)
        
        revenue = expected_sales * float(p['unit_price'])
        ordercost = qty * float(p['unit_cost']) + (float(p['order_fixed_cost']) if qty > 0 else 0.0)
        leftover = max(0.0, available - expected_sales)
        holdingcost = leftover * float(p['holding_cost_per_unit_day']) * lt
        
        unit_price = float(p['unit_price'])
        base_penalty = float(config.STOCKOUT_PENALTY_PER_UNIT)
        price_weight = max(1.0, (unit_price / 50.0) ** 1.2)
        
        current_sl = self.kb.service_level.get(sku, 1.0)
        sl_factor = 1.0
        if current_sl < config.SERVICE_LEVEL_TARGET:
            sl_deficit = config.SERVICE_LEVEL_TARGET - current_sl
            sl_factor = 1.0 + (sl_deficit * 5.0)
        
        stockout_penalty = expected_stockout * base_penalty * price_weight * sl_factor
        stockout_penalty = min(stockout_penalty, 50000.0)
        
        prevq = self.kb.get_last_order_qty(sku)
        bullwhip_penalty = float(config.BULLWHIP_LAMBDA) * abs(qty - prevq)
        
        utility = revenue - ordercost - holdingcost - stockout_penalty - bullwhip_penalty
        spend = ordercost
        
        return Candidate(qty=int(qty), utility=float(utility), spend=float(spend))

    def plan(self) -> Dict[str, Any]:
        state = self.kb.get_system_state()
        day = int(state['day'])

        plan: Dict[str, Any] = {'day': day, 'orders': {}, 'stop_orders': [], 'meta': {}}


        self.logger.info(f"Day {day}: Starting MILP optimization")

        for sku in config.PRODUCTS:
            self._dynamic_z(sku)

        # Generate candidates per SKU
        sku_cands: Dict[str, List[Candidate]] = {}
        blocked = []
        
        for sku in config.PRODUCTS:
            if self.kb.is_blocked(sku):
                blocked.append(sku)
                sku_cands[sku] = [Candidate(qty=0, utility=0.0, spend=0.0)]
                continue

            mean = float(self.kb.forecast.get(sku, {}).get('mean', 0.0))
            stock_pos = self.kb.get_stock_position(sku)
            overstock = self._is_overstock(sku, mean_demand=mean, stock_pos=stock_pos)
            
            if overstock:
                self.kb.block_orders(sku, config.STOP_ORDERS_DAYS)
                plan['stop_orders'].append({'sku': sku, 'days': int(config.STOP_ORDERS_DAYS)})
                sku_cands[sku] = [Candidate(qty=0, utility=0.0, spend=0.0)]
                self.logger.info(f"  {sku}: Overstock detected, blocking orders")  # ← LOG
                continue

            # Generate candidates
            cands = [self.candidate_utility(sku, q) for q in config.CANDIDATE_QTYS]

            # SERVICE LEVEL PRIORITY ADJUSTMENT 
            current_sl = self.kb.service_level.get(sku, 1.0)
            target_sl = config.SERVICE_LEVEL_TARGET
            p = config.PRODUCTS[sku]
            unit_price = float(p['unit_price'])
            mean_demand = max(1.0, float(self.kb.forecast.get(sku, {}).get('mean', 20.0)))
            
            priority_weight = max(1.0, (unit_price / 50.0) ** 1.3)

            if current_sl < target_sl:
                sl_deficit = target_sl - current_sl
                
                for c in cands:
                    if c.qty == 0:
                        penalty = sl_deficit * mean_demand * 20000.0 * priority_weight
                        c.utility -= penalty
                    else:
                        bonus = sl_deficit * c.qty * 500.0 * priority_weight
                        c.utility += bonus
            
            elif current_sl < (target_sl + 0.03):
                for c in cands:
                    if c.qty > 0:
                        bonus = c.qty * 100.0 * priority_weight
                        c.utility += bonus

            # Heuristic pruning
            best = {}
            for c in cands:
                b = int(round(c.spend))
                if b not in best or c.utility > best[b].utility:
                    best[b] = c
            sku_cands[sku] = list(best.values())

        # MILP optimization
        budget = float(config.DAILY_BUDGET_LIMIT)
        prob = pulp.LpProblem("InventoryOptimization", pulp.LpMaximize)

        x = {}
        for sku, cands in sku_cands.items():
            for i in range(len(cands)):
                x[(sku,i)] = pulp.LpVariable(f"x_{sku}_{i}", lowBound=0, upBound=1, cat="Binary")

        # Objective: maximize total utility
        prob += pulp.lpSum(
            x[(sku,i)] * sku_cands[sku][i].utility 
            for sku in sku_cands 
            for i in range(len(sku_cands[sku]))
        )

        # Constraints: one choice per SKU
        for sku, cands in sku_cands.items():
            prob += pulp.lpSum(x[(sku,i)] for i in range(len(cands))) == 1

        # Budget constraint
        prob += pulp.lpSum(
            x[(sku,i)] * sku_cands[sku][i].spend 
            for sku in sku_cands 
            for i in range(len(sku_cands[sku]))
        ) <= budget

        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        # Extract results
        total_spend = 0.0
        total_util = 0.0

        for sku, cands in sku_cands.items():
            chosen = cands[0]
            for i in range(len(cands)):
                val = pulp.value(x[(sku,i)])
                if val is not None and val > 0.5:
                    chosen = cands[i]
                    break
            
            plan['orders'][sku] = {
                'qty': int(chosen.qty), 
                'expected_utility': float(chosen.utility), 
                'spend': float(chosen.spend)
            }
            total_spend += float(chosen.spend)
            total_util += float(chosen.utility)

        plan['meta'] = {
            'budget_limit': budget, 
            'spend': round(total_spend, 2), 
            'utility': round(total_util, 2), 
            'blocked_skus': blocked
        }
        
        orders_to_place = sum(1 for o in plan['orders'].values() if o['qty'] > 0)
        self.logger.info(
            f"Day {day}: MILP completed - "
            f"Utility={total_util:,.2f}, Spend=${total_spend:,.2f}/{budget:,.2f}, "
            f"Orders={orders_to_place}/{len(config.PRODUCTS)}"
        )
        
        return plan
