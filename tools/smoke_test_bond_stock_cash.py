
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.simulation import run_simulation

payload = {
    "player_status": {
        "age": 30,
        "monthly_income": 80000,
        "monthly_expense": 40000,
        "savings": 200000,
        "debt": 0,
    },
    "investment_config": {
        "retirement_age": 65,
        "life_expectancy": 85,
        "inflation_rate": 0.03,
        "young_growth_ratio": 0.6,
        "young_conservative_ratio": 0.3,
        "young_cash_reserve_ratio": 0.1,
        "middle_growth_ratio": 0.5,
        "middle_conservative_ratio": 0.4,
        "middle_cash_reserve_ratio": 0.1,
        "old_growth_ratio": 0.3,
        "old_conservative_ratio": 0.6,
        "old_cash_reserve_ratio": 0.1,
        "growth_return_rate": 0.07,
        "conservative_return_rate": 0.03,
        "cash_return": 0.02,
    },
    "salary_config": {},
    "life_planning": {},
}

result = run_simulation(payload)
sim = result["simulation_results"]

retirement_age = payload["investment_config"]["retirement_age"]
if retirement_age in sim:
    data = sim[retirement_age]
    print(f"退休年齡: {retirement_age}")
    print(f"股票: {data.get('stock_investment', 0):,.0f}")
    print(f"債券: {data.get('bond_investment', 0):,.0f}")
    print(f"現金: {data.get('cash_investment', 0):,.0f}")
else:
    print(f"找不到退休年齡 {retirement_age} 的資產分布，可用年齡: {list(sim.keys())}")
