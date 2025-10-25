import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.simulation import run_simulation

# 用戶的測試案例：25歲，月入30000，月消費25000，全放現金，現金報酬0%，通膨3%，調薪5%，退休65歲
payload = {
    "player_status": {
        "age": 25,
        "monthly_income": 30000,
        "monthly_expense": 25000,
        "savings": 0,
        "debt": 0,
    },
    "investment_config": {
        "retirement_age": 65,
        "life_expectancy": 85,
        "inflation_rate": 0.03,
        "young_growth_ratio": 0.0,  # 全放現金
        "young_conservative_ratio": 0.0,
        "young_cash_reserve_ratio": 1.0,
        "middle_growth_ratio": 0.0,
        "middle_conservative_ratio": 0.0,
        "middle_cash_reserve_ratio": 1.0,
        "old_growth_ratio": 0.0,
        "old_conservative_ratio": 0.0,
        "old_cash_reserve_ratio": 1.0,
        "growth_return_rate": 0.07,
        "conservative_return_rate": 0.03,
        "cash_return": 0.0,  # 現金報酬0%
    },
    "salary_config": {
        "young_growth_rate": 0.05,  # 調薪5%
        "middle_growth_rate": 0.02,
        "senior_decline_rate": 0.1,
        "young_age_limit": 35,
        "middle_age_limit": 50,
        "decline_age": 55,
    },
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
    print(f"淨資產: {data.get('net_worth', 0):,.0f}")
    print(f"每月收入: {data.get('monthly_income', 0):,.0f}")
    print(f"每月支出: {data.get('monthly_expense', 0):,.0f}")
else:
    print(f"找不到退休年齡 {retirement_age} 的資產分布，可用年齡: {list(sim.keys())}")

# 手動計算驗證
print("\n手動計算驗證:")
age = 25
monthly_income = 30000
monthly_expense = 25000
inflation = 0.03
salary_growth = 0.05
cash_return = 0.0
total_savings = 0
for year in range(40):  # 25 to 65
    monthly_savings = monthly_income - monthly_expense
    annual_savings = monthly_savings * 12
    total_savings += annual_savings
    total_savings *= (1 + cash_return)  # 年複利，但現金0%
    monthly_income *= (1 + salary_growth)
    monthly_expense *= (1 + inflation)
    if year < 5:
        print(f"年 {year+1}: 月收入 {monthly_income:,.0f}, 月支出 {monthly_expense:,.0f}, 年儲蓄 {annual_savings:,.0f}, 累積 {total_savings:,.0f}")

print(f"最終累積: {total_savings:,.0f}")
