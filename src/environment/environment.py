from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
import random
import config


@dataclass
class PendingOrder:
    sku: str
    quantity: int
    arrival_day: int
    unit_cost: float


class Environment:
    """Simulated warehouse environment with demand, lead times, and stock."""

    def __init__(self, seed=None, demand_multiplier=1.0, lead_time_multiplier=1.0):
        """
        Initialize the warehouse environment.
        
        Args:
            seed: Random seed for reproducibility
            demand_multiplier: Multiplier for demand (1.0 = normal, 1.3 = 30% higher)
            lead_time_multiplier: Multiplier for lead times (1.0 = normal, 1.5 = 50% longer)
        """
        self.rng = random.Random(seed)
        self.demand_multiplier = demand_multiplier
        self.lead_time_multiplier = lead_time_multiplier
        
        # Initialize day counter
        self.day = 0  
        
        # Initialize stock with initial values from config
        self.stock = {sku: p['initial_stock'] for sku, p in config.PRODUCTS.items()}
        
        # Pending orders
        self.pending_orders: List[PendingOrder] = []
        
        # Last outcome for monitoring
        self.last_outcome = {
            'demand': {sku: 0 for sku in config.PRODUCTS},
            'sales': {sku: 0 for sku in config.PRODUCTS},
            'lost_sales': {sku: 0 for sku in config.PRODUCTS},
            'arrivals': []
        }
        
        self.supply_chain_signal = {}

    def get_day(self) -> int:
        """Return current simulation day."""
        return self.day

    def get_stock(self) -> Dict[str, int]:
        """Return current stock levels."""
        return dict(self.stock)

    def get_pending_orders(self) -> List[PendingOrder]:
        """Return list of pending orders."""
        return list(self.pending_orders)

    def get_last_outcome(self) -> Dict[str, Any]:
        """Return last day's outcome (demand, sales, lost sales, arrivals)."""
        return self.last_outcome

    def get_supply_chain_signal(self) -> Dict[str, Any]:
        """Return supply chain status signals."""
        return self.supply_chain_signal

    def place_order(self, sku: str, qty: int) -> Dict[str, Any]:
        """
        Place an order with scenario-adjusted lead time.
        
        Args:
            sku: Product SKU
            qty: Order quantity
            
        Returns:
            Order details including adjusted lead time
        """
        if qty <= 0:
            return {}
        
        p = config.PRODUCTS[sku]
        lt_min, lt_max = p['lead_time_days']
        
        # Apply scenario multiplier to lead time
        adjusted_lt_min = max(1, int(round(lt_min * self.lead_time_multiplier)))
        adjusted_lt_max = max(1, int(round(lt_max * self.lead_time_multiplier)))
        
        lead_time = self.rng.randint(adjusted_lt_min, adjusted_lt_max)
        arrival_day = self.day + lead_time
        
        order = PendingOrder(
            sku=sku,
            quantity=qty,
            arrival_day=arrival_day,
            unit_cost=p['unit_cost']
        )
        
        self.pending_orders.append(order)
        
        return {
            'sku': sku,
            'qty': qty,
            'arrival_day': arrival_day,
            'lead_time': lead_time,
            'unit_cost': p['unit_cost']
        }

    def _generate_demand(self, sku: str) -> int:
        """
        Generate demand for a SKU with scenario multiplier applied.
        
        Args:
            sku: Product SKU
            
        Returns:
            Demand quantity (non-negative integer)
        """
        p = config.PRODUCTS[sku]
        base_mean = p['daily_demand_mean']
        base_std = p['daily_demand_std']
        
        # Apply scenario multiplier
        adjusted_mean = base_mean * self.demand_multiplier
        adjusted_std = base_std * self.demand_multiplier
        
        demand = self.rng.gauss(adjusted_mean, adjusted_std)
        return max(0, int(round(demand)))

    def tick_one_day(self) -> Dict[str, Any]:
        """
        Advance simulation by one day: process arrivals, generate demand, fulfill sales.
        
        Returns:
            Outcome dictionary with demand, sales, lost_sales, and arrivals
        """
        self.day += 1
        
        # Process arrivals
        arrivals = []
        remaining_orders = []
        
        for order in self.pending_orders:
            if order.arrival_day <= self.day:
                self.stock[order.sku] += order.quantity
                arrivals.append({
                    'sku': order.sku,
                    'qty': order.quantity,
                    'day': self.day
                })
            else:
                remaining_orders.append(order)
        
        self.pending_orders = remaining_orders
        
        # Generate demand and fulfill sales
        demand = {}
        sales = {}
        lost_sales = {}
        
        for sku in config.PRODUCTS:
            d = self._generate_demand(sku)
            demand[sku] = d
            
            # Fulfill sales
            available = self.stock[sku]
            sold = min(d, available)
            lost = d - sold
            
            sales[sku] = sold
            lost_sales[sku] = lost
            
            # Update stock
            self.stock[sku] -= sold
        
        # Store outcome
        self.last_outcome = {
            'demand': demand,
            'sales': sales,
            'lost_sales': lost_sales,
            'arrivals': arrivals
        }
        
        return self.last_outcome
