# 📈 Taiwan Stock AI Advisor (台股 AI 智能投顧)

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-green)](https://openai.com/)
[![LINE Messaging API](https://img.shields.io/badge/LINE-Messaging%20API-00C300)](https://developers.line.biz/)

這是一個全自動化的台股分析與推薦系統。它每日定時抓取大盤與指定個股的市場數據，利用技術指標（MA, RSI, MACD）進行初步篩選，再結合 OpenAI 的 GPT 模型進行深度分析，最終將「大盤總結」與「潛力股推薦」整合成一份精美的 LINE Flex Message 卡片發送至你的手機。

它就像你的私人投資助理，每天收盤後自動為你整理重點，節省大量的看盤與篩選時間。

## ✨ 主要功能 (Key Features)

* **📊 自動化大盤總結**：
    * 抓取加權指數 (`^TWII`) 數據。
    * 計算當日漲跌幅與成交量。
    * 由 AI 生成簡短的市場情緒總結（50 字內）。

* **🔍 智慧技術篩選 (Smart Filtering)**：
    * 透過 Python 自動過濾股票，僅保留符合以下技術面的強勢標的：
        * **趨勢多頭**：股價站上 5 日均線 (MA5)。
        * **動能適中**：RSI 強弱指標介於 40 ~ 75 之間（避開超賣死魚股與超買過熱股）。
        * **狀態判定**：MACD 趨勢判斷（區間整理 vs 趨勢轉強）。

* **🤖 AI 深度點評**：
    * 整合篩選後的數據，讓 **GPT-4o-mini** 提供具體的進場理由與停損建議。

* **📱 LINE Flex Message 通知**：
    * 發送圖文並茂的卡片訊息，包含大盤資訊、個股推薦與 Yahoo 股市連結，閱讀體驗優於純文字。

* **☁️ GitHub Actions 自動排程**：
    * 部署在雲端，於每個交易日下午 **15:00 (UTC+8)** 自動執行。
    * 完全免費，無需自行架設伺服器。

## 🛠️ 安裝與本地執行 (Installation)

如果你想在本地電腦上測試或開發，請依照以下步驟：

### 1. 複製專案
```bash
git clone [https://github.com/你的帳號/taiwan-stock-ai.git](https://github.com/你的帳號/taiwan-stock-ai.git)
cd taiwan-stock-ai
```
### 2. 安裝依賴套件

建議使用 Python 3.10 或以上版本。

```bash
pip install -r requirements.txt
```

## ⚙️ GitHub Actions 部署設定 (Deployment)

本專案設計核心為雲端自動執行，你需要將 API 金鑰設定在 GitHub Repository 的 **Secrets** 中，以確保安全性。

1.  進入您的 **GitHub 儲存庫** 頁面。
2.  點擊上方選單的 **Settings** > 左側選單 **Secrets and variables** > **Actions**。
3.  點擊 **New repository secret**，依序新增以下變數：

| Secret Name | 說明 | 範例值 |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | OpenAI API 金鑰 | `sk-proj-...` |
| `LINE_ACCESS_TOKEN` | LINE Messaging API Token | `EyJhbGciOiJI...` |
| `LINE_USER_ID` | 您的 LINE User ID | `U12345678...` |
| `STOCK_LIST` | 監控股票代號 (逗號分隔) | `2330.TW,2317.TW,2454.TW` |



### ⏰ 自動排程時間

設定檔位於 `.github/workflows/daily_report.yml`：
* **Cron 設定**：`0 7 * * 1-5` (對應 UTC 時間 07:00，即 **台北時間 15:00**)。
* **手動觸發**：可至儲存庫的 **Actions** 頁面，選擇對應的工作流後點擊 **"Run workflow"** 進行即時測試。

---

## 📂 專案結構

```plaintext
taiwan-stock-ai/
├── .github/
│   └── workflows/
│       └── daily_report.yml  # GitHub Actions 自動化腳本
├── main.py                   # 主程式 (資料抓取、指標計算、AI分析、LINE發送)
├── requirements.txt          # Python 套件清單 (yfinance, pandas-ta, openai...)
├── .gitignore                # Git 忽略清單 (保護 token 檔)
└── README.md                 # 專案說明文件
```

## 貢獻 (Contributing)
歡迎提交 Issue 或 Pull Request 來改進這個專案！ 如果您覺得這個專案對您有幫助，請不吝給予一顆星星 ⭐！
