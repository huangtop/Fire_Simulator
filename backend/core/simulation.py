from typing import Dict, Any, List

# NOTE: Keep all core simulation logic here. Frontend must not implement business rules.
# This function consumes the payload shape sent by fire_streamlit.py and returns a
# compact response used by the UI.

def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Calculate monthly payment for principal average payment method (本金平均攤還)"""
    if years <= 0 or principal <= 0:
        return 0
    monthly_principal = principal / (years * 12)
    return monthly_principal

def run_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    ps = payload.get("player_status", {}) or {}
    invest = payload.get("investment_config", {}) or {}
    salary = payload.get("salary_config", {}) or {}
    life_planning = payload.get("life_planning", {}) or {}

    # Minimal placeholder computation to preserve interface; replace with full
    # private implementation in your private repo.
    age = int(ps.get("age") or 25)
    retirement_age = int(invest.get("retirement_age") or 65)
    life_expectancy = int(invest.get("life_expectancy") or 85)
    years = max(0, retirement_age - age)
    years_in_retirement = max(0, life_expectancy - retirement_age)

    # Synthesize a tiny monthly series to unblock UI rendering.
    financial_results: List[Dict[str, Any]] = []
    savings = float(ps.get("savings") or 0)
    monthly_income = float(ps.get("monthly_income") or 0)
    monthly_expense = float(ps.get("monthly_expense") or 0)
    debt = float(ps.get("debt") or 0)

    inflation = float(invest.get("inflation_rate") or 0.03)
    cons_ret = float(invest.get("conservative_return_rate") or 0.03)
    growth_ret = float(invest.get("growth_return_rate") or 0.07)

    event_log: List[str] = [
        "後端模擬開始",
        f"年齡 {age} → 退休 {retirement_age} → 終身 {life_expectancy}，通膨 {inflation:.2%}"
    ]

    # Build yearly summary mapping expected by frontend charts
    cur_age = age
    yearly_map: Dict[int, Dict[str, Any]] = {}
    current_debt = debt  # Track debt changes from life_planning events
    monthly_house_payment = 0.0
    stock_amt = 0.0
    bond_amt = 0.0
    cash_amt = 0.0
    
    # Working age simulation (accumulation phase)
    # 核心邏輯：每月計算現金流，並立即分配投資（月複利）
    for _ in range(years):
        # Check if there are house purchase events for this age
        if str(cur_age) in life_planning:
            events_at_age = life_planning[str(cur_age)]
            if isinstance(events_at_age, list):
                for event in events_at_age:
                    if isinstance(event, dict) and event.get("type") == "買房":
                        # Get the house price or loan amount from event
                        house_price = float(event.get("house_data", {}).get("house_price", 0) or 0)
                        down_payment_ratio = float(event.get("house_data", {}).get("down_payment_ratio", 20)) / 100.0
                        loan_rate = float(event.get("house_data", {}).get("loan_rate", 0.03))
                        loan_years = int(event.get("house_data", {}).get("loan_years", 30))
                        loan_amount = house_price * (1.0 - down_payment_ratio)
                        current_debt = loan_amount
                        monthly_house_payment = calculate_monthly_payment(loan_amount, loan_rate, loan_years)
                        event_log.append(f"年齡 {cur_age}: 買房，房價 ${house_price:,.0f}，貸款 ${loan_amount:,.0f}，月付款 ${monthly_house_payment:,.0f}")
        
        # Get investment ratios for this age
        if cur_age <= 40:
            gr = float(invest.get("young_growth_ratio", 0.0) or 0.0)
            cr = float(invest.get("young_conservative_ratio", 0.0) or 0.0)
            hr = float(invest.get("young_cash_reserve_ratio", 0.0) or 0.0)
        elif cur_age <= 55:
            gr = float(invest.get("middle_growth_ratio", 0.0) or 0.0)
            cr = float(invest.get("middle_conservative_ratio", 0.0) or 0.0)
            hr = float(invest.get("middle_cash_reserve_ratio", 0.0) or 0.0)
        else:
            gr = float(invest.get("old_growth_ratio", 0.0) or 0.0)
            cr = float(invest.get("old_conservative_ratio", 0.0) or 0.0)
            hr = float(invest.get("old_cash_reserve_ratio", 0.0) or 0.0)
        
        # Normalize ratios
        total_ratio = gr + cr + hr
        if total_ratio <= 0:
            gr = cr = 0.0
            hr = 1.0
        else:
            gr, cr, hr = gr / total_ratio, cr / total_ratio, hr / total_ratio
        
        # Monthly simulation
        for m in range(12):
            # Monthly cashflow = (income - house_payment) - expense
            net_monthly_income = monthly_income - monthly_house_payment
            cashflow = net_monthly_income - monthly_expense
            
            # Allocate cashflow to investments immediately (monthly compounding)
            monthly_growth_ret = growth_ret / 12
            monthly_cons_ret = cons_ret / 12
            monthly_cash_ret = float(invest.get("cash_return", 0.02)) / 12
            
            stock_amt = stock_amt * (1 + monthly_growth_ret) + cashflow * gr
            bond_amt = bond_amt * (1 + monthly_cons_ret) + cashflow * cr
            cash_amt = cash_amt * (1 + monthly_cash_ret) + cashflow * hr
            
            # Update loan remaining amount (principal average payment)
            if current_debt > 0 and monthly_house_payment > 0:
                current_debt -= monthly_house_payment
                current_debt = max(0, current_debt)
            
            # Record monthly financial result
            financial_results.append({
                "age": cur_age,
                "month": m + 1,
                "net_worth": stock_amt + bond_amt + cash_amt,
                "savings": 0.0,
                "debt": current_debt,
                "monthly_income": monthly_income,
                "monthly_expense": monthly_expense,
                "total_expense": monthly_expense + monthly_house_payment,
                "stock_investment": stock_amt,
                "bond_investment": bond_amt,
                "cash_investment": cash_amt,
                "real_estate_investment": 0,
            })
        
        # Year-end snapshot
        yearly_map[cur_age] = {
            "monthly_income": monthly_income,
            "monthly_expense": monthly_expense,
            "savings": 0.0,
            "debt": current_debt,
            "stock_investment": stock_amt,
            "bond_investment": bond_amt,
            "cash_investment": cash_amt,
            "net_worth": stock_amt + bond_amt + cash_amt,
            "yearly_withdrawn": 0,
            "monthly_house_payment": monthly_house_payment,
        }
        
        # Progress to next age/year
        cur_age += 1
        monthly_expense *= (1 + inflation)
        monthly_income *= (1 + float(salary.get("young_growth_rate", 0.0)))

    # Retirement phase - monthly withdrawals and monthly compounding
    monthly_income = 0  # No more income in retirement
    for _ in range(years_in_retirement):
        for m in range(12):
            # In retirement: spend monthly expense + house payment (if any)
            monthly_total_expense = monthly_expense + monthly_house_payment
            
            # Apply monthly returns first
            monthly_growth_ret = growth_ret / 12
            monthly_cons_ret = cons_ret / 12
            monthly_cash_ret = float(invest.get("cash_return", 0.02)) / 12
            
            stock_amt *= (1 + monthly_growth_ret)
            bond_amt *= (1 + monthly_cons_ret)
            cash_amt *= (1 + monthly_cash_ret)
            
            # Pay from cash first, then bond, then stock
            if cash_amt >= monthly_total_expense:
                cash_amt -= monthly_total_expense
                current_debt -= monthly_house_payment  # House payment reduces debt
                current_debt = max(0, current_debt)
            elif cash_amt + bond_amt >= monthly_total_expense:
                cash_needed = monthly_total_expense - cash_amt
                bond_amt -= cash_needed
                cash_amt = 0
                current_debt -= monthly_house_payment
                current_debt = max(0, current_debt)
            else:
                # Need to sell stocks
                cash_available = cash_amt + bond_amt
                stock_needed = monthly_total_expense - cash_available
                stock_amt -= stock_needed
                cash_amt = 0
                bond_amt = 0
                stock_amt = max(0, stock_amt)
                current_debt -= monthly_house_payment
                current_debt = max(0, current_debt)
            
            savings = stock_amt + bond_amt + cash_amt
            
            financial_results.append({
                "age": cur_age,
                "month": m + 1,
                "net_worth": savings,
                "savings": 0.0,
                "debt": current_debt,
                "monthly_income": 0,
                "monthly_expense": monthly_expense,
                "total_expense": monthly_total_expense,
                "stock_investment": max(0, stock_amt),
                "bond_investment": max(0, bond_amt),
                "cash_investment": max(0, cash_amt),
                "real_estate_investment": 0,
            })
        
        # End of retirement year
        yearly_map[cur_age] = {
            "monthly_income": 0,
            "monthly_expense": monthly_expense,
            "savings": 0.0,
            "debt": current_debt,
            "stock_investment": max(0, stock_amt),
            "bond_investment": max(0, bond_amt),
            "cash_investment": max(0, cash_amt),
            "net_worth": max(0, savings),
            "yearly_withdrawn": monthly_total_expense * 12,
            "monthly_house_payment": monthly_house_payment,
        }
        
        # Progress to next retirement year
        cur_age += 1
        monthly_expense *= (1 + inflation)
        
        # If debt paid off, stop making house payments
        if current_debt <= 0:
            monthly_house_payment = 0.0

    simulation_results = yearly_map

    event_log.append("後端模擬完成")

    return {
        "simulation_results": simulation_results,
        "financial_results": financial_results,
        "event_log": event_log,
    }
