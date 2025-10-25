"""
Core FIRE Calculation Module
============================
所有 FIRE 理財運算邏輯都在這裡。
前端 fire_streamlit.py 只負責 UI 渲染和 API 呼叫。

PROTECTED: 核心運算邏輯保留版本，禁止修改計算公式
"""

from typing import Dict, Any, Tuple


class FireCalculations:
    """FIRE 計算核心模組 - 包含所有財務運算邏輯"""

    @staticmethod
    def calculate_growing_annuity_present_value(
        annual_expense: float,
        years: int,
        real_return_rate: float,
        inflation_rate: float
    ) -> float:
        """
        計算成長年金現值 (Growing Annuity Present Value)
        
        公式：當 r ≠ g 時
        PV = E₀ × (1 - ((1+g)/(1+r))^n) / (r - g)
        
        當 r ≈ g 時（接近情況）
        PV = E₀ × n / (1 + r)
        
        Args:
            annual_expense: 第一年支出（E₀）
            years: 年數（n）
            real_return_rate: 實質回報率（r）
            inflation_rate: 通膨率（g）
            
        Returns:
            現值
        """
        if years <= 0 or annual_expense <= 0:
            return 0.0
        
        # 避免分母為零
        r = float(real_return_rate)
        g = float(inflation_rate)
        
        if abs(r - g) < 1e-6:  # r ≈ g
            return annual_expense * years / (1 + r)
        else:
            return annual_expense * (1 - ((1 + g) / (1 + r)) ** years) / (r - g)

    @staticmethod
    def calculate_retirement_target_growing_annuity(
        current_monthly_expense: float,
        current_age: int,
        retirement_age: int,
        life_expectancy: int,
        inflation_rate: float,
        real_return_rate: float
    ) -> float:
        """
        計算達到 FIRE 所需的資產（使用成長年金法）
        
        步驟：
        1. 計算退休時的年支出 = 當前月支出 × 12 × (1+g)^(退休年齡-當前年齡)
        2. 計算退休後年數 = 預期壽命 - 退休年齡
        3. 使用成長年金公式計算現值
        
        Args:
            current_monthly_expense: 當前月支出
            current_age: 當前年齡
            retirement_age: 退休年齡
            life_expectancy: 預期壽命
            inflation_rate: 通膨率
            real_return_rate: 實質回報率
            
        Returns:
            所需資產（現值）
        """
        g = float(inflation_rate)
        r = float(real_return_rate)
        
        # 計算至退休年齡的支出增長
        years_to_retirement = max(0, retirement_age - current_age)
        retirement_annual_expense = current_monthly_expense * 12 * ((1 + g) ** years_to_retirement)
        
        # 退休後年數
        years_in_retirement = max(0, life_expectancy - retirement_age)
        
        # 使用成長年金公式
        return FireCalculations.calculate_growing_annuity_present_value(
            retirement_annual_expense,
            years_in_retirement,
            r,
            g
        )

    @staticmethod
    def calculate_retirement_target_traditional_25x(
        current_monthly_expense: float,
        current_age: int,
        retirement_age: int,
        inflation_rate: float
    ) -> float:
        """
        計算傳統 4% / 25x 法則的退休目標資產
        
        公式：
        目標 = 退休時年支出 × 25
        其中退休時年支出 = 當前月支出 × 12 × (1+g)^(退休年齡-當前年齡)
        
        Args:
            current_monthly_expense: 當前月支出
            current_age: 當前年齡
            retirement_age: 退休年齡
            inflation_rate: 通膨率
            
        Returns:
            所需資產
        """
        g = float(inflation_rate)
        
        # 計算至退休年齡的支出增長
        years_to_retirement = max(0, retirement_age - current_age)
        retirement_annual_expense = current_monthly_expense * 12 * ((1 + g) ** years_to_retirement)
        
        return retirement_annual_expense * 25

    @staticmethod
    def get_allocation_ratios(
        age: int,
        investment_config: Dict[str, Any]
    ) -> Tuple[float, float, float]:
        """
        根據年齡和投資配置返回該年齡段的股票:債券:現金比率
        
        年齡分段：
        - ≤40: young 段
        - 41-55: middle 段
        - >55: old 段
        
        Args:
            age: 年齡
            investment_config: 包含各段比率的配置
            
        Returns:
            (stock_ratio, bond_ratio, cash_ratio)
        """
        if age <= 40:
            gr = float(investment_config.get("young_growth_ratio", 0.0) or 0.0)
            cr = float(investment_config.get("young_conservative_ratio", 0.0) or 0.0)
            hr = float(investment_config.get("young_cash_reserve_ratio", 0.0) or 0.0)
        elif age <= 55:
            gr = float(investment_config.get("middle_growth_ratio", 0.0) or 0.0)
            cr = float(investment_config.get("middle_conservative_ratio", 0.0) or 0.0)
            hr = float(investment_config.get("middle_cash_reserve_ratio", 0.0) or 0.0)
        else:
            gr = float(investment_config.get("old_growth_ratio", 0.0) or 0.0)
            cr = float(investment_config.get("old_conservative_ratio", 0.0) or 0.0)
            hr = float(investment_config.get("old_cash_reserve_ratio", 0.0) or 0.0)
        
        total = gr + cr + hr
        if total <= 0:
            return 0.0, 0.0, 1.0  # 全現金
        
        # 正規化
        return gr / total, cr / total, hr / total


def check_fire_achievement(
    simulation_results: Dict[int, Dict[str, Any]],
    player_status: Dict[str, Any],
    investment_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    檢查 FIRE 達成情況 - 成長年金現值法 + 傳統 25x 法則
    
    Args:
        simulation_results: 模擬結果 {age: {data}}
        player_status: 玩家狀態
        investment_config: 投資配置
        
    Returns:
        包含達成情況的字典
    """
    retirement_age = int(investment_config.get('retirement_age', 65) or 65)
    life_expectancy = int(investment_config.get('life_expectancy', 85) or 85)
    inflation = float(investment_config.get('inflation_rate', 0.03) or 0.03)
    conservative = float(investment_config.get('conservative_return_rate', 0.03) or 0.03)
    
    current_age = int(player_status.get('age', 25) or 25)
    current_monthly_expense = float(player_status.get('monthly_expense', 0) or 0)
    
    result = {
        'fire_age_growing': None,
        'fire_age_traditional': None,
        'fire_target_growing': 0.0,
        'fire_target_traditional': 0.0,
        'retirement_status': {},
        'achievements': []
    }
    
    # 計算目標資產
    if retirement_age in simulation_results:
        retirement_expenses = simulation_results[retirement_age].get('monthly_expense', 0) * 12
        years = max(0, life_expectancy - retirement_age)
        
        result['fire_target_growing'] = FireCalculations.calculate_growing_annuity_present_value(
            retirement_expenses,
            years,
            conservative,
            inflation
        )
        result['fire_target_traditional'] = retirement_expenses * 25
    else:
        result['fire_target_growing'] = FireCalculations.calculate_retirement_target_growing_annuity(
            current_monthly_expense,
            current_age,
            retirement_age,
            life_expectancy,
            inflation,
            conservative
        )
        result['fire_target_traditional'] = FireCalculations.calculate_retirement_target_traditional_25x(
            current_monthly_expense,
            current_age,
            retirement_age,
            inflation
        )
    
    # 檢查各年達成情況
    for age_key in sorted(simulation_results.keys(), key=lambda x: int(x) if isinstance(x, str) else x):
        try:
            age = int(age_key)
        except (ValueError, TypeError):
            continue
        
        data = simulation_results.get(age_key, {})
        net_worth = data.get('net_worth', 0)
        
        remaining_life_years = life_expectancy - age
        if remaining_life_years <= 0:
            continue
        
        years_from_now = age - current_age
        future_expense = current_monthly_expense * 12 * ((1 + inflation) ** years_from_now)
        
        # 成長年金目標
        age_fire_target_growing = FireCalculations.calculate_growing_annuity_present_value(
            future_expense,
            remaining_life_years,
            conservative,
            inflation
        )
        
        # 傳統 25x 目標
        age_fire_target_traditional = future_expense * 25
        
        # 檢查達成
        if result['fire_age_growing'] is None and net_worth >= age_fire_target_growing:
            result['fire_age_growing'] = age
            result['achievements'].append(f"成長年金現值法於 {age} 歲達成 (需要 ${age_fire_target_growing:,.0f}, 擁有 ${net_worth:,.0f})")
        
        if result['fire_age_traditional'] is None and net_worth >= age_fire_target_traditional:
            result['fire_age_traditional'] = age
            result['achievements'].append(f"傳統 25x 法則於 {age} 歲達成 (需要 ${age_fire_target_traditional:,.0f}, 擁有 ${net_worth:,.0f})")
    
    # 退休年齡摘要
    if retirement_age in simulation_results:
        retirement_data = simulation_results[retirement_age]
        result['retirement_status'] = {
            'age': retirement_age,
            'net_worth': retirement_data.get('net_worth', 0),
            'monthly_expense': retirement_data.get('monthly_expense', 0),
            'annual_expense': retirement_data.get('monthly_expense', 0) * 12,
            'safe_withdrawal': retirement_data.get('net_worth', 0) * 0.04
        }
    
    return result
