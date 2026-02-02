# Autonomous Warehouse Inventory Manager

## Overview

This project implements an autonomous inventory management system for a multi-SKU warehouse, following the MAPE-K (Monitor–Analyze–Plan–Execute over Knowledge) control loop. The system simulates daily demand, evaluates inventory and service levels, plans replenishment decisions, and executes orders under budget and operational constraints.

The main goal of the system is to maximize service level and overall profit while controlling inventory costs and avoiding demand amplification (bullwhip effect).

The project is fully containerized using Docker and Docker Compose to ensure modularity, reproducibility, and separation of concerns.

---

## Architecture

The system is composed of independent components orchestrated with Docker Compose:

- **App (Python)**: Implements the MAPE-K loop, demand simulation, planning, and execution logic.
- **InfluxDB**: Time-series database used to store KPIs and historical metrics.
- **Grafana**: Visualization platform connected to InfluxDB for real-time dashboards.
- **Telemetry layer**: Designed to support asynchronous KPI publishing and persistent storage via InfluxDB.

Each component runs in its own container where applicable, allowing clean modularity and easy experimentation.

**High-level flow:**

Environment (Demand Simulation) → Knowledge (State & History) → Planner (MILP + Heuristics) → Execution (Orders & Budget) → Telemetry (InfluxDB)


## Key Features

- Clear implementation of the MAPE-K control loop
- Multi-SKU inventory management under daily budget constraints
- Cost-aware replenishment (ordering and holding costs)
- Stockout penalties and service-level awareness
- Bullwhip penalization to discourage abrupt ordering oscillations
- MILP-based planner using PuLP and the CBC solver
- KPI tracking and storage using InfluxDB
- Fully Dockerized execution environment


## Planning Model

The planner evaluates a set of candidate replenishment quantities for each SKU and computes a utility function including:

- Revenue from fulfilled demand
- Ordering costs
- Holding costs
- Stockout penalties
- Bullwhip penalties (to reduce demand amplification)

A Mixed Integer Linear Programming (MILP) formulation selects the best set of orders under daily budget constraints. Additional heuristics increase replenishment priority for SKUs that recently experienced low service levels.


## KPIs

The system tracks and reports:

- Daily and cumulative fill rate
- Lost sales
- Budget usage (planned and executed)
- Utility value (profit-oriented objective)
- Total revenue, costs, and margin

KPIs are printed to the console and stored in InfluxDB for offline analysis and visualization.


## Project Structure

```text
autonomous-warehouse/
├── automatic_manager/     # Monitor, analyzer, planner, executor logic
├── environment/           # Demand and environment simulation
├── knowledge/             # System state and historical data
├── telemetry/             # InfluxDB telemetry integration
├── utils/                 # Shared utilities
├── grafana/               # Grafana provisioning and dashboards
├── main.py                # Entry point
├── config.py              # Global configuration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── results/               # Simulation outputs and CSV metrics
└── README.md
```

## How to Run

### Requirements

- Docker
- Docker Compose

### Steps

1. Clone the repository.
2. (Optional) Create a `.env` file based on `.env.example`.
3. Run the complete stack:

```bash
docker compose up --build
```

## Visualization & Monitoring

Once the containers are running, you can access the visualization tools to analyze the simulation results in real-time.
1. Grafana (Dashboards)
    - URL: http://localhost:3000
    - User: admin
    - Password: admin
    - Instructions:
        1. Log in with the credentials above.
        2. Navigate to Dashboards > MAPE-K Inventory.
        3. Open the Warehouse MAPE-K Metrics dashboard to view pre-configured plots for Fill Rate, Stock Levels, and Revenue.

2. InfluxDB (Data Explorer)
    - URL: http://localhost:8086
    - User: admin
    - Password: adminpassword123
    - Organization: mape-k-inventory-org
    - Bucket: inventory-metrics
    - Token: my-super-secret-token


## Data Analysis (Flux Queries)
You can perform deep-dive analysis using the InfluxDB Data Explorer or by creating custom panels in Grafana. Use the following Flux queries to extract specific metrics.

Note: The queries below filter for the baseline scenario over the last 92 days. You can change r.scenario == "baseline" to "high_demand" or "supply_issues" to analyze different scenarios.

### Revenue (Daily)
Visualizes the daily revenue fluctuation.

```bash
from(bucket: "inventory-metrics")
  |> range(start: -92d)
  |> filter(fn: (r) => r._measurement == "daily_metrics")
  |> filter(fn: (r) => r._field == "revenue")
  |> filter(fn: (r) => r.scenario == "baseline")
```

### Fill Rate (Service Level)
Tracks the daily service level (1.0 means 100% demand fulfilled).

```bash
from(bucket: "inventory-metrics")
  |> range(start: -92d)
  |> filter(fn: (r) => r._measurement == "daily_metrics")
  |> filter(fn: (r) => r._field == "fill_rate")
  |> filter(fn: (r) => r.scenario == "baseline")
```

### Stock Total
Monitors the total inventory units held in the warehouse.

```bash
from(bucket: "inventory-metrics")
  |> range(start: -92d)
  |> filter(fn: (r) => r._measurement == "daily_metrics")
  |> filter(fn: (r) => r._field == "stock_total")
  |> filter(fn: (r) => r.scenario == "baseline")
```

### Lost Sales (Non-Zero Only)
Filters for days where demand was not met.

Important: If this query returns no data or very few points, it is a positive result. It means the autonomous manager is successfully preventing stockouts.

```bash
from(bucket: "inventory-metrics")
  |> range(start: -92d)
  |> filter(fn: (r) => r._measurement == "daily_metrics")
  |> filter(fn: (r) => r._field == "lost_sales")
  |> filter(fn: (r) => r.scenario == "baseline")
  |> filter(fn: (r) => r._value > 0)
```

## Validation
The system was validated through long simulation runs (90 simulated days) across multiple demand scenarios. Observed results include:
- Service levels consistently above the target threshold (≈ 0.95).
- Reduced lost sales over time.
- Stable ordering behavior (controlled bullwhip effect).
- Positive overall margin.

Simulation outputs and aggregated metrics are provided as CSV files in the results/ directory for further analysis and comparison.

## Conclusion
This project demonstrates how autonomous control, optimization techniques, and containerized architectures can be combined to manage complex inventory systems in a simulated environment. The modular design enables experimentation with planning strategies, demand scenarios, and control policies, making it suitable for academic evaluation and further extension.