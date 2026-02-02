
import os


DAILY_BUDGET_HIGH_DEMAND = 42000.0  
DAILY_BUDGET_SUPPLY_ISSUES = 35000.0  

SIMULATION_DAYS = int(os.getenv('SIMULATION_DAYS', 90))
SERVICE_LEVEL_TARGET = 0.95

INITIAL_BUDGET = 30000.0  # Starting capital
DAILY_BUDGET_LIMIT = 30000.0  # Daily operational budget

DT = 1 


BULLWHIP_TARGET = 5.0
BULLWHIP_LAMBDA = 1.0  
DAILY_BUDGET_LIMIT = 30000.0


CANDIDATE_QTYS = [0, 25, 50, 75, 100, 150, 200, 250]


STOCKOUT_PENALTY_PER_UNIT = 300.0  
OVERSTOCK_DAYS_OF_COVER = 45  
STOP_ORDERS_DAYS = 2  

Z_BASE = 2.5  
Z_MIN = 2.0
Z_MAX = 3.5
VOL_TO_Z_SCALE = 0.12

FORECAST_WINDOW_DAYS = 14
ANOMALY_Z_THRESHOLD = 2.0

PRODUCTS = {
    "SKU_001": {
    "name": "Laptop",
    "daily_demand_mean": 20,
    "daily_demand_std": 4,
    "unit_price": 1000.0,
    "unit_cost": 550.0,
    "holding_cost_per_unit_day": 0.3,
    "order_fixed_cost": 50.0,
    "lead_time_days": [2, 4],
    "initial_stock": 550,  # 
    },
    "SKU_002": {
    "name": "Phone",
    "daily_demand_mean": 35,
    "daily_demand_std": 8,
    "unit_price": 700.0,
    "unit_cost": 350.0,
    "holding_cost_per_unit_day": 0.25,
    "order_fixed_cost": 45.0,
    "lead_time_days": [2, 5],
    "initial_stock": 750,  
    },

    "SKU_003": {
        "name": "Headphones",
        "daily_demand_mean": 55,
        "daily_demand_std": 15,
        "unit_price": 120.0,
        "unit_cost": 45.0,  
        "holding_cost_per_unit_day": 0.08,
        "order_fixed_cost": 25.0,
        "lead_time_days": [1, 3],
        "initial_stock": 550,  
    },
    "SKU_004": {
        "name": "Mouse",
        "daily_demand_mean": 70,
        "daily_demand_std": 18,
        "unit_price": 35.0,
        "unit_cost": 8.0,  
        "holding_cost_per_unit_day": 0.02,
        "order_fixed_cost": 15.0,
        "lead_time_days": [1, 2],
        "initial_stock": 700,  # 
    },
}


SCENARIOS = {
    'baseline': {
        'demand_multiplier': 1.0,
        'lead_time_multiplier': 1.0,
        'seed': 42
    },
    'high_demand': {
        'demand_multiplier': 1.2,  
        'lead_time_multiplier': 1.0,
        'seed': 42
    },
    'supply_issues': {
        'demand_multiplier': 1.0,
        'lead_time_multiplier': 1.3,  
        'seed': 42
    }
}

