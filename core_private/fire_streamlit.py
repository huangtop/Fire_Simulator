"""
FIRE理財規劃工具 - Streamlit版本
100%直接轉換原始main_desktop.py，保持原汁原味的邏輯

NOTE: UI 層與 運算邏輯已分離
- 前端：只負責 UI 渲染、用戶輸入、API 呼叫
- 後端：backend/core/simulation.py 負責完整模擬
- 核心計算：core_private/fire_calculations.py 負責 FIRE 指標計算
"""

import streamlit as st
import sys
import os
import json
import datetime
# 導入本地模組 (handle both direct execution and package import)
try:
    from .fire_calculations import FireCalculations, check_fire_achievement
except ImportError:
    try:
        from core_private import FireCalculations
    except ImportError:
        # When run directly, add current directory to path
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from core_private import FireCalculations
import random
import matplotlib.pyplot as plt
import math
import matplotlib.patches as patches
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import time
import base64
import requests

# 導入本地模組 (now imported at package level for Streamlit Cloud compatibility)
def _import_models():
    """Import model classes - now available at package level."""
    try:
        # Try importing from the core_private package (should work now)
        from . import PlayerStatus, InvestmentConfig, SalaryConfig, MonthlyFinancialResult
    except ImportError:
        try:
            # Fallback to direct import
            from .models_desktop import PlayerStatus, InvestmentConfig, SalaryConfig, MonthlyFinancialResult
        except ImportError:
            try:
                from core_private.models_desktop import PlayerStatus, InvestmentConfig, SalaryConfig, MonthlyFinancialResult
            except ImportError:
                # When run directly, add current directory to path
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.insert(0, current_dir)
                from core_private.models_desktop import PlayerStatus, InvestmentConfig, SalaryConfig, MonthlyFinancialResult
    return PlayerStatus, InvestmentConfig, SalaryConfig, MonthlyFinancialResult

# Always import at module level - this should work
PlayerStatus, InvestmentConfig, SalaryConfig, MonthlyFinancialResult = _import_models()

# === Thin-client API configuration (keep UI, move core logic to backend) ===
# Read from Streamlit secrets; provide safe local defaults for dev
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
API_KEY = st.secrets.get("API_KEY", "dev-key")

def call_backend_api(endpoint: str, data: dict) -> dict:
    """POST to backend and return JSON. Raises on non-200."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=data, headers=headers, timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(f"API Error {resp.status_code}: {resp.text}")
    try:
        return resp.json()
    except Exception:
        raise RuntimeError("API returned non-JSON response")

class StreamlitFIREPlanningTool:
    """直接轉換原始FIREPlanningTool類，保持所有原始邏輯"""

    def __init__(self):
        # ensure cache_file exists before any initialization which may read it
        try:
            base_dir = os.path.dirname(__file__)
        except Exception:
            base_dir = os.getcwd()
        self.cache_file = os.path.join(base_dir, "fire_settings_cache.json")

        # 初始化 session 狀態
        self.initialize_session_state()

        # 從 session state 取得引用
        self.player_status = st.session_state.get('player_status', PlayerStatus())
        self.investment_config = st.session_state.get('investment_config', InvestmentConfig())
        self.salary_config = st.session_state.get('salary_config', SalaryConfig())
        self.life_planning = st.session_state.get('life_planning', {})
        self.random_events = st.session_state.get('random_events', {})
        self.simulation_results = st.session_state.get('simulation_results', {})
        self.financial_results = st.session_state.get('financial_results', [])

    def initialize_session_state(self):
        """初始化必要的 session_state 鍵值"""
        # 基本物件
        if 'player_status' not in st.session_state:
            st.session_state['player_status'] = PlayerStatus()
        if 'investment_config' not in st.session_state:
            st.session_state['investment_config'] = InvestmentConfig()
        if 'salary_config' not in st.session_state:
            st.session_state['salary_config'] = SalaryConfig()

        # 集合/結果
        st.session_state.setdefault('life_planning', {})
        st.session_state.setdefault('random_events', {})
        st.session_state.setdefault('simulation_results', {})
        st.session_state.setdefault('financial_results', [])
        st.session_state.setdefault('log_messages', [])

    def save_settings_to_cache(self):
        """將關鍵設定寫入本地快取檔（原地覆蓋）- 已移除檔案操作以支援多用戶"""
        # Removed file caching for multi-user compatibility
        pass


    def log_monthly_asset(self, age, month, savings, stock_investment, bond_investment, net_worth):
        """記錄每月資產狀況（在 Streamlit 中以 session state 儲存文字列）"""
        if 'monthly_log' not in st.session_state:
            st.session_state.monthly_log = []
        message = f"{age}歲{month:2d}月 | 淨資產:${net_worth:>8,.0f} | 存款:${savings:>8,.0f} | 股票:${stock_investment:>8,.0f} | 債券:${bond_investment:>8,.0f}"
        st.session_state.monthly_log.append(message)
        # keep length reasonable
        if len(st.session_state.monthly_log) > 500:
            st.session_state.monthly_log = st.session_state.monthly_log[-500:]

    def log_event(self, message: str):
        """Append a timestamped message to the UI log stored in session_state."""
        try:
            if 'log_messages' not in st.session_state:
                st.session_state.log_messages = []
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = f"[{timestamp}] {message}"
            st.session_state.log_messages.append(entry)
            # keep length reasonable
            if len(st.session_state.log_messages) > 1000:
                st.session_state.log_messages = st.session_state.log_messages[-1000:]
        except Exception:
            # as a fallback, print to stdout so developer can see it in logs
            try:
                print(f"LOG_EVENT_FAILED: {message}")
            except Exception:
                pass

    def safe_rerun(self):
        """Attempt to trigger a Streamlit rerun in a safe way.

        Some environments may not support rerun; fall back to setting a session flag.
        """
        try:
            # preferred method: force Streamlit to rerun the script
            st.rerun()
        except Exception:
            try:
                # fallback: set a session flag that other code paths may honor
                st.session_state['_request_rerun'] = True
            except Exception:
                # last resort: no-op
                pass

    def _reset_session_preserve_params(self):
        """Reset session_state and in-memory state while preserving user parameters.

        Preserved keys: player parameters (age, monthly_income, monthly_expense, debt),
        investment_config, salary_config. Everything else will be cleared.
        """
        try:
            # Build preserved copies
            preserved = {}
            # Preserve a copy of the UI log so debug messages survive the clear
            try:
                preserved['log_messages'] = list(st.session_state.get('log_messages', []))
            except Exception:
                preserved['log_messages'] = []

            # debug: record keys before reset into preserved log
            try:
                preserved['log_messages'].append(f"DEBUG before_reset keys: {list(st.session_state.keys())}")
            except Exception:
                pass

            try:
                ps = st.session_state.get('player_status')
                if ps is not None:
                    preserved['player_status'] = PlayerStatus()
                    preserved['player_status'].age = getattr(ps, 'age', 25)
                    preserved['player_status'].monthly_income = getattr(ps, 'monthly_income', 35000)
                    preserved['player_status'].monthly_expense = getattr(ps, 'monthly_expense', 30000)
                    preserved['player_status'].debt = getattr(ps, 'debt', 0)
                    # ensure assets zeroed
                    preserved['player_status'].savings = 0
                    preserved['player_status'].stock_investment = 0
                    preserved['player_status'].bond_investment = 0
                    preserved['player_status'].cash_investment = 0
                    preserved['player_status'].real_estate_investment = 0
            except Exception:
                pass
            try:
                if 'investment_config' in st.session_state:
                    preserved['investment_config'] = st.session_state['investment_config']
            except Exception:
                pass
            try:
                if 'salary_config' in st.session_state:
                    preserved['salary_config'] = st.session_state['salary_config']
            except Exception:
                pass

            # Clear all keys
            for k in list(st.session_state.keys()):
                try:
                    del st.session_state[k]
                except Exception:
                    try:
                        st.session_state.pop(k, None)
                    except Exception:
                        pass

            # Restore preserved (log_messages first so further debug writes succeed)
            try:
                st.session_state['log_messages'] = preserved.get('log_messages', [])
            except Exception:
                try:
                    st.session_state['log_messages'] = []
                except Exception:
                    pass

            for k, v in preserved.items():
                if k == 'log_messages':
                    continue
                try:
                    st.session_state[k] = v
                except Exception:
                    pass

            # debug: record keys after reset into persistent log
            try:
                st.session_state['log_messages'].append(f"DEBUG after_reset keys: {list(st.session_state.keys())}")
            except Exception:
                pass

            # Ensure important empty keys exist
            st.session_state['life_planning'] = {}
            st.session_state['random_events'] = {}
            st.session_state['simulation_results'] = {}
            st.session_state['financial_results'] = []

            # Clear transient flags (but don't remove the preserved log)
            for t in ['latest_dice_event', 'selected_age', 'monthly_log', 'run_simulation_now', '_post_sim_rerun', 'last_sim_error', '_request_rerun']:
                try:
                    st.session_state.pop(t, None)
                except Exception:
                    pass

            # Mirror into in-memory attributes
            try:
                self.player_status = st.session_state.get('player_status', PlayerStatus())
            except Exception:
                pass
            try:
                self.investment_config = st.session_state.get('investment_config', InvestmentConfig())
            except Exception:
                pass
            try:
                self.salary_config = st.session_state.get('salary_config', SalaryConfig())
            except Exception:
                pass

            # Also clear instance-level collections so UI reads cleared state immediately
            try:
                self.simulation_results = {}
            except Exception:
                pass
            try:
                self.financial_results = []
            except Exception:
                pass
            try:
                self.life_planning = {}
            except Exception:
                pass
            try:
                self.random_events = {}
            except Exception:
                pass
            try:
                self.current_square = 0
            except Exception:
                pass

            # set just_restarted flag so UI shows placeholder metrics immediately
            try:
                st.session_state['just_restarted'] = True
            except Exception:
                pass

            # update disk cache to clear planning/results but preserve initial_settings debt if present
            # Removed file caching for multi-user compatibility
        except Exception:
            pass

    def _clear_planning(self):
        """Clear life planning, random events and simulation results (preserve UI log)."""
        try:
            # Preserve existing log
            preserved_log = list(st.session_state.get('log_messages', []))
        except Exception:
            preserved_log = []

        try:
            # Clear session-level planning and simulation data
            st.session_state['life_planning'] = {}
            st.session_state['random_events'] = {}
            st.session_state['simulation_results'] = {}
            st.session_state['financial_results'] = []
            # clear transients
            for t in ['latest_dice_event', 'selected_age', 'monthly_log', 'run_simulation_now', '_post_sim_rerun', 'last_sim_error', '_request_rerun']:
                try:
                    st.session_state.pop(t, None)
                except Exception:
                    pass
            # restore preserved log and append debug entry
            try:
                st.session_state['log_messages'] = preserved_log
                st.session_state['log_messages'].append(f"DEBUG clear_planning keys after clear: {list(st.session_state.keys())}")
            except Exception:
                try:
                    st.session_state['log_messages'] = [f"DEBUG clear_planning (log restore failed)"]
                except Exception:
                    pass

            # mirror to instance attributes
            try:
                self.life_planning = {}
                self.random_events = {}
                self.simulation_results = {}
                self.financial_results = []
                self.current_square = 0
            except Exception:
                pass

            # update cache to remove planning and results
            # Removed file caching for multi-user compatibility
        except Exception:
            try:
                self.log_event('清除規劃失敗')
            except Exception:
                pass
    
    def execute_life_planning_events_simulation(self, player, age):
        """核心邏輯已移至後端。此函式僅保留占位以維持介面穩定。"""
        try:
            self.log_event(f"ℹ️ 年齡 {age} 的人生事件由後端核心處理")
        except Exception:
            pass
        return 0
    
    def calculate_yearly_finances_simple(self, player, age, annual_event_impact=0):
        """核心邏輯已移至後端。前端不再執行財務計算。"""
        try:
            self.log_event(f"ℹ️ 年齡 {age} 的年度收支計算由後端核心處理")
        except Exception:
            pass
        return
    
    def run_full_simulation(self):
        """運行完整的退休模擬 - 直接調用本地模擬邏輯（適配 Streamlit Cloud）"""
        try:
            self.log_event("🚀 開始完整退休模擬...")

            # 準備模擬參數
            payload = {
                "player_status": {
                    "age": int(getattr(self.player_status, 'age', 25) or 25),
                    "monthly_income": float(getattr(self.player_status, 'monthly_income', 0) or 0),
                    "monthly_expense": float(getattr(self.player_status, 'monthly_expense', 0) or 0),
                    "savings": float(getattr(self.player_status, 'savings', 0) or 0),
                    "debt": float(getattr(self.player_status, 'debt', 0) or 0),
                    "stock_investment": float(getattr(self.player_status, 'stock_investment', 0) or 0),
                    "bond_investment": float(getattr(self.player_status, 'bond_investment', 0) or 0),
                    "cash_investment": float(getattr(self.player_status, 'cash_investment', 0) or 0),
                    "real_estate_investment": float(getattr(self.player_status, 'real_estate_investment', 0) or 0),
                    "is_married": bool(getattr(self.player_status, 'is_married', False) or False),
                    "children": int(getattr(self.player_status, 'children', 0) or 0),
                    "has_house": bool(getattr(self.player_status, 'has_house', False) or False),
                },
                "investment_config": {
                    "retirement_age": int(getattr(self.investment_config, 'retirement_age', 65) or 65),
                    "life_expectancy": int(getattr(self.investment_config, 'life_expectancy', 85) or 85),
                    "inflation_rate": float(getattr(self.investment_config, 'inflation_rate', 0.03) or 0.03),
                    "young_growth_ratio": float(getattr(self.investment_config, 'young_growth_ratio', 0.0) or 0.0),
                    "young_conservative_ratio": float(getattr(self.investment_config, 'young_conservative_ratio', 0.0) or 0.0),
                    "young_cash_reserve_ratio": float(getattr(self.investment_config, 'young_cash_reserve_ratio', 0.0) or 0.0),
                    "middle_growth_ratio": float(getattr(self.investment_config, 'middle_growth_ratio', 0.0) or 0.0),
                    "middle_conservative_ratio": float(getattr(self.investment_config, 'middle_conservative_ratio', 0.0) or 0.0),
                    "middle_cash_reserve_ratio": float(getattr(self.investment_config, 'middle_cash_reserve_ratio', 0.0) or 0.0),
                    "old_growth_ratio": float(getattr(self.investment_config, 'old_growth_ratio', 0.0) or 0.0),
                    "old_conservative_ratio": float(getattr(self.investment_config, 'old_conservative_ratio', 0.0) or 0.0),
                    "old_cash_reserve_ratio": float(getattr(self.investment_config, 'old_cash_reserve_ratio', 0.0) or 0.0),
                    "growth_return_rate": float(getattr(self.investment_config, 'growth_return_rate', 0.07) or 0.07),
                    "conservative_return_rate": float(getattr(self.investment_config, 'conservative_return_rate', 0.03) or 0.03),
                    "cash_return": float(getattr(self.investment_config, 'cash_return', 0.02) or 0.02),
                },
                "salary_config": {
                    "young_growth_rate": float(getattr(self.salary_config, 'young_growth_rate', 0.05) or 0.05),
                    "middle_growth_rate": float(getattr(self.salary_config, 'middle_growth_rate', 0.02) or 0.02),
                    "senior_decline_rate": float(getattr(self.salary_config, 'senior_decline_rate', 0.1) or 0.1),
                    "young_age_limit": int(getattr(self.salary_config, 'young_age_limit', 35) or 35),
                    "middle_age_limit": int(getattr(self.salary_config, 'middle_age_limit', 50) or 50),
                    "decline_age": int(getattr(self.salary_config, 'decline_age', 55) or 55),
                },
                "life_planning": st.session_state.get('life_planning', {}),
            }

            # 直接調用本地模擬函數，而不是 API
            try:
                from backend.core.simulation import run_simulation
                resp = run_simulation(payload)
                self.log_event("✅ 使用本地模擬引擎")
            except ImportError as e:
                self.log_event(f"❌ 無法載入模擬引擎: {e}")
                # 回退到 API 調用（用於開發環境）
                try:
                    resp = call_backend_api("/api/simulate", payload)
                    self.log_event("✅ 使用後端 API 模擬")
                except Exception as api_e:
                    self.log_event(f"❌ API 調用也失敗: {api_e}")
                    raise RuntimeError("無法執行模擬：本地引擎和 API 都不可用")

            # 處理模擬結果
            self.simulation_results = resp.get("simulation_results", {}) or {}
            # Normalize keys to int if they are strings
            if self.simulation_results:
                try:
                    first_key = next(iter(self.simulation_results.keys()))
                    if isinstance(first_key, str):
                        self.simulation_results = {int(k): v for k, v in self.simulation_results.items()}
                except Exception:
                    pass
            
            self.financial_results = []
            for item in resp.get("financial_results", []) or []:
                r = MonthlyFinancialResult()
                for k, v in (item or {}).items():
                    try:
                        setattr(r, k, v)
                    except Exception:
                        pass
                self.financial_results.append(r)

            st.session_state.simulation_results = self.simulation_results
            st.session_state.financial_results = self.financial_results
            try:
                st.session_state['simulation_params_version'] = st.session_state.get('params_version')
            except Exception:
                pass

            for log_msg in resp.get("event_log", []) or []:
                try:
                    self.log_event(log_msg)
                except Exception:
                    pass

            # 將模擬的最後結果更新到 player_status，以供左欄投資組合顯示
            try:
                if self.simulation_results:
                    # 確保 keys 轉換為整數進行比較
                    try:
                        max_year_key = max((int(k) if isinstance(k, str) else k) for k in self.simulation_results.keys())
                    except (ValueError, TypeError):
                        max_year_key = max(self.simulation_results.keys())
                    
                    # 找到對應的實際 key（可能是字符串或整數）
                    last_year = None
                    for k in self.simulation_results.keys():
                        if k == max_year_key:
                            last_year = k
                            break
                    
                    if last_year is not None:
                        last_data = self.simulation_results[last_year]
                        self.log_event(f"🔍 診斷: last_year={last_year}, last_data keys={list(last_data.keys()) if isinstance(last_data, dict) else 'not dict'}")
                        
                        ps = st.session_state.get('player_status') or self.player_status
                        if ps and isinstance(last_data, dict):
                            stock_val = int(last_data.get('stock_investment', 0) or 0)
                            bond_val = int(last_data.get('bond_investment', 0) or 0)
                            cash_val = int(last_data.get('cash_investment', 0) or 0)
                            
                            ps.stock_investment = stock_val
                            ps.bond_investment = bond_val
                            ps.cash_investment = cash_val
                            # real_estate_investment 已經在左欄的邏輯中處理
                            st.session_state['player_status'] = ps
                            self.player_status = ps
                            self.log_event(f"✅ 已更新投資組合: 股票=${stock_val:,.0f}, 債券=${bond_val:,.0f}, 現金=${cash_val:,.0f}")
                        else:
                            self.log_event(f"⚠️ ps={ps}, last_data is dict={isinstance(last_data, dict)}")
            except Exception as e:
                self.log_event(f"❌ 更新投資組合失敗: {str(e)}")
                import traceback
                self.log_event(f"❌ 錯誤追蹤: {traceback.format_exc()}")
                pass

            self.log_event(f"📈 完成{len(self.simulation_results)}年模擬，共{len(self.simulation_results)}筆記錄")
            try:
                self.check_fire_achievement()
            except Exception:
                pass
            # 標記已完成模擬，用於 UI 刷新
            try:
                st.session_state['_force_sim_display_refresh'] = True
            except Exception:
                pass
            return True
        except Exception as e:
            self.log_event(f"❌ 模擬過程中發生錯誤: {str(e)}")
            import traceback
            self.log_event(f"❌ 詳細錯誤: {traceback.format_exc()}")
            return False
    
    def draw_monopoly_board_streamlit(self, scale=0.7, start_age=20, end_age=None):
        """繪製大富翁風格的年齡棋盤 - 完全按照原始ui_components.py邏輯
        scale: multiply the base figsize by this factor (default 0.7)
        """
        # Ensure a CJK-capable font is selected before drawing so Chinese text doesn't render as boxes
        try:
            import matplotlib.font_manager as fm
            available = {f.name for f in fm.fontManager.ttflist}
            preferred = None
            for name in ['Noto Sans CJK TC', 'PingFang TC', 'Heiti TC', 'LiHei Pro', 'AppleGothic', 'Arial Unicode MS', 'DejaVu Sans']:
                if name in available:
                    preferred = name
                    break
            if preferred:
                plt.rcParams['font.family'] = preferred
        except Exception:
            pass

        # Slightly smaller board for streamlit layout
        # scale: multiply the base figsize by this factor
        fig, ax = plt.subplots(1, 1, figsize=(8 * float(scale), 8 * float(scale)))

        # 定義年齡範圍（預設20歲起，結束年齡由end_age決定，若未提供則使用investment_config.retirement_age或65作為上限）
        if end_age is None:
            try:
                end_age = int(getattr(self.investment_config, 'retirement_age', 65))
            except Exception:
                end_age = 65
        ages = list(range(int(start_age), int(end_age) + 1))

        # 設定畫布 - 尺寸會根據欲顯示年齡數動態調整，以避免標籤重疊或超出邊界
        # side_cells: 每邊的格子數 (至少12)，格子寬度/高度為1個單位
        num_ages = len(ages)
        side_cells = max(12, math.ceil((num_ages + 4) / 4))
        S = int(side_cells)
        ax.set_xlim(0, S)
        ax.set_ylim(0, S)
        ax.set_aspect('equal')
        ax.axis('off')

        # 動態計算周邊格子位置，以 S 為每邊格子數 (包含轉角)
        positions = []
        # 底邊：從左到右 (0..S-1)
        for i in range(S):
            positions.append((i, 0))
        # 右邊：從下往上 (1..S-1)
        for i in range(1, S):
            positions.append((S - 1, i))
        # 頂邊：從右往左 (1..S-1)
        for i in range(1, S):
            positions.append((S - 1 - i, S - 1))
        # 左邊：從上往下 (1..S-2)
        for i in range(1, S - 1):
            positions.append((0, S - 1 - i))

        squares = {}
        # 決定年齡帶分界 (年輕/中年/老年)
        total_years = int(end_age) - int(start_age) + 1
        if total_years > 2:
            band1_end = int(start_age + total_years // 4)
            band2_end = int(start_age + 2 * (total_years // 4))
            band3_end = int(start_age + 3 * (total_years // 4))
        else:
            band1_end = start_age
            band2_end = end_age

        # 為所有周邊位置都畫格子，若位置有對應年齡則標上年齡與依年齡帶著色，否則使用中性底色
        for idx, (x, y) in enumerate(positions):
            age = ages[idx] if idx < len(ages) else None
            if age is None:
                face = 'whitesmoke'
            else:
                # 年齡帶顏色：年輕=lightgreen，中年=lightyellow，老年=lightcoral
                if age <= band1_end:
                    face = 'lightgreen'
                elif age <= band2_end:
                    face = 'lightblue'
                elif age <= band3_end:
                    face = 'lightyellow'
                else:
                    face = 'lightcoral'

            rect = patches.Rectangle((x, y), 1, 1, linewidth=1,
                                     edgecolor='black', facecolor=face, alpha=0.9)
            ax.add_patch(rect)

            if age is not None:
                ax.text(x + 0.5, y + 0.5, str(age), ha='center', va='center', fontsize=max(6, int(7 * (12 / S))), weight='bold')
                squares[age] = (x + 0.5, y + 0.5)

        # 在中央添加標題和目前狀態 
        ax.text(6, 6.5, "💰 FIRE 理財規劃", ha='center', va='center', 
                fontsize=14, weight='bold', color='darkblue', fontfamily=preferred if 'preferred' in locals() and preferred else None)
        ax.text(6, 5.9, f"目前年齡: {self.player_status.age}歲", ha='center', va='center', 
                fontsize=11, weight='bold', fontfamily=preferred if 'preferred' in locals() and preferred else None)
        # show net worth as-is (may be negative) and color accordingly
        current_net = getattr(self.player_status, 'net_worth', None)
        if current_net is None:
            # fallback to computed sum of liquid assets if net_worth not set
            current_net = (
                getattr(self.player_status, 'savings', 0)
                + getattr(self.player_status, 'stock_investment', 0)
                + getattr(self.player_status, 'bond_investment', 0)
                + getattr(self.player_status, 'cash_investment', 0)
            )
        ax.text(6, 5.4, f"淨資產: ${current_net:,.0f}", ha='center', va='center', 
                fontsize=10, color='green' if current_net >= 0 else 'red', fontfamily=preferred if 'preferred' in locals() and preferred else None)
        ax.text(6, 5.0, f"月收入: ${self.player_status.monthly_income:,.0f}", ha='center', va='center', 
                fontsize=9, fontfamily=preferred if 'preferred' in locals() and preferred else None)
        ax.text(6, 4.6, f"月支出: ${self.player_status.monthly_expense:,.0f}", ha='center', va='center', 
                fontsize=9, fontfamily=preferred if 'preferred' in locals() and preferred else None)

        # 標示目前位置 
        if self.player_status.age in squares:
            x, y = squares[self.player_status.age]
            circle = patches.Circle((x, y), 0.25, color='red', alpha=0.8, zorder=10)
            ax.add_patch(circle)
            ax.text(x, y, "👤", ha='center', va='center', fontsize=10, zorder=11, fontfamily=preferred if 'preferred' in locals() and preferred else None)

        # 繪製人生規劃與隨機事件標記（來自 life_planning 與 random_events）
        try:
            for age_key, events in (self.life_planning or {}).items():
                try:
                    age_int = int(age_key)
                except Exception:
                    age_int = age_key
                if age_int in squares:
                    sx, sy = squares[age_int]
                    # draw markers for each event (small circles)
                    offset = 0
                    for ev in events:
                        impact = ev.get('financial_impact', 0) if isinstance(ev, dict) else 0
                        source = ev.get('source', '') if isinstance(ev, dict) else ''
                        etype = ev.get('type', '') if isinstance(ev, dict) else ''
                        if source == 'dice_game' or '骰' in str(etype):
                            color = 'red' if impact < 0 else 'orange'
                            symbol = '🎲'
                        else:
                            color = 'blue'
                            symbol = '📋'

                        circ = patches.Circle((sx + 0.12 + offset, sy + 0.12), 0.055, color=color, zorder=12)
                        ax.add_patch(circ)
                        ax.text(sx + 0.12 + offset, sy + 0.12, symbol, ha='center', va='center', fontsize=6, zorder=13, fontfamily=preferred if 'preferred' in locals() and preferred else None)
                        offset += 0.12
        except Exception:
            pass

        plt.title(f"FIRE理財規劃 - 人生年齡棋盤 ({start_age}-{end_age}歲)", fontsize=12, weight='bold', pad=12, fontfamily=preferred if 'preferred' in locals() and preferred else None)
        # plt.title(f"""FIRE理財規劃 - 人生年齡棋盤
        #             • 年輕期：努力增加本業收入，多配置市值型投資，長期投資從年輕開始。
        #             • 中年期：薪水及家庭負擔高原期，平衡配置，兼顧成長與穩定。
        #             • 退休前15年：轉職難度增加，增加保守型投資，降低波動風險。為退休打底。""",fontsize=8,)
        return fig, squares

    def show_monopoly_board(self):
        """Render a clickable board image with overlay links that set ?selected_age=XX or, when matplotlib is used,
        provide buttons in a grid to let users click an age to add planning events."""
        # Try to use a pre-generated PNG+meta if available (faster and gives precise clickable areas)
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        board_png = os.path.join(static_dir, 'board.png')
        board_meta = os.path.join(static_dir, 'board_meta.json')

        # If PNG+meta exist, render them with clickable overlays
        if os.path.exists(board_png) and os.path.exists(board_meta):
            try:
                with open(board_meta, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                with open(board_png, 'rb') as f:
                    img_bytes = f.read()
                img_b64 = base64.b64encode(img_bytes).decode('ascii')

                html = ["<div style='position:relative; max-width:650px; width:100%;'>"]
                html.append(f"<img src=\"data:image/png;base64,{img_b64}\" style=\"width:100%; display:block;\" />")
                for age_str, bbox in meta.items():
                    try:
                        age = int(age_str)
                    except Exception:
                        age = int(float(age_str))
                    left_pct = bbox[0] * 100
                    top_pct = bbox[1] * 100
                    width_pct = (bbox[2] - bbox[0]) * 100
                    height_pct = (bbox[3] - bbox[1]) * 100
                    html.append(
                        f"<a href='?selected_age={age}' title='{age}歲' "
                        f"style=\"position:absolute; left:{left_pct:.2f}%; top:{top_pct:.2f}%; width:{width_pct:.2f}%; height:{height_pct:.2f}%; display:block; background:rgba(0,0,0,0); text-decoration:none;\"></a>"
                    )
                html.append("</div>")
                st.markdown('\n'.join(html), unsafe_allow_html=True)

                params = st.experimental_get_query_params()
                if 'selected_age' in params:
                    try:
                        val = int(params['selected_age'][0])
                        st.session_state.selected_age = val
                        st.session_state.current_page = 'planning'
                        # ensure main() shows the planning UI after click
                        st.session_state['action_override'] = "📋 查看規劃"
                        st.query_params.clear()
                        # use safe rerun wrapper to avoid import-time errors
                        self.safe_rerun()
                    except Exception:
                        pass
                return
            except Exception:
                pass

        # Fallback: render matplotlib board and provide a grid of buttons
        # ensure a session_state value exists for board scale (default 0.7)
        if 'board_scale' not in st.session_state:
            st.session_state.board_scale = 0.7
        fig, squares = self.draw_monopoly_board_streamlit(scale=st.session_state.board_scale)
        st.pyplot(fig)
        # Provide a button grid for direct clicking
        # Build a grid layout similar to draw_monopoly_board
        ages = list(range(20, 66))
        bottom_ages = ages[:12]
        right_ages = ages[12:23]
        top_ages = ages[23:35]
        left_ages = ages[35:]

        # Compose grid rows (bottom row left->right)
        grid = []
        grid.append(list(bottom_ages))
        for a in reversed(right_ages):
            grid.append([None]*11 + [a])
        grid.append(list(reversed(top_ages)))
        for a in left_ages:
            grid.append([a] + [None]*11)

        # Render simple buttons
        for row in grid:
            cols = st.columns(len(row))
            for c, age in enumerate(row):
                with cols[c]:
                    if age is None:
                        st.write('')
                    else:
                        label = f"{age}歲"
                        if st.button(label, key=f"age_btn_{age}"):
                            st.session_state.selected_age = int(age)
                            st.session_state.current_page = 'planning'
                            # navigate to planning UI and request a rerun
                            try:
                                self.safe_rerun()
                            except Exception:
                                pass
                            # continue rendering so the edit selection and updated list appear
    def show_life_planning(self):
        """Show life planning UI inline (add/edit/delete) and support loan-type selection for 買房 events."""
        st.markdown("### 📋 規劃人生")

        # local copy of planning
        planning = st.session_state.get('life_planning', {})

        st.markdown("---")
        st.markdown("#### ➕ 新增人生規劃事件")
        with st.form("add_life_event_form"):
            col1, col2, col3 = st.columns([2,2,1])
            with col1:
                default_age = int(getattr(st.session_state, 'selected_age', 30))
                add_age = st.number_input("目標年齡", min_value=20, max_value=65, value=default_age, step=1)
                event_type = st.selectbox("事件類型", options=["結婚","生小孩","買房","買車","其他"])
            with col2:
                default_amount = 0
                if event_type == '買房':
                    default_amount = 15000000
                elif event_type == '買車':
                    default_amount = 300000
                elif event_type == '結婚':
                    default_amount = 300000
                elif event_type == '生小孩':
                    default_amount = 100000
                add_amount = st.number_input("金額 (選填)", value=float(default_amount), min_value=0.0, step=1000.0)
            with col3:
                add_desc = st.text_input("描述 (選填)", value="")
            # Additional inputs for buy house
            house_options = None
            if event_type == '買房':
                st.markdown("##### 買房選項")
                colh1, colh2 = st.columns(2)
                with colh1:
                    house_price = default_amount
                    #house_price = st.number_input("房價", value=float(add_amount), step=10000.0)
                    down_payment_ratio = st.slider("頭期款比例 (%)", 0, 100, 20)
                with colh2:
                    loan_rate = st.number_input("利率 (%)", value=3.0, step=0.01)
                    loan_years = st.number_input("貸款年數", min_value=1, max_value=40, value=30)
                    loan_type = st.selectbox("貸款類型", options=["本金平均攤還", "本息平均攤還"])
                house_options = {
                    'house_price': float(house_price),
                    'down_payment_ratio': down_payment_ratio,
                    'loan_rate': float(loan_rate)/100.0,
                    'loan_years': int(loan_years),
                    'loan_type': loan_type,
                    'down_payment': float(house_price) * (down_payment_ratio/100.0)
                }

            submitted = st.form_submit_button("➕ 新增事件")
            if submitted:
                age_key = str(int(add_age))  # Convert to string for consistency with cache
                ev = {'type': event_type, 'description': add_desc or None, 'amount': float(add_amount) if add_amount and add_amount>0 else None}
                if house_options:
                    ev['house_data'] = house_options

                # Safely mutate the session-level planning dict directly so we
                # avoid any local-copy confusion across reruns.
                try:
                    s_plan = st.session_state.get('life_planning') or {}
                    s_plan.setdefault(age_key, []).append(ev)
                    st.session_state['life_planning'] = s_plan
                except Exception:
                    # fallback: write via attribute access
                    try:
                        st.session_state.life_planning = planning
                    except Exception:
                        pass

                # mirror into instance so board drawing and other instance methods see the update
                try:
                    self.life_planning = st.session_state.get('life_planning', {})
                except Exception:
                    pass

                try:
                    self.log_event(f"✅ 新增規劃: {age_key}歲 - {event_type} ({ev.get('amount')})")
                except Exception:
                    pass
                # save to cache (write session-level planning)
                try:
                    if os.path.exists(self.cache_file):
                        with open(self.cache_file, 'r', encoding='utf-8') as f:
                            cached = json.load(f)
                    else:
                        cached = {}
                    cached['life_planning'] = st.session_state.get('life_planning', {})
                    with open(self.cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cached, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                st.success(f"已在 {age_key} 歲新增：{event_type}")
                if 'selected_age' in st.session_state:
                    try:
                        del st.session_state['selected_age']
                    except Exception:
                        st.session_state.pop('selected_age', None)

        # show existing planning
        if not planning:
            st.info("目前沒有任何人生規劃事件")
            return

        st.markdown("**📅 人生規劃事件:**")
        for age, events in sorted(planning.items(), key=lambda x: int(x[0])):
            with st.expander(f"{age}歲的規劃事件"):
                for i, event in enumerate(events):
                    cols = st.columns([4,1,1])
                    with cols[0]:
                        st.write(f"{i+1}. {event.get('type')}: {event.get('description','')}")
                        if event.get('amount'):
                            st.write(f"   金額: ${event.get('amount'):,.0f}")
                        if event.get('house_data'):
                            hd = event['house_data']
                            st.write(f"   房價: ${hd.get('house_price',0):,.0f}，頭期款: ${hd.get('down_payment',0):,.0f}，貸款類型: {hd.get('loan_type')}")
                    with cols[1]:
                        edit_key = f"edit_{age}_{i}"
                        if st.button("✏️ 編輯", key=edit_key):
                            st.session_state['edit_event_age'] = int(age)
                            st.session_state['edit_event_index'] = int(i)
                            # ensure we stay on the planning page and open edit (do not force rerun)
                            try:
                                st.session_state['action_override'] = '📋 查看規劃'
                                st.session_state['sidebar_action'] = '📋 查看規劃'
                            except Exception:
                                pass
                            # continue rendering so the deletion is reflected immediately
                    with cols[2]:
                        del_key = f"delete_{age}_{i}"
                        if st.button("🗑️ 刪除", key=del_key):
                            try:
                                # age is already a string key from the iteration
                                age_key = str(age) if not isinstance(age, str) else age
                                if age_key in planning:
                                    planning[age_key].pop(i)
                                    if not planning[age_key]:
                                        del planning[age_key]
                                st.session_state.life_planning = planning
                                # mirror into instance and log
                                try:
                                    self.life_planning = planning
                                except Exception:
                                    pass
                                try:
                                    self.log_event(f"🗑️ 已刪除規劃: {age}歲 第{i+1}筆")
                                except Exception:
                                    pass
                                # save cache - removed for multi-user compatibility
                                st.rerun()
                            except Exception:
                                pass
                                # keep the UI on the planning page after deletion — only
                                # set a transient override so the planning UI is shown on
                                # the next run. Also log a snapshot for debugging.
                                try:
                                    st.session_state['action_override'] = '📋 查看規劃'
                                    st.session_state['sidebar_action'] = '📋 查看規劃'
                                    self.log_event('DEBUG after add: set sidebar_action and action_override')
                                except Exception:
                                    pass
                                try:
                                    self.log_event(f"DEBUG planning snapshot after delete: {json.dumps(planning, ensure_ascii=False)}")
                                except Exception:
                                    try:
                                        self.log_event(f"DEBUG planning snapshot after delete: {repr(planning)}")
                                    except Exception:
                                        pass
    
    def show_parameter_dialog_streamlit(self):
        """顯示參數設定對話框 - 轉換原始show_parameter_dialog邏輯"""
        st.subheader("🔧 個人參數設定")
    # Ensure widget-backed keys reflect the authoritative player_status
    # stored in session_state so widgets render the latest saved values.
        try:
            ps = st.session_state.get('player_status') or PlayerStatus()
            # Only set param_* keys if not already present (avoids overwriting
            # user-typed input when a rerun occurs due to Enter)
            try:
                if 'param_age' not in st.session_state:
                    st.session_state['param_age'] = int(getattr(ps, 'age', 25))
            except Exception:
                pass
            try:
                if 'param_monthly_income' not in st.session_state:
                    st.session_state['param_monthly_income'] = int(getattr(ps, 'monthly_income', 0))
            except Exception:
                pass
            try:
                if 'param_monthly_expense' not in st.session_state:
                    st.session_state['param_monthly_expense'] = int(getattr(ps, 'monthly_expense', 0))
            except Exception:
                pass
            try:
                if 'param_savings' not in st.session_state:
                    st.session_state['param_savings'] = int(getattr(ps, 'savings', 0))
            except Exception:
                pass
            try:
                if 'param_debt' not in st.session_state:
                    st.session_state['param_debt'] = int(getattr(ps, 'debt', 0))
            except Exception:
                pass
            # Initialize inflation widget state from current investment_config
            try:
                if 'param_inflation_pct' not in st.session_state:
                    ic_tmp = st.session_state.get('investment_config') or getattr(self, 'investment_config', None)
                    infl = float(getattr(ic_tmp, 'inflation_rate', 0.03) or 0.03) * 100
                    st.session_state['param_inflation_pct'] = float(infl)
            except Exception:
                pass
        except Exception:
            pass
        
        
        with st.form("parameter_form"):
            # 基本設定 - 完全照搬原始邏輯
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本資料**")
                age = st.number_input("目前年齡", min_value=18, max_value=65,
                                    value=int(st.session_state.get('param_age', int(getattr(self.player_status, 'age', 25)))), step=1, key='param_age')
                retirement_age = st.number_input("退休年齡", min_value=50, max_value=80, value=int(st.session_state.get('param_retirement_age', int(getattr(self.investment_config, 'retirement_age', 65)))), step=1, key='param_retirement_age')
                monthly_income = st.number_input("月收入", min_value=0,
                                               value=int(st.session_state.get('param_monthly_income', int(getattr(self.player_status, 'monthly_income', 0)))), step=1000, key='param_monthly_income')
                savings = st.number_input("目前儲蓄", min_value=0,
                                        value=int(st.session_state.get('param_savings', int(getattr(self.player_status, 'savings', 0)))), step=10000, key='param_savings')
            
            with col2:
                st.write("**支出與負債**")
                monthly_expense = st.number_input("月支出", min_value=0,
                                                value=int(st.session_state.get('param_monthly_expense', int(getattr(self.player_status, 'monthly_expense', 0)))), step=1000, key='param_monthly_expense')
                debt = st.number_input("目前負債", min_value=0,
                                     value=int(st.session_state.get('param_debt', int(getattr(self.player_status, 'debt', 0)))), step=10000, key='param_debt')
                # 年通膨率（提供成長年金現值等計算使用）
                inflation_pct = st.number_input(
                    "年通膨率 (%)",
                    min_value=0.0,
                    max_value=20.0,
                    value=float(st.session_state.get('param_inflation_pct', float(getattr(self.investment_config, 'inflation_rate', 0.03) * 100))),
                    step=0.1,
                    format="%.2f",
                    key='param_inflation_pct'
                )
            
            # --- 預設資產配置範本（不覆寫使用者個人化，按下「套用」時才會把數值複製到你的設定）
            st.markdown("### ⚙️ 預設資產配置範本")
            tcol1, tcol2, tcol3 = st.columns(3)

            # get a sensible current age for template calculations
            current_age = st.session_state.get('param_age', int(getattr(self.player_status, 'age', 30)))

            def _apply_120_age():
                ic = st.session_state.get('investment_config') or InvestmentConfig()
                # Use the current age from the form/session (forms update keys on submit)
                try:
                    age_for_calc = int(st.session_state.get('param_age', int(getattr(self.player_status, 'age', 30))))
                except Exception:
                    age_for_calc = int(getattr(self.player_status, 'age', 30))
                # 120-年齡法則：股票% = 120 - 年齡
                eq_pct = max(0, min(100, 120 - int(age_for_calc)))
                eq = eq_pct / 100.0  # 轉換為小數 (0-1)
                # distribute equally across age buckets so user can further微調
                ic.young_growth_ratio = eq
                ic.young_conservative_ratio = 1.0 - eq
                ic.young_cash_reserve_ratio = 0.0
                ic.middle_growth_ratio = eq
                ic.middle_conservative_ratio = 1.0 - eq
                ic.middle_cash_reserve_ratio = 0.0
                ic.old_growth_ratio = eq
                ic.old_conservative_ratio = 1.0 - eq
                ic.old_cash_reserve_ratio = 0.0
                # Directly update slider state so they display the template values
                try:
                    st.session_state['young_growth_pct'] = int(ic.young_growth_ratio * 100)
                    st.session_state['young_conservative_pct'] = int(ic.young_conservative_ratio * 100)
                    st.session_state['young_cash_pct'] = int(ic.young_cash_reserve_ratio * 100)
                    st.session_state['middle_growth_pct'] = int(ic.middle_growth_ratio * 100)
                    st.session_state['middle_conservative_pct'] = int(ic.middle_conservative_ratio * 100)
                    st.session_state['middle_cash_pct'] = int(ic.middle_cash_reserve_ratio * 100)
                    st.session_state['old_growth_pct'] = int(ic.old_growth_ratio * 100)
                    st.session_state['old_conservative_pct'] = int(ic.old_conservative_ratio * 100)
                    st.session_state['old_cash_pct'] = int(ic.old_cash_reserve_ratio * 100)
                except Exception:
                    pass
                st.session_state['investment_config'] = ic
                self.investment_config = ic
                # applying template updates session state only; do NOT auto-run simulation
                try:
                    self.log_event(f"套用範本: 120-年齡法則（年齡={age_for_calc}，股票比例={eq*100:.0f}%）")
                except Exception:
                    pass

            def _apply_glide_path():
                ic = st.session_state.get('investment_config') or InvestmentConfig()
                ic.young_growth_ratio = 0.85
                ic.young_conservative_ratio = 0.15
                ic.young_cash_reserve_ratio = 0.0
                ic.middle_growth_ratio = 0.75
                ic.middle_conservative_ratio = 0.25
                ic.middle_cash_reserve_ratio = 0.0
                ic.old_growth_ratio = 0.55
                ic.old_conservative_ratio = 0.45
                ic.old_cash_reserve_ratio = 0.0
                # Directly update slider state so they display the template values
                try:
                    st.session_state['young_growth_pct'] = int(ic.young_growth_ratio * 100)
                    st.session_state['young_conservative_pct'] = int(ic.young_conservative_ratio * 100)
                    st.session_state['young_cash_pct'] = int(ic.young_cash_reserve_ratio * 100)
                    st.session_state['middle_growth_pct'] = int(ic.middle_growth_ratio * 100)
                    st.session_state['middle_conservative_pct'] = int(ic.middle_conservative_ratio * 100)
                    st.session_state['middle_cash_pct'] = int(ic.middle_cash_reserve_ratio * 100)
                    st.session_state['old_growth_pct'] = int(ic.old_growth_ratio * 100)
                    st.session_state['old_conservative_pct'] = int(ic.old_conservative_ratio * 100)
                    st.session_state['old_cash_pct'] = int(ic.old_cash_reserve_ratio * 100)
                except Exception:
                    pass
                st.session_state['investment_config'] = ic
                self.investment_config = ic
                # applying template updates session state only; do NOT auto-run simulation
                try:
                    self.log_event("套用範本: Glide Path（動態曲線示例）")
                except Exception:
                    pass

            def _apply_all_weather():
                ic = st.session_state.get('investment_config') or InvestmentConfig()
                ic.young_growth_ratio = 0.30
                ic.young_conservative_ratio = 0.55
                ic.young_cash_reserve_ratio = 0.15
                ic.middle_growth_ratio = 0.30
                ic.middle_conservative_ratio = 0.55
                ic.middle_cash_reserve_ratio = 0.15
                ic.old_growth_ratio = 0.30
                ic.old_conservative_ratio = 0.55
                ic.old_cash_reserve_ratio = 0.15
                # Directly update slider state so they display the template values
                try:
                    st.session_state['young_growth_pct'] = int(ic.young_growth_ratio * 100)
                    st.session_state['young_conservative_pct'] = int(ic.young_conservative_ratio * 100)
                    st.session_state['young_cash_pct'] = int(ic.young_cash_reserve_ratio * 100)
                    st.session_state['middle_growth_pct'] = int(ic.middle_growth_ratio * 100)
                    st.session_state['middle_conservative_pct'] = int(ic.middle_conservative_ratio * 100)
                    st.session_state['middle_cash_pct'] = int(ic.middle_cash_reserve_ratio * 100)
                    st.session_state['old_growth_pct'] = int(ic.old_growth_ratio * 100)
                    st.session_state['old_conservative_pct'] = int(ic.old_conservative_ratio * 100)
                    st.session_state['old_cash_pct'] = int(ic.old_cash_reserve_ratio * 100)
                except Exception:
                    pass
                st.session_state['investment_config'] = ic
                self.investment_config = ic
                # applying template updates session state only; do NOT auto-run simulation
                try:
                    self.log_event("套用範本: All-Weather（全天候）")
                except Exception:
                    pass

            # Use form_submit_button inside the same form (Streamlit disallows
            # regular st.button inside st.form). We capture which template was
            # pressed and handle it specially to avoid running the main save flow.
            with tcol1:
                st.markdown("**120 − 年齡法則**")
                st.write("股票比例 = max(0, 120 − 年齡)；其餘配置到債券/現金")
                st.write(f"預設計算年齡: {current_age}")
                apply_120 = st.form_submit_button("套用 120-年齡", key='apply_120_age')

            with tcol2:
                st.markdown("**Glide Path（動態曲線）**")
                st.write("年輕時高股權，隨年齡平滑降低到保守型")
                apply_glide = st.form_submit_button("套用 Glide Path", key='apply_glide')

            with tcol3:
                st.markdown("**All‑Weather（全天候）**")
                st.write("分散到股票、長短期債、替代資產（簡化映射到成長/保守/現金）")
                apply_all = st.form_submit_button("套用 All‑Weather", key='apply_allweather')

            # If a template button was pressed, apply the template and skip the
            # main save handler which runs below. This prevents accidental
            # double-handling of form submission.
            template_applied = False
            try:
                if apply_120:
                    _apply_120_age()
                    template_applied = True
                elif apply_glide:
                    _apply_glide_path()
                    template_applied = True
                elif apply_all:
                    _apply_all_weather()
                    template_applied = True
            except Exception:
                # non-fatal; allow normal save flow to continue if something fails
                template_applied = False

            st.markdown("---")
            
            # 投資設定 - 包含年齡分層與回報率（與 main_desktop.py 對齊）
            st.subheader("📈 投資設定")

            # Ensure widget-backed slider keys exist in session_state before
            # creating widgets. This prevents Streamlit warning when a widget is
            # created with a default while session_state already contains a value.
            try:
                defaults = {
                    'young_growth_pct': int(round(getattr(self.investment_config, 'young_growth_ratio', 0.0) * 100)),
                    'young_conservative_pct': int(round(getattr(self.investment_config, 'young_conservative_ratio', 0.0) * 100)),
                    'young_cash_pct': int(round(getattr(self.investment_config, 'young_cash_reserve_ratio', 0.0) * 100)),
                    'middle_growth_pct': int(round(getattr(self.investment_config, 'middle_growth_ratio', 0.0) * 100)),
                    'middle_conservative_pct': int(round(getattr(self.investment_config, 'middle_conservative_ratio', 0.0) * 100)),
                    'middle_cash_pct': int(round(getattr(self.investment_config, 'middle_cash_reserve_ratio', 0.0) * 100)),
                    'old_growth_pct': int(round(getattr(self.investment_config, 'old_growth_ratio', 0.0) * 100)),
                    'old_conservative_pct': int(round(getattr(self.investment_config, 'old_conservative_ratio', 0.0) * 100)),
                    'old_cash_pct': int(round(getattr(self.investment_config, 'old_cash_reserve_ratio', 0.0) * 100)),
                }
                for k, v in defaults.items():
                    if k not in st.session_state:
                        st.session_state[k] = v
                # Prefill at most once per session to avoid overriding template/user choices on later renders.
                if not st.session_state.get('_allocation_prefilled_once'):
                    def _prefill_if_all_zero(g_key, c_key, cash_key, age_for_calc: int):
                        g = int(st.session_state.get(g_key, 0) or 0)
                        c = int(st.session_state.get(c_key, 0) or 0)
                        h = int(st.session_state.get(cash_key, 0) or 0)
                        if (g + c + h) == 0:
                            eq = max(0, min(100, 120 - int(age_for_calc)))
                            st.session_state[g_key] = int(eq)
                            st.session_state[c_key] = int(100 - eq)
                            st.session_state[cash_key] = 0
                    try:
                        age_for_calc = int(st.session_state.get('param_age', int(getattr(self.player_status, 'age', 30))))
                    except Exception:
                        age_for_calc = int(getattr(self.player_status, 'age', 30))
                    _prefill_if_all_zero('young_growth_pct', 'young_conservative_pct', 'young_cash_pct', age_for_calc)
                    _prefill_if_all_zero('middle_growth_pct', 'middle_conservative_pct', 'middle_cash_pct', age_for_calc)
                    _prefill_if_all_zero('old_growth_pct', 'old_conservative_pct', 'old_cash_pct', age_for_calc)
                    st.session_state['_allocation_prefilled_once'] = True
            except Exception:
                pass
            col3, col4, col5 = st.columns(3)

            with col3:
                # use explicit keys so we can programmatically update sliders when a template is applied
                # CRITICAL: Use session_state directly, NOT self.investment_config default, to prevent
                # stale cached values from overriding template-applied values on reruns
                young_growth_pct = st.slider("40歲以下 成長型比例 (%)", 0, 100, key='young_growth_pct')
                young_conservative_pct = st.slider("40歲以下 保守型比例 (%)", 0, 100, key='young_conservative_pct')
                young_cash_pct = st.slider("40歲以下 現金保留比例 (%)", 0, 100, key='young_cash_pct')

            with col4:
                middle_growth_pct = st.slider("41-55歲 成長型比例 (%)", 0, 100, key='middle_growth_pct')
                middle_conservative_pct = st.slider("41-55歲 保守型比例 (%)", 0, 100, key='middle_conservative_pct')
                middle_cash_pct = st.slider("41-55歲 現金保留比例 (%)", 0, 100, key='middle_cash_pct')

            with col5:
                old_growth_pct = st.slider("55歲以上 成長型比例 (%)", 0, 100, key='old_growth_pct')
                old_conservative_pct = st.slider("55歲以上 保守型比例 (%)", 0, 100, key='old_conservative_pct')
                old_cash_pct = st.slider("55歲以上 現金保留比例 (%)", 0, 100, key='old_cash_pct')
            
            # 投資回報設定
            st.subheader("📉 投資回報設定")
            col6, col7, col8 = st.columns(3)
            with col6:
                growth_return_rate = st.number_input("成長型年報酬率 (%)", value=float(getattr(self.investment_config, 'growth_return_rate', 0.07) * 100), step=0.1, format="%.2f")
            with col7:
                conservative_return_rate = st.number_input("保守型年報酬率 (%)", value=float(getattr(self.investment_config, 'conservative_return_rate', 0.03) * 100), step=0.1, format="%.2f")
            with col8:
                cash_return = st.number_input("現金年利率 (%)", value=float(getattr(self.investment_config, 'cash_return', 0.02) * 100), step=0.01, format="%.2f")
            
            # 薪資成長設定 - 完全照搬原始邏輯
            st.subheader("💼 薪資成長設定")
            col9, col10 , col11 = st.columns(3)

            with col9:
                young_growth = st.number_input("年輕期成長率 (%) (25-50歲)", 
                                             value=float(self.salary_config.young_growth_rate * 100), 
                                             step=0.1, format="%.1f")
            with col10:
                middle_growth = st.number_input("中年期成長率 (%) (51-55歲)", 
                                              value=float(self.salary_config.middle_growth_rate * 100), 
                                              step=0.1, format="%.1f")

            with col11:
                decline_rate = st.number_input("56歲薪資降幅 (%)", 
                                             value=float(self.salary_config.senior_decline_rate * 100), 
                                             step=0.1, format="%.1f")
                #young_age_limit = st.number_input("年輕期上限", min_value=25, max_value=60, 
                #                                value=int(self.salary_config.young_age_limit), step=1)
            
            submitted = st.form_submit_button("💾 保存設定")
            
            if submitted:
                # Debug: announce form submit (stdout + UI log) so we can trace submission
                try:
                    print(f"PARAM_FORM_SUBMIT: age={age}, retirement_age={retirement_age}, income={monthly_income}, expense={monthly_expense}, savings={savings}, debt={debt}")
                    sys.stdout.flush()
                except Exception:
                    pass
                try:
                    self.log_event(f"PARAM_FORM_SUBMIT: age={age}, income={monthly_income}, expense={monthly_expense}")
                except Exception:
                    pass

                # 更新玩家狀態 - 寫入 session_state 的物件以確保跨 rerun 一致
                try:
                    ps = st.session_state.get('player_status') or PlayerStatus()
                    ps.age = age
                    ps.monthly_income = monthly_income
                    ps.monthly_expense = monthly_expense
                    ps.savings = savings
                    ps.debt = debt
                    st.session_state['player_status'] = ps
                    self.player_status = ps
                except Exception:
                    try:
                        self.player_status.age = age
                        self.player_status.monthly_income = monthly_income
                        self.player_status.monthly_expense = monthly_expense
                        self.player_status.savings = savings
                        self.player_status.debt = debt
                        st.session_state['player_status'] = self.player_status
                    except Exception:
                        pass

                # Also sync the individual widget-backed keys so widget state
                # won't later overwrite the updated player_status when widgets
                # are re-rendered. This prevents the main board from showing
                # stale values coming from leftover widget state.
                try:
                    st.session_state['param_age'] = int(age)
                    st.session_state['param_monthly_income'] = int(monthly_income)
                    st.session_state['param_monthly_expense'] = int(monthly_expense)
                    st.session_state['param_savings'] = int(savings)
                    st.session_state['param_debt'] = int(debt)
                    # keep inflation widget state synced
                    try:
                        st.session_state['param_inflation_pct'] = float(inflation_pct)
                    except Exception:
                        pass
                except Exception:
                    # non-fatal; continue without blocking save
                    pass

                # 更新投資設定（年齡分層與回報率）直接到 session_state — strictly use slider values
                try:
                    ic = st.session_state.get('investment_config') or InvestmentConfig()
                    ic.retirement_age = retirement_age
                    ic.young_growth_ratio = (int(st.session_state.get('young_growth_pct', 0)) or 0) / 100.0
                    ic.young_conservative_ratio = (int(st.session_state.get('young_conservative_pct', 0)) or 0) / 100.0
                    ic.young_cash_reserve_ratio = (int(st.session_state.get('young_cash_pct', 0)) or 0) / 100.0
                    ic.middle_growth_ratio = (int(st.session_state.get('middle_growth_pct', 0)) or 0) / 100.0
                    ic.middle_conservative_ratio = (int(st.session_state.get('middle_conservative_pct', 0)) or 0) / 100.0
                    ic.middle_cash_reserve_ratio = (int(st.session_state.get('middle_cash_pct', 0)) or 0) / 100.0
                    ic.old_growth_ratio = (int(st.session_state.get('old_growth_pct', 0)) or 0) / 100.0
                    ic.old_conservative_ratio = (int(st.session_state.get('old_conservative_pct', 0)) or 0) / 100.0
                    ic.old_cash_reserve_ratio = (int(st.session_state.get('old_cash_pct', 0)) or 0) / 100.0
                    ic.growth_return_rate = growth_return_rate / 100
                    ic.conservative_return_rate = conservative_return_rate / 100
                    ic.cash_return = cash_return / 100
                    # 更新年通膨率（由支出與負債區塊輸入）
                    try:
                        ic.inflation_rate = (st.session_state.get('param_inflation_pct', 3.0) or 3.0) / 100.0
                    except Exception:
                        ic.inflation_rate = getattr(ic, 'inflation_rate', 0.03)
                    st.session_state['investment_config'] = ic
                    self.investment_config = ic
                except Exception:
                    pass

                # 更新薪資設定
                try:
                    sc = st.session_state.get('salary_config') or SalaryConfig()
                    sc.young_growth_rate = young_growth / 100
                    sc.middle_growth_rate = middle_growth / 100
                    sc.senior_decline_rate = decline_rate / 100
                    st.session_state['salary_config'] = sc
                    self.salary_config = sc
                except Exception:
                    pass

                # 保存到快取
                self.save_settings_to_cache()
                
                # Debug: log what was actually saved
                try:
                    ic = st.session_state.get('investment_config')
                    if ic:
                        print(f"SAVED TO CACHE: young={ic.young_growth_ratio:.2f}/{ic.young_conservative_ratio:.2f}/{ic.young_cash_reserve_ratio:.2f}, middle={ic.middle_growth_ratio:.2f}/{ic.middle_conservative_ratio:.2f}/{ic.middle_cash_reserve_ratio:.2f}, old={ic.old_growth_ratio:.2f}/{ic.old_conservative_ratio:.2f}/{ic.old_cash_reserve_ratio:.2f}")
                        sys.stdout.flush()
                except Exception as e:
                    print(f"DEBUG ERROR: {e}")
                    sys.stdout.flush()

                # 讀回快取的 initial_settings 並寫入日誌，便於在 UI 中確認
                try:
                    if os.path.exists(self.cache_file):
                        with open(self.cache_file, 'r', encoding='utf-8') as f:
                            cached = json.load(f)
                        init = cached.get('initial_settings', {})
                        self.log_event(f"💾 快取已寫入 initial_settings: {init}")
                except Exception:
                    pass

                try:
                    print("PARAM_FORM_SAVED: cache written")
                    sys.stdout.flush()
                except Exception:
                    pass

                # Mark settings as saved (do not force navigation or rerun)
                try:
                    st.session_state['params_saved'] = True
                except Exception:
                    pass
                # Keep the UI on the settings page so the user sees the confirmation
                try:
                    st.session_state['sidebar_action'] = '🔧 個人設定'
                except Exception:
                    pass

                # Mark a new parameters version so the UI and simulation can
                # detect whether existing simulation results are stale.
                try:
                    import time
                    st.session_state['params_version'] = time.time()
                except Exception:
                    try:
                        st.session_state['params_version'] = 1
                    except Exception:
                        pass

                # Inform the user that settings were saved
                try:
                    st.success("✅ 設定已保存！")
                except Exception:
                    pass

                # Trigger a rerun so the sidebar/main UI refreshes and reflects the new params
                try:
                    self.safe_rerun()
                except Exception:
                    pass
    
    def show_charts_streamlit(self):
        """顯示圖表分析 - 完全照搬原始show_charts邏輯"""
        st.subheader("📊 財務分析圖表")
        
        if not self.simulation_results:
            st.warning("請先執行完整模擬以查看圖表")
            if st.button("🚀 立即執行模擬"):
                self.run_full_simulation()
                self.safe_rerun()

        # Debug helper: a small out-of-form button to force-save current param keys
        # This helps diagnose if the browser is failing to submit form data.
        try:
            psnap_age = st.session_state.get('param_age', None)
        except Exception:
            psnap_age = None
        
        # 準備數據 - 完全照搬原始邏輯
        ages = []
        net_worths = []
        incomes = []
        expenses = []
        stocks = []
        bonds = []
        debts = []

        for age_key, data in sorted(self.simulation_results.items(), key=lambda x: int(x[0])):
            # Ensure age is an int (JSON keys may be strings)
            try:
                age = int(age_key)
            except Exception:
                try:
                    age = int(float(age_key))
                except Exception:
                    # skip unparseable keys
                    continue
            if not isinstance(data, dict):
                # skip invalid entries
                continue
            ages.append(age)
            # compute net worth from components (exclude mortgage debt)
            sv = float(data.get('savings', 0) or 0)
            si = float(data.get('stock_investment', 0) or 0)
            bi = float(data.get('bond_investment', 0) or 0)
            ci = float(data.get('cash_investment', 0) or 0)
            nw = sv + si + bi + ci
            net_worths.append(nw)
            mi = float(data.get('monthly_income', 0) or 0)
            me = float(data.get('monthly_expense', 0) or 0)
            incomes.append(mi * 12)
            expenses.append(me * 12)
            stocks.append(si)
            bonds.append(bi)
            debts.append(float(data.get('debt', 0) or 0))
        
        # Render all charts on the page in a compact 2-per-row layout
        # Choose an available CJK-capable font at runtime to avoid missing-glyph boxes on macOS.
        try:
            import matplotlib.font_manager as fm

            candidates = [
                'Noto Sans CJK TC', 'Noto Sans CJK JP', 'Noto Sans CJK SC', 'PingFang TC',
                'PingFang', 'AppleGothic', 'Heiti TC', 'Microsoft JhengHei', 'SimHei',
                'Arial Unicode MS', 'Source Han Sans TW', 'Source Han Sans CN', 'Source Han Serif SC',
            ]

            available = {f.name for f in fm.fontManager.ttflist}
            chosen = None
            for c in candidates:
                if c in available:
                    chosen = c
                    break

            if not chosen:
                # try substring matches
                for f in fm.fontManager.ttflist:
                    lname = f.name.lower()
                    for sub in ['noto', 'pingfang', 'heiti', 'jhenghei', 'simhei', 'source han', 'arial unicode']:
                        if sub in lname:
                            chosen = f.name
                            break
                    if chosen:
                        break

            if not chosen:
                chosen = 'DejaVu Sans'

            plt.rcParams['font.family'] = chosen
        except Exception:
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

        plt.rcParams['axes.unicode_minus'] = False

        figs = []

        # 1) 淨資產成長趨勢 - 使用 Plotly 提供互動 hover（若不可用則回退到 Matplotlib）
        try:
            import plotly.graph_objects as go

            # prepare arrays
            x = list(ages)
            y = list(net_worths)

            # positive and negative areas for different fills
            y_pos = [v if v >= 0 else 0 for v in y]
            y_neg = [v if v < 0 else 0 for v in y]

            fig_plotly = go.Figure()
            # line trace
            fig_plotly.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='淨資產',
                                            line=dict(color='#0000f5', width=2),
                                            hovertemplate='年齡: %{x}<br>淨資產: $%{y:,.0f}<extra></extra>'))
            # positive fill
            fig_plotly.add_trace(go.Scatter(x=x, y=y_pos, mode='none', fill='tozeroy',
                                            fillcolor='rgba(0,0,245,0.12)', showlegend=False))
            # negative fill
            fig_plotly.add_trace(go.Scatter(x=x, y=y_neg, mode='none', fill='tozeroy',
                                            fillcolor='rgba(255,107,107,0.12)', showlegend=False))

            fig_plotly.update_layout(title='淨資產成長趨勢', xaxis_title='年齡', yaxis_title='淨資產 ($)',
                                     template='plotly_white', height=360)
            # format y-axis to show commas and dollar sign in hover
            fig_plotly.update_yaxes(tickprefix='$', separatethousands=True)

            # render Plotly chart directly (interactive)
            st.plotly_chart(fig_plotly, use_container_width=True)
        except Exception:
            # fallback to Matplotlib if Plotly not available
            fig1, ax = plt.subplots(figsize=(6, 3.6))
            # color matched to figures.png (bright blue)
            net_color = '#0000f5'
            neg_fill_color = '#FF6B6B'
            ax.plot(ages, net_worths, color=net_color, linewidth=2, label='淨資產', marker='o')
            ax.axhline(0, color='black', linewidth=0.8, alpha=0.7)
            nw_arr = np.array(net_worths)
            if len(nw_arr) > 0:
                mask_pos = (nw_arr >= 0).tolist()
                mask_neg = (nw_arr < 0).tolist()
                ax.fill_between(ages, nw_arr, 0, where=mask_pos, interpolate=True, alpha=0.25, color=net_color)
                ax.fill_between(ages, nw_arr, 0, where=mask_neg, interpolate=True, alpha=0.25, color=neg_fill_color)
            ax.set_title('淨資產成長趨勢', fontsize=12, weight='bold')
            ax.set_xlabel('年齡')
            ax.set_ylabel('淨資產 ($)')
            ax.grid(True, alpha=0.25)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            figs.append(fig1)

        # 2) 月度現金流（還原原始月度現金流圖）
        monthly_surplus = []
        monthly_income_vals = []
        monthly_expense_vals = []
        monthly_withdrawn_vals = []
        for age, data in sorted(self.simulation_results.items()):
            mi = data.get('monthly_income', 0)
            me = data.get('monthly_expense', 0)
            mh = data.get('monthly_house_payment', 0)
            monthly_surplus.append(mi - me - mh)
            monthly_income_vals.append(mi)
            monthly_expense_vals.append(me + mh)
            # use stored yearly_withdrawn if present (divide by 12 for monthly average), else 0
            yw = data.get('yearly_withdrawn', 0)
            monthly_withdrawn_vals.append(yw / 12.0 if yw else 0)

        fig2, ax = plt.subplots(figsize=(6, 3.6))
        if monthly_income_vals:
            # stacked bars: income (green) on bottom, expense (red) above (as positive), withdrawal (yellow) overlay when expense>income
            # We'll plot income as positive green bars, then plot expense as red bars representing outflows (plotted negative for visual), and overlay withdrawn portion in yellow on top of red where applicable.
            income_c = '#64a456'  # green
            expense_c = '#FF6B6B'  # red
            withdrawn_c = '#F4D35E'  # yellow (visible on sample)

            x = np.array(ages)
            inc = np.array(monthly_income_vals)
            exp = np.array(monthly_expense_vals)
            wdr = np.array(monthly_withdrawn_vals)

            # Plot income as upward bars
            ax.bar(x, inc, color=income_c, label='月收入', alpha=0.9)

            # Plot expense as negative bars so they appear below zero line
            ax.bar(x, -exp, color=expense_c, label='月支出', alpha=0.9)

            # For withdrawn portion, show it as downward yellow segment representing how much of expense required drawing from investments
            # Withdrawn cannot exceed expense; ensure clipped
            wdr_clipped = np.minimum(wdr, exp)
            ax.bar(x, -wdr_clipped, color=withdrawn_c, label='動用投資/現金補足差額', alpha=0.95)

            ax.set_title('月度現金流（綠=收入，紅=支出，黃=動用投資補足差）', fontsize=12, weight='bold')
            ax.set_xlabel('年齡')
            ax.set_ylabel('金額 ($)')
            ax.axhline(0, color='black', linewidth=0.8)
            ax.grid(True, alpha=0.25)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            ax.legend(loc='upper right', fontsize=9)
            if len(ages) > 0:
                ax.set_xlim(min(ages) - 1, max(ages) + 1)
        else:
            ax.text(0.5, 0.5, '無數據', ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('月度現金流', fontsize=12, weight='bold')
        figs.append(fig2)

        # 3) 資產配置趨勢（成長/防禦/現金） - stacked area
        growth_vals = stocks
        conservative_vals = bonds
        cash_vals = []
        for age, data in sorted(self.simulation_results.items()):
            cash_vals.append(data.get('savings', 0) + data.get('cash_investment', 0))

        fig3, ax = plt.subplots(figsize=(6, 3.6))
        if any((np.array(growth_vals) + np.array(conservative_vals) + np.array(cash_vals)) > 0):
            # match stacked colors from figures.png samples
            stack_colors = ['#0000f5', '#77b06c', '#f7eedb']
            ax.stackplot(ages, growth_vals, conservative_vals, cash_vals, labels=['成長(股票)', '防禦(債券)', '現金'], colors=stack_colors, alpha=0.9)
            ax.set_title('資產配置趨勢 (成長/防禦/現金)', fontsize=12, weight='bold')
            ax.set_xlabel('年齡')
            ax.set_ylabel('金額 ($)')
            ax.legend(loc='upper left', fontsize=9)
            ax.grid(True, alpha=0.25)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
        else:
            ax.text(0.5, 0.5, '無投資數據', ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('資產配置趨勢 (成長/防禦/現金)', fontsize=12, weight='bold')
        figs.append(fig3)

        # 4) 投資組合分布（圓餅圖，使用最後一年數據）
        fig4, ax = plt.subplots(figsize=(8, 3.6))
        # Choose retirement-age snapshot; fallback to latest available if exact age not present
        target_age = int(getattr(self.investment_config, 'retirement_age', 65) or 65)
        snap = None
        if self.simulation_results:
            # exact retirement age if present
            try:
                for k, v in self.simulation_results.items():
                    try:
                        if int(k) == target_age:
                            snap = v
                            break
                    except Exception:
                        continue
                if snap is None:
                    # fallback to the latest age prior to retirement
                    latest_age = max(int(k) for k in self.simulation_results.keys())
                    for k, v in self.simulation_results.items():
                        try:
                            if int(k) == latest_age:
                                snap = v
                                break
                        except Exception:
                            continue
            except Exception:
                snap = None
        if snap is None and self.financial_results:
            # fallback: last monthly record at or before retirement_age, else last overall
            try:
                candidates = [r for r in self.financial_results if int(getattr(r, 'age', -1)) == target_age]
                last = candidates[-1] if candidates else self.financial_results[-1]
                snap = {
                    'stock_investment': float(getattr(last, 'stock_investment', 0) or 0),
                    'bond_investment': float(getattr(last, 'bond_investment', 0) or 0),
                    'cash_investment': float(getattr(last, 'cash_investment', 0) or 0),
                    'savings': float(getattr(last, 'savings', 0) or 0),
                }
            except Exception:
                snap = None

        if isinstance(snap, dict):
            stock = max(0.0, float(snap.get('stock_investment', 0) or 0))
            bond = max(0.0, float(snap.get('bond_investment', 0) or 0))
            cash = max(0.0, float(snap.get('cash_investment', 0) or 0) + float(snap.get('savings', 0) or 0))
            total = stock + bond + cash
        else:
            stock = bond = cash = total = 0.0

        labels = ['股票', '債券', '現金']
        colors_pie = ['#0000f5', '#77b06c', '#f7eedb']
        if total > 0:
            vals = [stock, bond, cash]
            ax.pie(vals, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
            # Create legend with color mapping
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', markerfacecolor='#0000f5', markersize=10, label='股票 (成長型)'),
                Line2D([0], [0], marker='o', color='w', markerfacecolor='#77b06c', markersize=10, label='債券 (防禦型)'),
                Line2D([0], [0], marker='o', color='w', markerfacecolor='#f7eedb', markersize=10, label='現金 (保留)', markeredgecolor='gray', markeredgewidth=0.5)
            ]
            ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)
            ax.set_title('投資組合分佈（退休時）', fontsize=12, weight='bold')
        else:
            ax.text(0.5, 0.5, '無投資數據', ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('投資組合分佈（退休時）', fontsize=12, weight='bold')
        figs.append(fig4)

        # 5) 房貸分析
        fig5, ax = plt.subplots(figsize=(6, 3.6))
        if any(debt > 0 for debt in debts):
            debt_color = '#FF6B6B'
            ax.plot(ages, debts, color=debt_color, linewidth=2, label='房貸餘額', marker='o')
            ax.fill_between(ages, 0, debts, alpha=0.2, color=debt_color)
            ax.set_title('房貸變化趨勢', fontsize=12, weight='bold')
            ax.set_xlabel('年齡')
            ax.set_ylabel('房貸金額 ($)')
            ax.grid(True, alpha=0.25)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
        else:
            ax.text(0.5, 0.5, '目前沒有房貸記錄', ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('房貸分析', fontsize=12, weight='bold')
        figs.append(fig5)

        # Display all figures two-per-row
        for i in range(0, len(figs), 2):
            cols = st.columns(2)
            with cols[0]:
                st.pyplot(figs[i])
                plt.close(figs[i])
            if i + 1 < len(figs):
                with cols[1]:
                    st.pyplot(figs[i + 1])
                    plt.close(figs[i + 1])
            else:
                cols[1].empty()
    
    def create_medical_emergency_event_streamlit(self):
        impact = -random.randint(30000, 200000)
        return {'name': f'意外醫療支出（{abs(impact):,}元）', 'impact': impact}

    def create_loan_default_event_streamlit(self):
        impact = -random.randint(20000, 150000)
        return {'name': f'借貸被賴帳（{abs(impact):,}元）', 'impact': impact}

    def create_investment_loss_event_streamlit(self):
        impact = -random.randint(50000, 300000)
        return {'name': f'投資損失（{abs(impact):,}元）', 'impact': impact}

    def create_car_damage_event_streamlit(self):
        impact = -random.randint(10000, 100000)
        return {'name': f'車禍維修（{abs(impact):,}元）', 'impact': impact}

    def create_business_failure_event_streamlit(self):
        impact = -random.randint(50000, 500000)
        return {'name': f'生意失敗（{abs(impact):,}元）', 'impact': impact}

    def create_job_loss_event_streamlit(self):
        months_loss = random.randint(2, 12)
        impact = - (self.player_status.monthly_income * months_loss)
        return {'name': f'裁員失業（{months_loss}個月無收入）', 'impact': impact}

    def roll_double_dice_streamlit(self, current_age):
        age_dice = random.randint(1, 6)
        event_dice = random.randint(1, 6)
        min_age = max(int(current_age), int(self.player_status.age))
        max_age = int(self.investment_config.retirement_age) - 1
        if min_age >= max_age:
            trigger_age = min_age
        else:
            trigger_age = random.randint(min_age, max_age)
        events = {
            1: self.create_medical_emergency_event_streamlit(),
            2: self.create_loan_default_event_streamlit(),
            3: self.create_investment_loss_event_streamlit(),
            4: self.create_car_damage_event_streamlit(),
            5: self.create_business_failure_event_streamlit(),
            6: self.create_job_loss_event_streamlit()
        }
        event_info = events[event_dice]
        return age_dice, event_dice, event_info['name'], event_info['impact'], trigger_age

    def add_dice_event_to_planning(self, trigger_age, event_name, financial_impact):
        if trigger_age not in self.life_planning:
            self.life_planning[trigger_age] = []
        dice_event = {'type': '骰子事件', 'description': event_name, 'financial_impact': financial_impact, 'source': 'dice_game'}
        self.life_planning[trigger_age].append(dice_event)
        # mirror session state
        st.session_state.life_planning = self.life_planning
        self.log_event(f"🎲 {trigger_age}歲骰子事件：{event_name}（{financial_impact:+,}元）")

    def mark_event_on_board_streamlit(self, age, event_name, financial_impact, event_type='dice'):
        # Mirror main_desktop.mark_event_on_board behavior by recording event into life_planning and logging
        try:
            if age not in self.life_planning:
                self.life_planning[age] = []

            ev = {
                'type': event_type,
                'description': event_name,
                'financial_impact': financial_impact,
                'source': 'dice_game' if event_type == 'dice' else 'planning'
            }
            self.life_planning[age].append(ev)
            st.session_state.life_planning = self.life_planning
            self.log_event(f"📍 在棋盤標注事件: {age}歲 - {event_name} ({financial_impact:+,} 元)")
            # 保存到快取（保留設定與規劃）
            try:
                # load existing cache if any
                if os.path.exists(self.cache_file):
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cached = json.load(f)
                else:
                    cached = {}

                cached['life_planning'] = self.life_planning
                cached['random_events'] = self.random_events
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cached, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        except Exception as e:
            self.log_event(f"⚠️ 在棋盤標注事件失敗: {e}")
    
    def show_dice_ui(self):
        current_age = int(self.player_status.age)
        st.write(f"目前年齡: {current_age} 歲，事件可能發生在 {current_age} ~ {self.investment_config.retirement_age-1} 歲之間")
        if st.button("擲骰子，產生隨機事件"):
            age_dice, event_dice, event_name, impact, trigger_age = self.roll_double_dice_streamlit(current_age)
            # 儲存到人生規劃
            self.add_dice_event_to_planning(trigger_age, event_name, impact)
            # 保存快取
            self.save_settings_to_cache()
            st.success(f"骰子結果：{event_name}，觸發年齡：{trigger_age} 歲，影響：{impact:+,} 元")
            # do not rerun or stop; remain on current view so caller can continue rendering main board
            # mirror session state already performed in add_dice_event_to_planning
            return

    def check_fire_achievement(self):
        """
        檢查FIRE達成情況 (成長年金現值法 + 傳統25倍法則)
        
        NOTE: 實際計算已移至 core_private/fire_calculations.py
        此方法只負責 UI 日誌輸出
        """
        try:
            # 構建傳遞給核心計算的參數
            player_status = {
                'age': getattr(self.player_status, 'age', 25),
                'monthly_expense': getattr(self.player_status, 'monthly_expense', 0),
            }
            
            investment_config = {
                'retirement_age': getattr(self.investment_config, 'retirement_age', 65),
                'life_expectancy': getattr(self.investment_config, 'life_expectancy', 85),
                'inflation_rate': getattr(self.investment_config, 'inflation_rate', 0.03),
                'conservative_return_rate': getattr(self.investment_config, 'conservative_return_rate', 0.03),
            }
            
            # 呼叫核心計算模組
            result = check_fire_achievement(
                simulation_results=self.simulation_results,
                player_status=player_status,
                investment_config=investment_config
            )
            
            # 輸出結果到 UI
            self.log_event("🏁 FIRE 達成檢查：")
            
            if result['fire_age_growing']:
                self.log_event(f"🎯 成長年金現值法達成年齡: {result['fire_age_growing']}歲 (目標: ${result['fire_target_growing']:,.0f})")
            else:
                self.log_event(f"⚠️ 成長年金現值法未達成於模擬期間 (目標: ${result['fire_target_growing']:,.0f})")

            if result['fire_age_traditional']:
                self.log_event(f"📌 傳統25倍法則達成年齡: {result['fire_age_traditional']}歲 (目標: ${result['fire_target_traditional']:,.0f})")
            else:
                self.log_event(f"⚠️ 傳統25倍法則未達成於模擬期間 (目標: ${result['fire_target_traditional']:,.0f})")

            # 退休年齡摘要
            if result['retirement_status']:
                ret = result['retirement_status']
                self.log_event(f"💰 {ret['age']}歲淨資產: ${ret['net_worth']:,.0f}")
                self.log_event(f"💸 {ret['age']}歲年支出: ${ret['annual_expense']:,.0f}")
                self.log_event(f"🎯 25倍年支出目標: ${ret['annual_expense'] * 25:,.0f}")
                self.log_event(f"📈 4% 提領金額: ${ret['safe_withdrawal']:,.0f}")
                
                if ret['annual_expense'] > 0:
                    sustainability_ratio = ret['safe_withdrawal'] / ret['annual_expense']
                    self.log_event(f"📊 可持續性比率: {sustainability_ratio:.2f}")

        except Exception as e:
            import traceback
            self.log_event(f"❌ 計算 FIRE 達成時發生錯誤: {e}")
            try:
                traceback.print_exc()
            except Exception:
                pass


    def main(self):
        """主程式介面 - 完全模仿原始main_desktop.py的介面結構"""
        st.set_page_config(
            page_title="💰 FIRE理財規劃工具",
            page_icon="💰",
            layout= "wide",
            initial_sidebar_state="expanded"
        )
        
        st.markdown("""<style>
        #MainMenu, header, footer {display: none !important;}
        [data-testid="stToolbar"] {display: none !important;}
        </style>""", unsafe_allow_html=True)
        
        st.title("💰 FIRE理財規劃工具")
        st.markdown("---")

        # Ensure the in-memory instance reflects the session-authoritative player_status
        # and push those values back into the param_* widget keys so widgets do not
        # accidentally render older values from prior widget state and overwrite
        # the authoritative player_status on subsequent reruns.
        try:
            ps = st.session_state.get('player_status')
            if ps is not None:
                # mirror into instance
                self.player_status = ps
                # Only set widget-backed keys if they are not already present.
                # This avoids overwriting user-typed values during a rerun.
                try:
                    if 'param_age' not in st.session_state:
                        st.session_state['param_age'] = int(getattr(ps, 'age', 25))
                except Exception:
                    pass
                try:
                    if 'param_monthly_income' not in st.session_state:
                        st.session_state['param_monthly_income'] = int(getattr(ps, 'monthly_income', 0))
                except Exception:
                    pass
                try:
                    if 'param_monthly_expense' not in st.session_state:
                        st.session_state['param_monthly_expense'] = int(getattr(ps, 'monthly_expense', 0))
                except Exception:
                    pass
                try:
                    if 'param_savings' not in st.session_state:
                        st.session_state['param_savings'] = int(getattr(ps, 'savings', 0))
                except Exception:
                    pass
                try:
                    if 'param_debt' not in st.session_state:
                        st.session_state['param_debt'] = int(getattr(ps, 'debt', 0))
                except Exception:
                    pass
        except Exception:
            pass

        # Defensive sync: normally prefer widget-backed param_* keys when the
        # user is actively editing; however, immediately after a params save
        # the browser widgets may still hold stale values that would overwrite
        # the authoritative saved `player_status`. To avoid that race we
        # consume a one-shot 'params_saved' flag here and skip the widget->
        # player_status sync on that run. Subsequent runs will resume normal
        # defensive syncing.
        try:
            # Only consider widget-backed param_* keys when the user is actively
            # on the personal settings page. This avoids a scenario where stale
            # widget values (left in the browser) overwrite the authoritative
            # `player_status` when the user navigates back to the main board.
            current_action = st.session_state.get('sidebar_action')
            if st.session_state.get('params_saved'):
                # consume the flag and skip this sync to avoid stale widget values
                try:
                    st.session_state['params_saved'] = False
                except Exception:
                    try:
                        st.session_state.pop('params_saved', None)
                    except Exception:
                        pass
            elif current_action == '🔧 個人設定':
                # prefer explicit widget keys when present (only on settings page)
                p_age = st.session_state.get('param_age', None)
                p_income = st.session_state.get('param_monthly_income', None)
                p_expense = st.session_state.get('param_monthly_expense', None)
                p_savings = st.session_state.get('param_savings', None)
                p_debt = st.session_state.get('param_debt', None)
                changed = False
                ps = st.session_state.get('player_status') or PlayerStatus()
                if p_age is not None and getattr(ps, 'age', None) != int(p_age):
                    ps.age = int(p_age); changed = True
                if p_income is not None and getattr(ps, 'monthly_income', None) != int(p_income):
                    ps.monthly_income = int(p_income); changed = True
                if p_expense is not None and getattr(ps, 'monthly_expense', None) != int(p_expense):
                    ps.monthly_expense = int(p_expense); changed = True
                if p_savings is not None and getattr(ps, 'savings', None) != int(p_savings):
                    ps.savings = int(p_savings); changed = True
                if p_debt is not None and getattr(ps, 'debt', None) != int(p_debt):
                    ps.debt = int(p_debt); changed = True
                if changed:
                    st.session_state['player_status'] = ps
                    self.player_status = ps
                    try:
                        self.log_event(f"DEBUG sync_from_params: age={ps.age}, income={ps.monthly_income}, expense={ps.monthly_expense}")
                    except Exception:
                        pass
        except Exception:
            pass

        # Debug: record current navigation state and life_planning keys
        try:
            self.log_event(f"DEBUG run start: sidebar_action={st.session_state.get('sidebar_action')}, life_planning_keys={list(st.session_state.get('life_planning', {}).keys())}")
        except Exception:
            pass

        # Additional diagnostic info to help trace form submit / rerun behavior
        try:
            self.log_event(f"DEBUG params_saved={st.session_state.get('params_saved', False)}, action_override={st.session_state.get('action_override', None)}, param_monthly_income={st.session_state.get('param_monthly_income', None)}")
        except Exception:
            pass

        # Lightweight top navigation: Home button only (settings/help relocated to toolbar)
        try:
            nav_c1, _ = st.columns([1,9])
            with nav_c1:
                if st.button("🏠 主棋盤", key="nav_home"):
                    st.session_state['sidebar_action'] = '🏠 主棋盤'
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass
        except Exception:
            pass

        # If there are already simulation results in session_state (for example
        # produced by a previous run or loaded from cache), mirror them into
        # this instance so the UI will render results immediately without
        # requiring an extra restart. Also normalize string keys (from JSON)
        # into ints for consistent lookups.
        try:
            sess_sim = st.session_state.get('simulation_results', {}) or {}
            if sess_sim:
                try:
                    first_key = next(iter(sess_sim.keys()))
                    if isinstance(first_key, str):
                        normalized = {int(k): v for k, v in sess_sim.items()}
                    else:
                        normalized = dict(sess_sim)
                except Exception:
                    normalized = dict(sess_sim)

                # Mirror into instance and session_state
                self.simulation_results = normalized
                self.financial_results = st.session_state.get('financial_results', []) or []
                try:
                    st.session_state['simulation_results'] = self.simulation_results
                    st.session_state['financial_results'] = self.financial_results
                except Exception:
                    pass

                # If there are real results, clear any previous simulation error
                try:
                    st.session_state.pop('last_sim_error', None)
                except Exception:
                    pass

                # Ensure we show the main board when results exist
                try:
                    st.session_state['sidebar_action'] = st.session_state.get('sidebar_action', '🏠 主棋盤')
                except Exception:
                    pass
            
        except Exception:
            pass

        # If a start simulation was requested in the previous run, execute it now
        if st.session_state.get('run_simulation_now'):
            with st.spinner("執行模擬中..."):
                ok = self.run_full_simulation()
            if ok:
                # ensure session_state results are mirrored into this instance
                try:
                    st.session_state['simulation_results'] = st.session_state.get('simulation_results', self.simulation_results)
                    st.session_state['financial_results'] = st.session_state.get('financial_results', self.financial_results)
                except Exception:
                    pass
                try:
                    # mirror into in-memory attributes used for rendering
                    self.simulation_results = st.session_state.get('simulation_results', {}) or {}
                    self.financial_results = st.session_state.get('financial_results', []) or []
                except Exception:
                    pass
                try:
                    # ensure the UI shows the main board after run
                    # but if the run was triggered by a template Apply,
                    # don't force navigation (respect run_simulation_no_nav)
                    if not st.session_state.get('run_simulation_no_nav'):
                        st.session_state['sidebar_action'] = '🏠 主棋盤'
                except Exception:
                    pass
                try:
                    st.session_state.pop('last_sim_error', None)
                except Exception:
                    pass
                # If a template requested a simulation without navigation,
                # clear that request now so future runs behave normally.
                try:
                    if st.session_state.get('run_simulation_no_nav'):
                        st.session_state.pop('run_simulation_no_nav', None)
                except Exception:
                    pass
            else:
                try:
                    st.session_state['last_sim_error'] = 'run_full_simulation returned False'
                except Exception:
                    pass
            # clear the request so it won't run again automatically
            try:
                st.session_state['run_simulation_now'] = False
            except Exception:
                pass
        
        # Ensure instance mirrors session_state after any parameter updates so
        # UI reads are consistent.
        try:
            ss_ps = st.session_state.get('player_status')
            if ss_ps is not None:
                self.player_status = ss_ps
        except Exception:
            pass
        try:
            self.log_event(f"DEBUG sidebar sync: session_age={getattr(st.session_state.get('player_status', None), 'age', None)}, instance_age={getattr(self.player_status, 'age', None)}")
        except Exception:
            pass

        # 側邊欄 - 模仿原始左側狀態面板
        with st.sidebar:
            retirement_age = int(getattr(self.investment_config, 'retirement_age', 65) or 65)
            sim_raw = st.session_state.get('simulation_results', {})
            sim = {int(k) if isinstance(k, str) else k: v for k, v in sim_raw.items()}
            data = sim.get(retirement_age)
            if not data and sim:
                last_year = max(sim.keys())
                data = sim.get(last_year, {})
            if not isinstance(data, dict):
                data = {}
            st.header("💰 個人財務狀況")
            st.subheader("基本信息")
            st.write(f"**年齡**: {retirement_age}歲（退休年齡）")
            st.write(f"**淨資產**: ${data.get('net_worth', 0):,.0f}")
            st.subheader("投資組合（退休時）")
            st.write(f"**股票**: ${data.get('stock_investment', 0):,.0f}")
            st.write(f"**債券**: ${data.get('bond_investment', 0):,.0f}")
            st.write(f"**現金**: ${data.get('cash_investment', 0):,.0f}")
            st.write(f"**房地產**: ${data.get('real_estate_investment', 0):,.0f}")
 
            
        
        # Determine current action from session_state (sidebar_action) and
        # then honor any transient action_override set by board clicks.
        action = st.session_state.get('sidebar_action', '🏠 主棋盤')
        if 'action_override' in st.session_state:
            # Only honor known toolbar-driven overrides to avoid accidental navigation
            ao = st.session_state.get('action_override')
            if ao in ('🔧 個人設定', '📋 查看規劃', '❓ 使用說明', '🎲 人生骰子'):
                action = st.session_state.pop('action_override')
            else:
                # ignore unknown overrides but clear the key to avoid repeated effects
                try:
                    st.session_state.pop('action_override', None)
                except Exception:
                    pass
            # If board click requested to open planning, immediately render the planning UI
            # if action == "📋 查看規劃":
            #     selected = st.session_state.get('selected_age')
            #     if selected is not None:
            #         # brief visible confirmation so user knows click was received
            #         st.info(f"已選擇 {selected} 歲，正在打開規劃表單")
            #     # render planning UI immediately and stop further main content
            #     self.show_life_planning()
            #     return

        # 主要內容區域 - 完全模仿原始右側面板
        if action == "🏠 主棋盤":
            # 在棋盤上方顯示模擬結果摘要（預設 [待模擬]）
            st.subheader("📊 模擬結果摘要")
            # Debug indicator: always show counts so user can see whether results were
            # detected by the instance and session_state (temporary, safe to keep)
            try:
                sess_len = len(st.session_state.get('simulation_results', {}) or {})
            except Exception:
                sess_len = 'err'
            try:
                inst_len = len(self.simulation_results) if getattr(self, 'simulation_results', None) is not None else 'err'
            except Exception:
                inst_len = 'err'
            # st.caption(f"DEBUG: instance results={inst_len}  | session results={sess_len}")
            # top row: show placeholder or top metrics and a right-aligned start-simulation button
            top_cols = st.columns([2, 2, 1])
            if not self.simulation_results:
                # show retirement age from user settings, but reset numeric summaries to default/待模擬
                try:
                    retirement_age = int(getattr(self.investment_config, 'retirement_age', 65))
                except Exception:
                    retirement_age = 65
                final_age = retirement_age
                with top_cols[0]:
                    st.metric("最終年齡", f"{final_age}歲")
                with top_cols[1]:
                    st.metric("最終淨資產", f"$0")
            else:
                # If simulation exists but was run against different params, warn the user
                try:
                    pv = st.session_state.get('params_version')
                    spv = st.session_state.get('simulation_params_version')
                    if pv and spv and pv != spv:
                        with top_cols[0]:
                            st.warning("注意：現有模擬基於舊參數，請重新執行模擬以取得正確結果。")
                except Exception:
                    pass
                try:
                    # Show the user's configured retirement age as the summary '最終年齡'
                    retirement_age = int(getattr(self.investment_config, 'retirement_age', 65))
                    final_age = retirement_age
                    # If we have simulation results for the retirement age, show that net worth; otherwise fall back to the last available year or player_status
                    if self.simulation_results:
                        last_age = max(self.simulation_results.keys())
                        final_net_worth = self.simulation_results.get(final_age, self.simulation_results.get(last_age, {})).get('net_worth', getattr(self.player_status, 'net_worth', 0))
                    else:
                        final_net_worth = getattr(self.player_status, 'net_worth', 0)
                    with top_cols[0]:
                        st.metric("最終年齡", f"{final_age}歲")
                    with top_cols[1]:
                        st.metric("最終淨資產", f"${final_net_worth:,.0f}")
                except Exception as e:
                    # if anything goes wrong preparing metrics, show placeholder
                    with top_cols[0]:
                        st.info("[待模擬]")

            # (已移除) 右上開始模擬按鈕 - 改為在棋盤上方顯示快速工具列，並在棋盤下方置中放置主要「開始模擬」按鈕
            # show the four FIRE metrics (same compact view as 完整模擬)
            # If we just restarted, show placeholder metrics so UI reads as '待模擬'
            if st.session_state.get('just_restarted'):
                try:
                    fire_target = self.player_status.monthly_expense * 12 * 25
                except Exception:
                    fire_target = 0
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("4%法則 - 首次達成年齡", "待模擬")
                with c2:
                    st.metric("4%法則 - 目標金額", f"${fire_target:,.0f}")
                with c3:
                    st.metric("成長年金 - 首次達成年齡", "N/A")
                with c4:
                    st.metric("成長年金 - 目標金額", "N/A")
                try:
                    del st.session_state['just_restarted']
                except Exception:
                    pass
            elif self.simulation_results:
                try:
                    # 呼叫核心計算模組計算 FIRE 指標
                    player_status = {
                        'age': getattr(self.player_status, 'age', 25),
                        'monthly_expense': getattr(self.player_status, 'monthly_expense', 0),
                    }
                    
                    investment_config = {
                        'retirement_age': getattr(self.investment_config, 'retirement_age', 65),
                        'life_expectancy': getattr(self.investment_config, 'life_expectancy', 85),
                        'inflation_rate': getattr(self.investment_config, 'inflation_rate', 0.03),
                        'conservative_return_rate': getattr(self.investment_config, 'conservative_return_rate', 0.03),
                    }
                    
                    result = check_fire_achievement(
                        self.simulation_results,
                        player_status,
                        investment_config
                    )

                    retirement_age = investment_config['retirement_age']
                    fire_target_traditional = result['fire_target_traditional']
                    fire_target_growing_annuity = result['fire_target_growing']
                    first_age_traditional = result['fire_age_traditional']
                    first_age_growing = result['fire_age_growing']

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        # show first-achievement age only if it occurs on/before the configured retirement age
                        trad_age_disp = f"{first_age_traditional}歲" if (first_age_traditional and first_age_traditional <= retirement_age) else "未達成"
                        st.metric("4%法則 - 首次達成年齡", trad_age_disp)
                    with c2:
                        st.metric("4%法則 - 目標金額", f"${fire_target_traditional:,.0f}")
                    with c3:
                        grow_age_disp = f"{first_age_growing}歲" if (first_age_growing and first_age_growing <= retirement_age) else "未達成"
                        st.metric("成長年金 - 首次達成年齡", grow_age_disp)
                    with c4:
                        st.metric("成長年金 - 目標金額", f"${fire_target_growing_annuity:,.0f}")

                    # Below the metrics, show whether the configured retirement age meets each target
                    with st.expander("退休年齡達成檢查 (顯示是否在設定退休年齡達成)"):
                        st.write(f"設定退休年齡: {retirement_age} 歲")
                        if result['retirement_status']:
                            ret = result['retirement_status']
                            ret_traditional = ret['net_worth'] >= fire_target_traditional
                            ret_growing = ret['net_worth'] >= fire_target_growing_annuity
                            st.write(f"4%法則 在 {retirement_age} 歲是否達成: {'是' if ret_traditional else '否'}")
                            st.write(f"成長年金 在 {retirement_age} 歲是否達成: {'是' if ret_growing else '否'}")
                        else:
                            st.write("無該年齡的模擬數據")
                except Exception as e:
                    # fallback simple 25x display
                    import traceback
                    self.log_event(f"❌ 成長年金計算失敗: {str(e)}")
                    try:
                        traceback.print_exc()
                    except Exception:
                        pass
                    try:
                        fire_target = self.player_status.monthly_expense * 12 * 25
                        fire_age = "未達成"
                        for age, data in sorted(self.simulation_results.items()):
                            if data['net_worth'] >= fire_target:
                                fire_age = f"{age}歲"
                                break
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("4%法則 - 達成年齡", fire_age)
                        with c2:
                            st.metric("4%法則 - 目標金額", f"${fire_target:,.0f}")
                        with c3:
                            st.metric("成長年金 - 達成年齡", "N/A")
                        with c4:
                            st.metric("成長年金 - 目標金額", "N/A")
                    except Exception as e:
                        self.log_event(f"❌ 顯示模擬摘要失敗: {e}")

            # 顯示大富翁棋盤 - 縮小約10%
            board_end = int(getattr(self.investment_config, 'retirement_age', 65))
            st.subheader(f"🎯 FIRE理財規劃棋盤 (20-{board_end}歲)")
            # If a dice event was just created, show a highlighted banner similar to the 'confirm' flows
            latest = st.session_state.get('latest_dice_event')
            if latest:
                st.info(f"最新事件: {latest}")
            # toolbar above the board: quick actions (dice / clear planning / restart) + right-aligned primary start button
            tbc1, tbc2, tbc3, tbc4 = st.columns([1,1,1,2])
            with tbc1:
                # 個人設定 按鈕（移到此處，位於人生骰子上方）
                if st.button("🔧 個人設定", key="toolbar_settings", use_container_width=True):
                    try:
                        st.session_state['action_override'] = '🔧 個人設定'
                        # persist the desired view so subsequent reruns keep the settings page
                        st.session_state['sidebar_action'] = '🔧 個人設定'
                    except Exception:
                        pass
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass

                # Directly run dice roll and add event without opening a new page
                if st.button("🎲 人生骰子", key="toolbar_dice", use_container_width=True):
                    # pick current age from session (or player age)
                    current_age = st.session_state.get('selected_age', self.player_status.age)
                    age_dice, event_dice, name, impact, trigger_age = self.roll_double_dice_streamlit(current_age)
                    # Mark event on board (mark_event_on_board_streamlit already appends and saves)
                    self.mark_event_on_board_streamlit(trigger_age, name, impact, event_type='dice')
                    # record a short banner message to show on main board
                    try:
                        st.session_state['latest_dice_event'] = f"🎲 {trigger_age}歲: {name} ({impact:+,} 元)"
                    except Exception:
                        pass
                    st.success(f"🎲 已產生骰子事件: {trigger_age}歲 - {name} ({impact:+,} 元)")
                    # ensure sidebar selection returns to main board and rerun so UI updates
                    try:
                        st.session_state['sidebar_action'] = '🏠 主棋盤'
                    except Exception:
                        pass
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass
            with tbc2:
     
                # 快速導航：查看規劃（放在清除規劃上方）
                if st.button("📋 查看規劃", key="toolbar_view_planning_top", use_container_width=True):
                    try:
                        st.session_state['action_override'] = '📋 查看規劃'
                        st.session_state['sidebar_action'] = '📋 查看規劃'
                        self.log_event('DEBUG toolbar: open planning')
                    except Exception:
                        pass
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass
                # Use session flag for confirm to avoid nested-button races
                if st.button("🗑️ 清除規劃", key="toolbar_clear", use_container_width=True):
                    # toggle the confirmation panel so clicking again will collapse it
                    st.session_state['confirm_clear'] = not st.session_state.get('confirm_clear', False)

                if st.session_state.get('confirm_clear'):
                    st.warning("此操作將清除所有人生規劃和模擬結果")
                    if st.button("確認清除", key="toolbar_confirm_clear", type="secondary"):
                        try:
                            self._clear_planning()
                        except Exception:
                            try:
                                self.log_event('清除規劃失敗')
                            except Exception:
                                pass
                        try:
                            st.session_state.pop('confirm_clear', None)
                        except Exception:
                            pass
                        st.success("✅ 已清除所有規劃")
                        try:
                            self.safe_rerun()
                        except Exception:
                            pass
                        return
            with tbc3:

                # keep the start button at the right-most column so it appears on same row as restart
                if st.button("🚀 開始模擬", key="toolbar_start_right", type="primary", use_container_width=True):
                    # request simulation run on next rerun and trigger rerun now
                    try:
                        st.session_state['run_simulation_now'] = True
                    except Exception:
                        pass
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass
                # If a recent simulation error exists, show it here
                if st.session_state.get('last_sim_error'):
                    st.error(f"最近模擬錯誤: {st.session_state.get('last_sim_error')}")
                # Use a session flag for confirmation to avoid nested-button race conditions
                if st.button("🔄 重新開始", key="toolbar_restart", use_container_width=True):
                    # toggle the confirmation panel so clicking again will collapse it
                    st.session_state['confirm_restart'] = not st.session_state.get('confirm_restart', False)

                if st.session_state.get('confirm_restart'):
                    st.warning("此操作將重置所有設定到初始狀態")
                    if st.button("確認重新開始", key="toolbar_confirm_restart", type="secondary"):
                        try:
                            self._reset_session_preserve_params()
                        except Exception:
                            try:
                                self.log_event("重新開始時重置 session 失敗")
                            except Exception:
                                pass

                        # ensure cache is cleared of planning/results (helper already writes initial_settings.savings=0)
                        try:
                            if os.path.exists(self.cache_file):
                                with open(self.cache_file, 'r', encoding='utf-8') as f:
                                    cached = json.load(f)
                            else:
                                cached = {}
                            cached['life_planning'] = {}
                            cached['random_events'] = {}
                            cached['simulation_results'] = {}
                            if 'initial_settings' not in cached:
                                cached['initial_settings'] = {}
                            cached['initial_settings']['savings'] = 0
                            if 'debt' not in cached['initial_settings']:
                                cached['initial_settings']['debt'] = getattr(getattr(self, 'player_status', None), 'debt', 0)
                            with open(self.cache_file, 'w', encoding='utf-8') as f:
                                json.dump(cached, f, ensure_ascii=False, indent=2)
                        except Exception as e:
                            try:
                                self.log_event(f"重新開始時更新快取檔案失敗: {e}")
                            except Exception:
                                pass

                        # clear confirmation flag and mark restart
                        try:
                            st.session_state.pop('confirm_restart', None)
                        except Exception:
                            pass

                        st.success("✅ 工具已重新開始")
                        try:
                            st.session_state['just_restarted'] = True
                        except Exception:
                            pass
                        try:
                            self.safe_rerun()
                        except Exception:
                            pass
                        return
            # right-most area: place the primary start button aligned with restart (方案2 要求)
            with tbc4:
                # 使用說明 按鈕放在右側工具列
                if st.button("❓ 使用說明", key="toolbar_help", use_container_width=True):
                    try:
                        st.session_state['action_override'] = '❓ 使用說明'
                    except Exception:
                        pass
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass
            # Board scale slider (default 0.7)
            if 'board_scale' not in st.session_state:
                st.session_state.board_scale = 0.7
            col_s1, col_s2 = st.columns([3,1])
            with col_s1:
                st.write('調整棋盤大小')
                bs = st.slider('棋盤縮放比例', min_value=0.4, max_value=1.2, value=float(st.session_state.board_scale), step=0.05, format="%.2f")
                st.session_state.board_scale = float(bs)
            with col_s2:
                st.write('')
                st.caption(f"目前: {st.session_state.board_scale:.2f}x")

            fig, squares = self.draw_monopoly_board_streamlit(scale=st.session_state.board_scale, start_age=20, end_age=board_end)
            st.pyplot(fig)

            # 若已有模擬結果，顯示圖表（放在主棋盤下方）
            if self.simulation_results:
                try:
                    self.show_charts_streamlit()
                except Exception as e:
                    st.warning(f"圖表顯示失敗: {e}")
            
            # 日誌顯示
            st.subheader("📋 操作日誌")
            if 'log_messages' in st.session_state and st.session_state.log_messages:
                log_text = "\n".join(st.session_state.log_messages[-20:])  # 顯示最後20條
                # Provide a non-empty (but hidden) label to avoid Streamlit accessibility warnings
                st.text_area("操作日誌內容", value=log_text, height=200, disabled=True, label_visibility="hidden")
            else:
                st.info("目前沒有操作記錄")

            # # Debug: show a snapshot of key runtime state for diagnosis
            # with st.expander("🔧 調試：顯示目前狀態快照"):
            #     if st.button("顯示 session 快照", key="debug_snapshot"):
            #         snap = {}
            #         try:
            #             ps = st.session_state.get('player_status')
            #             if ps is not None:
            #                 try:
            #                     snap['player_status'] = ps.__dict__
            #                 except Exception:
            #                     # dataclass may not expose __dict__ reliably
            #                     snap['player_status'] = {k: getattr(ps, k) for k in ['age','monthly_income','monthly_expense','savings','debt','stock_investment','bond_investment','cash_investment','real_estate_investment'] if hasattr(ps, k)}
            #             else:
            #                 snap['player_status'] = None
            #         except Exception as e:
            #             snap['player_status_error'] = str(e)
            #         try:
            #             snap['simulation_results_keys'] = list(st.session_state.get('simulation_results', {}).keys())
            #             snap['simulation_results_len'] = len(st.session_state.get('simulation_results', {}))
            #         except Exception as e:
            #             snap['simulation_results_error'] = str(e)
            #         try:
            #             snap['self_simulation_results_len'] = len(self.simulation_results) if getattr(self, 'simulation_results', None) is not None else 0
            #         except Exception:
            #             snap['self_simulation_results_len'] = 'err'
            #         try:
            #             snap['just_restarted'] = st.session_state.get('just_restarted')
            #         except Exception:
            #             snap['just_restarted'] = 'unknown'

            #         # log the snapshot and show it
            #         try:
            #             self.log_event(f"DEBUG SNAPSHOT: {list(snap.keys())}")
            #         except Exception:
            #             pass
            #         st.json(snap)
        
        elif action == "🔧 個人設定":
            self.show_parameter_dialog_streamlit()
        
        elif action == "🚀 完整模擬":
            st.subheader("🚀 完整FIRE退休模擬")
            
            if st.button("開始模擬", type="primary"):
                try:
                    st.session_state['run_simulation_now'] = True
                except Exception:
                    pass
            
            # 顯示模擬結果
            if self.simulation_results:
                st.subheader("📊 模擬結果摘要")
                
                # Prefer showing the user's configured retirement age if present
                preferred_final_age = getattr(self.investment_config, 'retirement_age', None)
                if preferred_final_age is not None and preferred_final_age in self.simulation_results:
                    final_age = preferred_final_age
                else:
                    final_age = max(self.simulation_results.keys())
                final_net_worth = self.simulation_results.get(final_age, self.simulation_results[max(self.simulation_results.keys())])['net_worth']
                
                # Top row: final age & final net worth
                top1, top2 = st.columns(2)
                with top1:
                    st.metric("最終年齡", f"{final_age}歲")
                with top2:
                    st.metric("最終淨資產", f"${final_net_worth:,.0f}")

                # Second row: split two methods into four metric cards (25x age, 25x target, growing annuity age, growing annuity target)
                try:
                    # Compute targets and first-achievement ages（近似計算）
                    retirement_age = int(getattr(self.investment_config, 'retirement_age', 65))
                    life_expectancy = int(getattr(self.investment_config, 'life_expectancy', 85))
                    inflation = float(getattr(self.investment_config, 'inflation_rate', 0.03) or 0.03)
                    conservative = float(getattr(self.investment_config, 'conservative_return_rate', 0.03) or 0.03)

                    # 呼叫核心計算模組
                    player_status = {
                        'age': getattr(self.player_status, 'age', 25),
                        'monthly_expense': getattr(self.player_status, 'monthly_expense', 0),
                    }
                    
                    investment_config = {
                        'retirement_age': retirement_age,
                        'life_expectancy': life_expectancy,
                        'inflation_rate': inflation,
                        'conservative_return_rate': conservative,
                    }
                    
                    result = check_fire_achievement(
                        self.simulation_results,
                        player_status,
                        investment_config
                    )

                    fire_target_traditional = result['fire_target_traditional']
                    fire_target_growing_annuity = result['fire_target_growing']
                    first_age_traditional = result['fire_age_traditional']
                    first_age_growing = result['fire_age_growing']

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        trad_age_disp = f"{first_age_traditional}歲" if first_age_traditional else "未達成"
                        st.metric("25x - 首次達成年齡", trad_age_disp)
                    with c2:
                        st.metric("25x - 目標金額", f"${fire_target_traditional:,.0f}")
                    with c3:
                        grow_age_disp = f"{first_age_growing}歲" if first_age_growing else "未達成"
                        st.metric("成長年金 - 首次達成年齡", grow_age_disp)
                    with c4:
                        st.metric("成長年金 - 目標金額", f"${fire_target_growing_annuity:,.0f}")

                    with st.expander("退休年齡達成檢查 (顯示是否在設定退休年齡達成)"):
                        st.write(f"設定退休年齡: {retirement_age} 歲")
                        if result['retirement_status']:
                            ret = result['retirement_status']
                            st.write(f"25x 在 {retirement_age} 歲是否達成: {'是' if ret['net_worth'] >= fire_target_traditional else '否'}")
                            st.write(f"成長年金 在 {retirement_age} 歲是否達成: {'是' if ret['net_worth'] >= fire_target_growing_annuity else '否'}")
                        else:
                            st.write("無該年齡的模擬數據")

                except Exception as e:
                    # Fallback: show simple 25x metrics if calculation module unavailable
                    fire_target = self.player_status.monthly_expense * 12 * 25
                    fire_age = "未達成"
                    for age, data in sorted(self.simulation_results.items()):
                        if data['net_worth'] >= fire_target:
                            fire_age = f"{age}歲"
                            break
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("4%法則 - 達成年齡", fire_age)
                    with c2:
                        st.metric("4%法則 - 目標金額", f"${fire_target:,.0f}")
                    with c3:
                        st.metric("成長年金 - 達成年齡", "N/A")
                    with c4:
                        st.metric("成長年金 - 目標金額", "N/A")
        
    # '檢視圖表' 已移至主棋盤下方，故不再需要單獨分頁
        
        elif action == "🎲 人生骰子":
            # Inline dice behavior: directly roll, add event to planning, mark on board.
            # Then set action override back to main board and rerun so user stays on the board view.
            current_age = st.session_state.get('selected_age', self.player_status.age)
            age_dice, event_dice, name, impact, trigger_age = self.roll_double_dice_streamlit(current_age)
            # mark_event_on_board_streamlit appends to life_planning and saves; avoid calling add_dice_event_to_planning twice
            self.mark_event_on_board_streamlit(trigger_age, name, impact, event_type='dice')
            try:
                st.session_state['latest_dice_event'] = f"🎲 {trigger_age}歲: {name} ({impact:+,} 元)"
            except Exception:
                pass
            st.success(f"🎲 已產生骰子事件: {trigger_age}歲 - {name} ({impact:+,} 元)")
            # ensure we return to main board view
            try:
                st.session_state['sidebar_action'] = '🏠 主棋盤'
            except Exception:
                pass
            try:
                self.safe_rerun()
            except Exception:
                pass
        
        elif action == "📋 查看規劃":
            # show the full life planning UI (add/edit/delete)
            self.show_life_planning()
        
        elif action in ("🗑️ 清除規劃", "🔄 重新開始"):
            st.subheader("操作已移至主棋盤工具列")
            # Note: navigation is available via the left sidebar '回到主棋盤' button.

            # Provide a session-flag driven restart option here as well (in case user navigates from sidebar)
            if st.button("🔄 重新開始（側欄）", key="sidebar_restart_quick"):
                # toggle confirmation from the sidebar as well
                st.session_state['confirm_restart'] = not st.session_state.get('confirm_restart', False)

            if st.session_state.get('confirm_restart'):
                st.warning("此操作將重置所有設定到初始狀態（側欄）")
                if st.button("確認重新開始（側欄）", key="sidebar_confirm_restart", type="secondary"):
                    try:
                        self._reset_session_preserve_params()
                    except Exception:
                        try:
                            self.log_event("重新開始(側欄)時重置 session 失敗")
                        except Exception:
                            pass

                    # clear confirmation flag
                    try:
                        st.session_state.pop('confirm_restart', None)
                    except Exception:
                        pass

                    st.success("✅ 工具已重新開始 (側欄)")
                    try:
                        st.session_state['just_restarted'] = True
                    except Exception:
                        pass
                    try:
                        self.safe_rerun()
                    except Exception:
                        pass
        
        elif action == "❓ 使用說明":
            st.subheader("❓ FIRE理財規劃工具使用說明")
            st.markdown("""
            ## 🎯 工具說明
            
            ### 📊 主要功能
            
            1. **🏠 主棋盤**: 顯示20歲起至設定退休年齡的大富翁風格年齡棋盤
            2. **🔧 個人設定**: 設定基本財務資料、投資配置、薪資成長參數  
            3. **🚀 完整模擬**: 執行從目前年齡到設定的壽命或退休年齡（由設定控制）的完整財務模擬
            4. **📊 檢視圖表**: 多種圖表分析模擬結果
            5. **🎲 人生骰子**: 原始遊戲系統（保留功能）
            6. **📋 查看規劃**: 規劃並檢視人生事件，加入人生重大開銷如結婚、生子、買房（「本金攤還或本息攤還）等
            7. **🗑️ 清除規劃**: 清除所有規劃和模擬結果
            8. **🔄 重新開始**: 重置到初始狀態
            
            ### 💡 使用流程
            1. 先進入「個人設定」設定您的財務狀況
            2. 執行「完整模擬」查看退休規劃
            3. 使用「檢視圖表」分析結果
            4. 根據結果調整設定並重新模擬
            
            ### ⚠️ 注意事項
            - 模擬結果僅供參考
            - 建議保守估計投資報酬率
            """)

if __name__ == "__main__":
    tool = StreamlitFIREPlanningTool()
    tool.main()

