import sys
import os
import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import importlib

# ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# import original project modules
PlayerStatus = None
InvestmentConfig = None
UnifiedFireCalculations = None
try:
    from models_desktop import PlayerStatus, InvestmentConfig
    # Resolve calculation module lazily to avoid static import errors
    _calc_mod = importlib.import_module('unified_calculations_desktop')
    UnifiedFireCalculations = getattr(_calc_mod, 'UnifiedFireCalculations', None)
except Exception:
    # fall back to minimal structures if import fails
    PlayerStatus = None
    InvestmentConfig = None
    UnifiedFireCalculations = None
try:
    # import the original UIComponents to reuse its board layout logic
    _ui_mod = importlib.import_module('ui_components')
    UIComponents = getattr(_ui_mod, 'UIComponents', None)
except Exception:
    UIComponents = None

app = FastAPI(title="FIRE API (integrated)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class BackendState:
    def __init__(self):
        if PlayerStatus is not None:
            try:
                self.player_status = PlayerStatus()
            except Exception:
                self.player_status = {'age': 25, 'monthly_income': 35000, 'monthly_expense': 30000, 'savings': 0, 'debt': 0}
        else:
            self.player_status = {'age': 25, 'monthly_income': 35000, 'monthly_expense': 30000, 'savings': 0, 'debt': 0}
        self.investment_config = InvestmentConfig() if InvestmentConfig is not None else None
        self.life_planning: Dict[int, list] = {}
        self.random_events: Dict[int, Any] = {}
        self.current_square = 0
        # Removed cache_file for multi-user compatibility

    def _ps_value(self, key: str, default: Any = None):
        ps = self.player_status
        if isinstance(ps, dict):
            return ps.get(key, default)
        return getattr(ps, key, default)

    def save_cache(self):
        # Removed file caching for multi-user compatibility
        pass


state = BackendState()


class LifeEventRequest(BaseModel):
    age: int
    event_type: str
    amount: Optional[float] = None
    description: Optional[str] = None


class DeleteLifeEventRequest(BaseModel):
    age: int
    index: int


class UpdateLifeEventRequest(BaseModel):
    age: int
    index: int
    event_type: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "FIRE API integrated with project logic"}


@app.get("/api/player-status")
async def get_player_status():
    ps = state.player_status
    if PlayerStatus is not None and not isinstance(ps, dict):
        return ps.__dict__ if hasattr(ps, '__dict__') else ps
    return ps


@app.get("/api/life-planning")
async def get_life_planning():
    return {"life_planning": state.life_planning, "random_events": state.random_events}


@app.post("/api/add-life-event")
async def add_life_event(event: LifeEventRequest):
    if event.age not in state.life_planning:
        state.life_planning[event.age] = []
    event_data = {"type": event.event_type, "amount": event.amount, "description": event.description or f"{event.event_type} event"}
    state.life_planning[event.age].append(event_data)
    state.save_cache()
    return {"status": "success", "message": f"added {event.event_type} at {event.age}"}


@app.post("/api/delete-life-event")
async def delete_life_event(req: DeleteLifeEventRequest):
    age = req.age
    idx = req.index
    if age not in state.life_planning:
        raise HTTPException(status_code=404, detail="no events for age")
    events = state.life_planning[age]
    if idx < 0 or idx >= len(events):
        raise HTTPException(status_code=400, detail="invalid index")
    removed = events.pop(idx)
    if not events:
        del state.life_planning[age]
    state.save_cache()
    return {"status": "success", "message": f"deleted event {removed.get('type')}"}


@app.post("/api/update-life-event")
async def update_life_event(req: UpdateLifeEventRequest):
    age = req.age
    idx = req.index
    if age not in state.life_planning:
        raise HTTPException(status_code=404, detail="no events for age")
    events = state.life_planning[age]
    if idx < 0 or idx >= len(events):
        raise HTTPException(status_code=400, detail="invalid index")
    event = events[idx]
    if req.event_type is not None:
        event['type'] = req.event_type
    if req.description is not None:
        event['description'] = req.description
    if req.amount is not None:
        event['amount'] = req.amount
    events[idx] = event
    state.save_cache()
    return {"status": "success", "message": "updated", "event": event}


@app.post("/api/clear-planning")
async def clear_all_planning():
    state.life_planning.clear()
    state.random_events.clear()
    state.save_cache()
    return {"status": "success", "message": "cleared"}


@app.get("/api/board-state")
async def get_board_state():
    # Prefer using the original UIComponents board layout logic so behavior matches main_desktop.py exactly
    try:
        if UIComponents is not None:
            # UIComponents.draw_monopoly_board expects a canvas-like object; provide a minimal shim
            class DummyCanvas:
                def delete(self, *args, **kwargs):
                    return None

            ui = UIComponents(None)
            squares = ui.draw_monopoly_board(DummyCanvas())

            board_squares = []
            # squares returned by draw_monopoly_board contain keys: text, age, color, pos
            for idx, sq in enumerate(squares):
                age = sq.get('age')
                is_current = (age == 20 + state.current_square)
                has_planning = age in state.life_planning and len(state.life_planning[age]) > 0
                has_random_event = age in state.random_events
                board_squares.append({
                    "position": idx,
                    "age": age,
                    "is_current": is_current,
                    "has_planning": has_planning,
                    "has_random_event": has_random_event,
                    "title": sq.get('text', str(age)),
                    "pos": sq.get('pos')
                })

            return {"squares": board_squares, "current_position": state.current_square, "current_age": 20 + state.current_square}
    except Exception:
        # fallback to simple sequential board if UIComponents cannot be used
        board_squares = []
        for i in range(46):
            age = 20 + i
            is_current = (i == state.current_square)
            has_planning = age in state.life_planning and len(state.life_planning[age]) > 0
            has_random_event = age in state.random_events
            board_squares.append({
                "position": i,
                "age": age,
                "is_current": is_current,
                "has_planning": has_planning,
                "has_random_event": has_random_event,
                "title": f"{age}"
            })
        return {"squares": board_squares, "current_position": state.current_square, "current_age": 20 + state.current_square}


@app.post("/api/dice-game")
async def start_dice_game():
    import random
    
    # 第一顆骰子：年齡骰子（用於顯示）
    age_dice = random.randint(1, 6)
    
    # 第二顆骰子：事件類型
    event_dice = random.randint(1, 6)
    
    # 計算觸發年齡：從當前年齡到退休年齡之間隨機
    current_age = state.player_status.get('age', 25) if isinstance(state.player_status, dict) else getattr(state.player_status, 'age', 25)
    retirement_age = 65  # 預設退休年齡
    if state.investment_config is not None:
        try:
            retirement_age = getattr(state.investment_config, 'retirement_age', 65)
        except:
            pass
    
    min_age = max(int(current_age), 25)
    max_age = int(retirement_age) - 1
    
    if min_age >= max_age:
        trigger_age = min_age
    else:
        trigger_age = random.randint(min_age, max_age)
    
    # 定義隨機事件
    events = {
        1: create_medical_emergency_event(),
        2: create_loan_default_event(),
        3: create_investment_loss_event(),
        4: create_car_damage_event(),
        5: create_business_failure_event(),
        6: create_job_loss_event()
    }
    
    event_info = events[event_dice]
    event_name = event_info['name']
    financial_impact = event_info['impact']
    
    # 將事件添加到 random_events
    if trigger_age not in state.random_events:
        state.random_events[trigger_age] = []
    state.random_events[trigger_age].append({
        'type': 'random_event',
        'description': event_name,
        'amount': financial_impact
    })
    
    state.save_cache()
    
    return {
        "age_dice": age_dice,
        "event_dice": event_dice,
        "event_name": event_name,
        "financial_impact": financial_impact,
        "trigger_age": trigger_age
    }


def create_medical_emergency_event():
    """創建醫療緊急事件"""
    impact = -random.randint(30000, 200000)  # 3-20萬醫療支出
    return {
        'name': f'意外醫療支出（{abs(impact):,.0f}元）',
        'impact': impact
    }


def create_loan_default_event():
    """創建借錢不還事件"""
    impact = -random.randint(50000, 150000)  # 5-15萬借錢損失
    return {
        'name': f'被借錢不還（{abs(impact):,.0f}元）',
        'impact': impact
    }


def create_investment_loss_event():
    """創建投資失利事件"""
    loss_percentage = random.randint(10, 40)  # 10-40%損失
    impact = -random.randint(80000, 300000)  # 8-30萬投資損失
    return {
        'name': f'投資失利（虧損{abs(impact):,.0f}元）',
        'impact': impact
    }


def create_car_damage_event():
    """創建車子泡水維修事件"""
    impact = -random.randint(40000, 120000)  # 4-12萬維修費
    return {
        'name': f'車子泡水維修（{abs(impact):,.0f}元）',
        'impact': impact
    }


def create_business_failure_event():
    """創建生意失敗事件"""
    impact = -random.randint(100000, 500000)  # 10-50萬生意損失
    return {
        'name': f'生意失敗（損失{abs(impact):,.0f}元）',
        'impact': impact
    }


def create_job_loss_event():
    """創建裁員事件"""
    # 裁員影響：3-6個月薪資損失
    months_loss = random.randint(3, 6)
    impact = -random.randint(80000, 200000)  # 8-20萬收入損失
    return {
        'name': f'裁員（{months_loss}個月薪資損失，{abs(impact):,.0f}元）',
        'impact': impact
    }


@app.post("/api/update-settings")
async def update_settings(payload: Dict[str, Any]):
    ps = state.player_status
    for k, v in payload.items():
        if v is None:
            continue
        if PlayerStatus is not None and not isinstance(ps, dict):
            if hasattr(ps, k):
                setattr(ps, k, v)
        else:
            # ensure dict-like structure
            if not isinstance(ps, dict):
                ps = {
                    'age': getattr(ps, 'age', 25),
                    'monthly_income': getattr(ps, 'monthly_income', 35000),
                    'monthly_expense': getattr(ps, 'monthly_expense', 30000),
                    'savings': getattr(ps, 'savings', 0),
                    'debt': getattr(ps, 'debt', 0),
                }
                state.player_status = ps
            ps[k] = v
    state.save_cache()
    return {"status": "success"}


@app.post("/api/restart")
async def restart_tool():
    state.__init__()
    return {"status": "success"}


@app.get("/api/help")
async def get_help():
    return {"help_text": "integrated API: use /api/life-planning and /api/add-life-event etc."}


@app.post("/api/calc-retirement-target")
async def calc_retirement_target(payload: Dict[str, Any]):
    if UnifiedFireCalculations is None:
        raise HTTPException(status_code=500, detail="calculation module not available")
    try:
        monthly_expense = float(payload.get('monthly_expense', 30000))
        current_age = int(payload.get('current_age', 25))
        retirement_age = int(payload.get('retirement_age', 65))
        life_expectancy = int(payload.get('life_expectancy', 85))
        inflation_rate = float(payload.get('inflation_rate', 0.03))
        conservative_return_rate = float(payload.get('conservative_return_rate', 0.03))
        val = UnifiedFireCalculations.calculate_retirement_target_growing_annuity(monthly_expense, current_age, retirement_age, life_expectancy, inflation_rate, conservative_return_rate)
        return {"retirement_target": val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Simulation endpoint (core only) ---
try:
    from backend.core import run_simulation as core_run_simulation
except Exception:
    try:
        # support relative import when running as module
        from ..core import run_simulation as core_run_simulation  # type: ignore
    except Exception:
        core_run_simulation = None  # will 500 if called


@app.post("/api/simulate")
async def simulate(payload: Dict[str, Any]):
    if core_run_simulation is None:
        raise HTTPException(status_code=500, detail="simulation core not available")
    try:
        result = core_run_simulation(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# duplicate helper definitions removed (defined above)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
