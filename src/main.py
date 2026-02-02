from __future__ import annotations

import config
from environment.environment import Environment
from knowledge.knowledge import Knowledge
from automatic_manager.monitor import Monitor
from automatic_manager.analyzer import Analyzer
from automatic_manager.planner import Planner
from automatic_manager.executor import Executor
from utils.logging import info, warn, log_day_header, log_kpis
import csv
from telemetry.influx_writer import InfluxWriter

def run_simulation(scenario_name: str, params: dict, verbose: bool = True) -> dict:
    """
    Run a complete simulation for a given scenario.
    
    Args:
        scenario_name: Name of the scenario
        params: Scenario parameters (demand_mult, lead_mult, seed)
        verbose: Whether to print detailed logs
        
    Returns:
        Dictionary with simulation results
    """
    if verbose:
        info(f"=== SCENARIO: {scenario_name.upper()} ===")
        info(f"Parameters: demand_mult={params['demand_multiplier']}, "
             f"lead_mult={params['lead_time_multiplier']}")
    
    if scenario_name == 'high_demand':
        daily_budget = config.DAILY_BUDGET_HIGH_DEMAND
    elif scenario_name == 'supply_issues':
        daily_budget = config.DAILY_BUDGET_SUPPLY_ISSUES
    else:
        daily_budget = config.DAILY_BUDGET_LIMIT
    
    env = Environment(
        seed=params['seed'],
        demand_multiplier=params['demand_multiplier'],
        lead_time_multiplier=params['lead_time_multiplier']
    )
    
    kb = Knowledge()
    monitor = Monitor(env, kb)
    analyzer = Analyzer(kb)
    planner = Planner(kb)
    executor = Executor(env, kb)
    
    monitor.observe()
    
    total_demand = {sku: 0 for sku in config.PRODUCTS}
    total_sales = {sku: 0 for sku in config.PRODUCTS}
    total_lost = {sku: 0 for sku in config.PRODUCTS}
    total_revenue = 0.0
    total_cost = 0.0
    daily_metrics = []
    
    # ✅ INICIALIZAR TELEMETRY ANTES DEL LOOP
    telemetry = InfluxWriter()
    
    for _ in range(1, int(config.SIMULATION_DAYS) + 1):
        kb.budget = float(daily_budget)
        analysis = analyzer.analyze()
        plan = planner.plan()
        exec_res = executor.execute(plan)
        outcome = env.tick_one_day()
        
        for sku in config.PRODUCTS:
            sales_qty = int(outcome['sales'].get(sku, 0))
            unit_price = float(config.PRODUCTS[sku]['unit_price'])
            unit_cost = float(config.PRODUCTS[sku]['unit_cost'])
            total_revenue += sales_qty * unit_price
            total_cost += sales_qty * unit_cost
        
        mon = monitor.observe()
        day = env.get_day()
        
        # Calculate KPIs
        daily_lost = sum(int(outcome['lost_sales'][sku]) for sku in config.PRODUCTS)
        daily_demand = sum(int(outcome['demand'][sku]) for sku in config.PRODUCTS)
        daily_sales = sum(int(outcome['sales'][sku]) for sku in config.PRODUCTS)
        fill_rate = (daily_sales / daily_demand) if daily_demand > 0 else 1.0
        
        for sku in config.PRODUCTS:
            total_demand[sku] += int(outcome['demand'][sku])
            total_sales[sku] += int(outcome['sales'][sku])
            total_lost[sku] += int(outcome['lost_sales'][sku])
        
        # ✅ ESCRIBIR A INFLUX DENTRO DEL LOOP CON VALORES DEL DÍA ACTUAL
        telemetry.write_daily_metrics(
            scenario=scenario_name,
            day=day,
            metrics={
                'fill_rate': fill_rate,
                'lost_sales': daily_lost,
                'stock_total': sum(mon['stock'].values()),
                'budget_spent': exec_res['spend'],
                'revenue': sum(outcome['sales'][sku] * config.PRODUCTS[sku]['unit_price']
                              for sku in config.PRODUCTS)
            }
        )
        
        for sku in config.PRODUCTS:
            telemetry.write_sku_metrics(
                scenario=scenario_name,
                day=day,
                sku=sku,
                stock=mon['stock'][sku],
                demand=outcome['demand'][sku],
                sales=outcome['sales'][sku]
            )
        
        daily_metrics.append({
            'day': day,
            'fill_rate': fill_rate,
            'lost_sales': daily_lost,
            'budget_spent': exec_res['spend'],
            'revenue': sum(outcome['sales'][sku] * config.PRODUCTS[sku]['unit_price']
                          for sku in config.PRODUCTS)
        })
        
        if verbose:
            log_day_header(day)
            kpis = {
                "Lost sales (units)": daily_lost,
                "Fill rate (daily)": round(fill_rate, 3),
                "Budget spend (plan)": plan['meta']['spend'],
                "Budget spend (exec)": exec_res['spend'],
                "Budget remaining": round(kb.budget, 2),
                "Utility (planned)": plan['meta']['utility'],
            }
            log_kpis(kpis)
            if analysis['anomalies']:
                warn(f"Anomalies: {analysis['anomalies']}")
            if exec_res['orders_placed']:
                info(f"Orders placed: {exec_res['orders_placed']}")
    
    # ✅ CERRAR CONEXIÓN DESPUÉS DEL LOOP
    telemetry.close()
    
    overall_d = sum(total_demand.values())
    overall_s = sum(total_sales.values())
    overall_fill = (overall_s / overall_d) if overall_d > 0 else 1.0
    total_margin = total_revenue - total_cost
    
    csv_filename = f'{scenario_name}_daily_metrics.csv'
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['day', 'fill_rate', 'lost_sales', 'budget_spent', 'revenue'])
        writer.writeheader()
        writer.writerows(daily_metrics)
    
    if verbose:
        info(f"Daily metrics saved to {csv_filename}")
    
    # Print final report
    print("\n" + "="*60)
    print(f"SCENARIO: {scenario_name.upper()} - COMPLETE")
    print("="*60)
    print(f"Overall Fill Rate: {overall_fill:.4f}")
    print(f"\nPer-SKU Fill Rate:")
    for sku in config.PRODUCTS:
        d = total_demand[sku]
        s = total_sales[sku]
        fr = (s / d) if d > 0 else 1.0
        print(f"  {sku}: {fr:.4f} (lost units: {total_lost[sku]})")
    print(f"\nFinancial Summary:")
    print(f"  Total Revenue: ${total_revenue:,.2f}")
    print(f"  Total Cost: ${total_cost:,.2f}")
    print(f"  Total Margin: ${total_margin:,.2f}")
    print(f"  Margin %: {(total_margin/total_revenue*100) if total_revenue > 0 else 0:.2f}%")
    print("="*60)
    
    return {
        'fill_rate': overall_fill,
        'revenue': total_revenue,
        'cost': total_cost,
        'margin': total_margin,
        'margin_pct': (total_margin/total_revenue*100) if total_revenue > 0 else 0,
        'lost_sales': sum(total_lost.values()),
        'total_demand': overall_d,
        'total_sales': overall_s
    }


def main() -> None:
    info("="*60)
    info("AUTONOMOUS INVENTORY MANAGER (MAPE-K)")
    info("Multi-Scenario Evaluation")
    info("="*60)
    info(f"Goal: service level >= {config.SERVICE_LEVEL_TARGET:.2f}")
    info(f"Daily budget limit: ${config.DAILY_BUDGET_LIMIT:,.2f}")
    info(f"Simulation days: {config.SIMULATION_DAYS}")
    info(f"Scenarios: {len(config.SCENARIOS)}")
    info("="*60 + "\n")

    results = {}
    
    for scenario_name, params in config.SCENARIOS.items():
        print(f"\n{'='*60}")
        print(f"STARTING SCENARIO: {scenario_name.upper()}")
        print(f"{'='*60}\n")
        
        scenario_results = run_simulation(scenario_name, params, verbose=False)
        results[scenario_name] = scenario_results
        
        print("\n")

    comparison_file = 'scenario_comparison.csv'
    with open(comparison_file, 'w', newline='') as f:
        fieldnames = ['scenario', 'fill_rate', 'revenue', 'cost', 'margin', 
                     'margin_pct', 'lost_sales', 'total_demand', 'total_sales']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for scenario, data in results.items():
            writer.writerow({'scenario': scenario, **data})
    
    info(f"\n Scenario comparison saved to {comparison_file}")

    print("\n" + "="*80)
    print("MULTI-SCENARIO COMPARISON")
    print("="*80)
    print(f"{'Scenario':<20} {'Fill Rate':<12} {'Lost Sales':<12} {'Margin':<15} {'Margin %':<10}")
    print("-"*80)
    for scenario, data in results.items():
        print(f"{scenario:<20} {data['fill_rate']:<12.4f} {data['lost_sales']:<12.0f} "
              f"${data['margin']:<14,.2f} {data['margin_pct']:<10.2f}%")
    print("="*80)
    
    print("\n TARGET ANALYSIS:")
    target_met = sum(1 for r in results.values() if r['fill_rate'] >= config.SERVICE_LEVEL_TARGET)
    print(f"Scenarios meeting {config.SERVICE_LEVEL_TARGET:.0%} fill rate target: "
          f"{target_met}/{len(results)}")
    
    for scenario, data in results.items():
        print(f"   {scenario}: {data['fill_rate']:.2%}")
    
    print("\n" + "="*80)
    info("ALL SCENARIOS COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
