"""Compatibility launcher: import the ASGI app from backend.app.main for uvicorn entrypoints."""

import os

try:
    # import the app object from the package
    from backend.app.main import app
except Exception:
    # fallback: simple message app
    from fastapi import FastAPI
    app = FastAPI()
    @app.get('/')
    def root():
        return {'message': 'fallback backend launcher - failed to import backend.app.main'}


if __name__ == '__main__':
    # allow running this file directly for backward compatibility
    import uvicorn
    print('Starting backend.app.main:app on 0.0.0.0:8000')
    uvicorn.run('backend.app.main:app', host='0.0.0.0', port=8000, reload=False)
            del state.life_planning[age]
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
        return {"status": "success", "message": "updated", "event": event}


    @app.post("/api/clear-planning")
    async def clear_all_planning():
        state.life_planning.clear()
        state.random_events.clear()
        return {"status": "success", "message": "cleared"}


    @app.get("/api/board-state")
    async def get_board_state():
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
        d1 = random.randint(1,6)
        d2 = random.randint(1,6)
        steps = d1 + d2
        state.current_square = min(45, state.current_square + steps)
        new_age = 20 + state.current_square
        state.player_status['age'] = new_age
        return {"dice1": d1, "dice2": d2, "total_steps": steps, "old_age": 20 + state.current_square - steps, "new_age": new_age, "is_finished": state.current_square >= 45}


    @app.post("/api/update-settings")
    async def update_settings(payload: Dict[str, Any]):
        for k,v in payload.items():
            if k in state.player_status and v is not None:
                state.player_status[k] = v
        return {"status": "success"}


    @app.post("/api/restart")
    async def restart_tool():
        state.__init__()
        return {"status": "success"}


    @app.get("/api/help")
    async def get_help():
        return {"help_text": "test API"}


    if __name__ == '__main__':
        print("Starting standalone FIRE API on http://0.0.0.0:8000")
        uvicorn.run(app, host='0.0.0.0', port=8000)
