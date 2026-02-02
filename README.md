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
- **Telemetry layer**: Designed to support asynchronous KPI publishing (e.g., MQTT) and persistent storage via InfluxDB.

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

1. Clone the repository
2. (Optional) Create a `.env` file based on `.env.example`
3. Run:

```bash
docker compose up --build
```
This starts all services and runs the autonomous simulation. Daily decisions and KPIs are printed to the console.


## Validation

The system was validated through long simulation runs (90+ simulated days) across multiple demand scenarios. Observed results include:

- Service levels consistently above the target threshold (≈ 0.95)
- Reduced lost sales over time
- Stable ordering behavior (controlled bullwhip effect)
- Positive overall margin

Simulation outputs and aggregated metrics are provided as CSV files for further analysis and comparison.


## Limitations and Future Work

- Add a Grafana dashboard for real-time KPI visualization
- Compare performance against simple baseline policies (e.g., reorder point)
- Extend the model to stochastic lead times
- Support multi-warehouse or multi-supplier scenarios
- Integrate a fully containerized MQTT broker for real-time telemetry

---

## Conclusion

This project demonstrates how autonomous control, optimization techniques, and containerized architectures can be combined to manage complex inventory systems in a simulated environment. The modular design enables experimentation with planning strategies, demand scenarios, and control policies, making it suitable for academic evaluation and further extension.