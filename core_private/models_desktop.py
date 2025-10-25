"""
FIRE計算器 - 資料模型
包含所有的資料類別和配置
"""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class PlayerStatus:
    """玩家狀態"""
    age: int = 25  # 當前年齡
    monthly_income: float = 35000  # 月收入
    monthly_expense: float = 30000  # 月支出
    savings: float = 0  # 存款
    debt: float = 0  # 負債
    stock_investment: float = 0  # 股票投資
    bond_investment: float = 0  # 債券投資
    cash_investment: float = 0  # 現金投資
    real_estate_investment: float = 0  # 房地產投資
    is_married: bool = False
    children: int = 0
    has_house: bool = False
    game_events: List[str] = field(default_factory=list)
    
    # 詳細房貸資訊
    house_loan_data: Optional[dict] = None  # 房貸詳細資訊
    
    # 舊屬性的相容性支援
    @property
    def current_age(self):
        return self.age
    
    @current_age.setter
    def current_age(self, value):
        self.age = value
    
    @property
    def cash(self):
        return self.savings
    
    @cash.setter
    def cash(self, value):
        self.savings = value
    
    @property
    def monthly_salary(self):
        return self.monthly_income
    
    @monthly_salary.setter
    def monthly_salary(self, value):
        self.monthly_income = value
    
    @property
    def asset_growth(self):
        return self.stock_investment
    
    @asset_growth.setter
    def asset_growth(self, value):
        self.stock_investment = value
    
    @property
    def asset_conservative(self):
        return self.bond_investment
    
    @asset_conservative.setter
    def asset_conservative(self, value):
        self.bond_investment = value
    
    @property
    def house_loan(self):
        return self.debt
    
    @house_loan.setter
    def house_loan(self, value):
        self.debt = value
    
    @property
    def total_assets(self):
        # 淨資產 = 存款 + 投資總值
        # 注意：
        # 1. 債務(房貸)已經在每月現金流中扣除，不需要在這裡再減
        # 2. real_estate_investment 僅用於圖表顯示，不計入淨資產
        return self.savings + self.stock_investment + self.bond_investment + self.cash_investment
    
    @property
    def net_worth(self):
        return self.total_assets

@dataclass
class SalaryConfig:
    """薪資成長配置"""
    # 薪資成長率 (年度調整)
    young_growth_rate: float = 0.05  # 25-50歲薪資成長率 (5%)
    middle_growth_rate: float = 0.02  # 51-55歲薪資成長率 (2%) 
    senior_decline_rate: float = 0.1  # 56歲薪資驟降比例 (10%)
    
    # 年齡界限
    young_age_limit: int = 50  # 年輕期上限
    middle_age_limit: int = 55  # 中年期上限
    decline_age: int = 56  # 薪資驟降年齡
    
    def get_growth_rate(self, age: int) -> float:
        """根據年齡獲取薪資成長率"""
        if age <= self.young_age_limit:
            return self.young_growth_rate
        elif age <= self.middle_age_limit:
            return self.middle_growth_rate
        elif age == self.decline_age:
            return -self.senior_decline_rate  # 負成長(驟降)
        else:
            return 0.0  # 56歲後不再調薪

@dataclass
class InvestmentConfig:
    """投資配置設定"""
    # 投資比例配置
    stock_ratio: float = 60.0  # 股票比例
    bond_ratio: float = 20.0  # 債券比例
    cash_ratio: float = 15.0  # 現金比例
    real_estate_ratio: float = 5.0  # 房地產比例
    
    # 投資回報率
    stock_return: float = 0.08  # 股票年回報率
    bond_return: float = 0.04  # 債券年回報率
    cash_return: float = 0.02  # 現金年回報率
    real_estate_return: float = 0.06  # 房地產年回報率
    
    # 年齡與退休設定
    retirement_age: int = 65  # 退休年齡
    life_expectancy: int = 85  # 預期壽命
    inflation_rate: float = 0.03  # 通脹率
    
    # 年齡分層配置 - 更新為合理的默認值
    young_growth_ratio: float = 0.8  # 40歲以下成長型比例（80%股票）
    young_conservative_ratio: float = 0.2  # 40歲以下保守型比例（20%債券）
    young_cash_reserve_ratio: float = 0.0  # 40歲以下現金保留比例
    middle_growth_ratio: float = 0.6  # 41-55歲成長型比例（60%股票）
    middle_conservative_ratio: float = 0.4  # 41-55歲保守型比例（40%債券）
    middle_cash_reserve_ratio: float = 0.0  # 41-55歲現金保留比例
    old_growth_ratio: float = 0.4  # 55歲以上成長型比例（40%股票）
    old_conservative_ratio: float = 0.6  # 55歲以上保守型比例（60%債券）
    old_cash_reserve_ratio: float = 0.0  # 55歲以上現金保留比例
    
    # 投資報酬率（向後相容）
    growth_return_rate: float = 0.07  # 成長型年報酬率
    conservative_return_rate: float = 0.05  # 保守型年報酬率（修正為5%，用於成長年金現值折現）

@dataclass
class MonthlyFinancialResult:
    """月度財務結果"""
    age: int = 0
    month: int = 0
    income: float = 0
    basic_expense: float = 0
    monthly_expense: float = 0  # 每月總支出（含基本支出和房貸等）
    house_payment: float = 0
    education_payment: float = 0
    total_expense: float = 0
    net_income: float = 0
    deficit: float = 0
    available_for_investment: float = 0
    bankruptcy_risk: bool = False
    net_worth: float = 0
    monthly_surplus: float = 0
    savings: float = 0
    stock_investment: float = 0
    bond_investment: float = 0
    cash_investment: float = 0
    real_estate_investment: float = 0
    debt: float = 0  # 房貸餘額
