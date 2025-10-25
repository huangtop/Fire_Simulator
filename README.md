# 💰 FIRE 理財規劃工具

現代化的財務獨立提早退休(FIRE)規劃工具，採用前後端分離架構。

## 🚀 快速開始

```bash
# 1. 克隆主 repo
git clone https://github.com/YOUR_USERNAME/fire-simulator.git

# 2. 克隆 core_private 子模組（需要私有訪問權限）
git submodule update --init --recursive

# 3. 安裝依賴
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. 啟動後端 API (終端1)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 啟動前端 UI (終端2)
streamlit run frontend/fire_streamlit.py --server.port 8501
```

然後在瀏覽器開啟 `http://localhost:8501`

## 📁 項目結構

### 公開 Repository (fire-simulator)

```
.
├── frontend/                    # 前端 launcher (簡潔)
│   └── fire_streamlit.py        # 只做加載，呼叫 core_private
├── backend/                     # 後端 API
│   ├── app/main.py
│   └── core/simulation.py
├── core_private/                # 🔒 指向私有 submodule
│   └── .gitmodule (配置文件)
├── requirements.txt
└── README.md
```

### 私有 Repository (fire-simulator-core) 

```
core_private/
├── fire_streamlit.py           # UI 實現 (2991 行)
├── fire_calculations.py        # FIRE 計算公式 (280 行)
├── models_desktop.py           # 數據模型 (170 行)
├── unified_calculations_desktop.py
├── ui_components.py
├── __init__.py
└── README.md
```

## 🏗️ 架構設計

### 雙層 Repository 結構

| 層級 | Repository | 訪問權限 |
|------|-----------|---------|
| **Frontend + Backend** | 公開 (fire-simulator) | ✅ Public |
| **Core Logic & UI** | 私有 (fire-simulator-core) | 🔒 Private |

### 數據流

```
Frontend (public)
  ↓ 載入 core_private (private submodule)
StreamlitFIREPlanningTool
  ↓ 調用
Backend API (public)
  ↓ 調用
Core Calculations (private)
  ↓ 返回結果
Frontend 渲染
```

## � 信息隱藏策略

### 公開看到的：
- ✅ `frontend/fire_streamlit.py` - 簡潔的 20 行 launcher
- ✅ `backend/` - 完整的 API 端點
- ✅ Architecture 文檔

### 不會看到的：
- ❌ `fire_streamlit.py` 複雜的 UI 邏輯 (2991 行)
- ❌ `models_desktop.py` 數據模型
- ❌ `unified_calculations_desktop.py` 舊計算層
- ❌ `ui_components.py` UI 元件

### 方式：
1. **主 repo** (.gitignore) 隱藏這些檔案
2. **Private submodule** 完全獨立 repo

別人即使 clone 主 repo，也看不到這些檔案。只有有權限的人才能訪問 private submodule。

## 📚 API 端點

詳見 `backend/app/main.py`

主要端點：
- `POST /api/simulate` - 執行 FIRE 模擬
- `POST /api/check-fire-status` - 檢查 FIRE 成就
- `POST /api/update-settings` - 更新設定

## 🛠️ 技術棧

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Simulation**: Python
- **Database**: JSON files (可升級為 SQLite/PostgreSQL)

## 📝 開發提示

- 所有新邏輯都應該在 `backend/` 中添加
- 不要在 `frontend/` 中添加複雜的業務邏輯
- 核心計算公式在 `core_private/fire_calculations.py` (受保護)

---

**注意**: 此項目使用 `.gitignore` 隱藏實現細節，確保 git repository 只包含必要的架構和 API 定義。
