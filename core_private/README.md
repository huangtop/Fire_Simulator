# 🔒 Core Private Module

This is the private repository for all core FIRE simulation logic and UI implementation.

## 📦 Contents

- **fire_calculations.py** - Core FIRE calculation formulas
  - Growing annuity present value
  - FIRE achievement checking
  - Retirement target calculations

- **fire_streamlit.py** - Streamlit UI implementation
  - User interface and form handling
  - Data visualization
  - Session state management

- **models_desktop.py** - Data models
  - PlayerStatus
  - InvestmentConfig
  - SalaryConfig
  - MonthlyFinancialResult

- **unified_calculations_desktop.py** - Legacy calculation utilities

- **ui_components.py** - UI component utilities

## 🚀 Usage

This module is imported by the public `frontend/fire_streamlit.py` launcher:

```python
from core_private import StreamlitFIREPlanningTool

tool = StreamlitFIREPlanningTool()
tool.main()
```

## 🔐 Private Deployment

To use this as a private submodule or separate repository:

1. Create a private GitHub repository: `fire-simulator-core`
2. Add this folder as a submodule:
   ```bash
   git submodule add https://github.com/YOUR_USERNAME/fire-simulator-core.git core_private
   ```

## 📝 Notes

- All calculation logic is here for protection
- UI implementation is hidden from public repository
- Only exposed through `.gitignore` in the parent repository
