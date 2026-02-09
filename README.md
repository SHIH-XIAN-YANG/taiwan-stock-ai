📈 Taiwan Stock AI Advisor (台股 AI 智能投顧)這是一個自動化的台股分析與推薦系統。它每日定時抓取大盤與指定個股的市場數據，利用技術指標（MA, RSI, MACD）進行初步篩選，再結合 OpenAI 的 GPT 模型進行深度分析，最終將「大盤總結」與「潛力股推薦」整合成一份精美的 LINE Flex Message 卡片發送至你的手機。它就像你的私人投資助理，每天收盤後自動為你整理重點，節省大量的看盤與篩選時間。✨ 主要功能 (Key Features)📊 自動化大盤總結：抓取加權指數 (^TWII) 數據，並由 AI 生成簡短的當日市場情緒總結。🔍 智慧技術篩選：透過 Python 自動過濾股票，僅保留符合以下技術面的強勢標的：股價站上 5 日均線 (MA5)。RSI 強弱指標介於 40 ~ 75 之間（避開超賣與過熱）。MACD 趨勢判斷（區間整理 vs 趨勢轉強）。🤖 AI 深度點評：整合篩選後的數據，讓 GPT-4o-mini 提供進場理由與停損建議。📱 LINE Flex Message 通知：發送圖文並茂的卡片訊息，包含大盤資訊、個股推薦與 Yahoo 股市連結。☁️ GitHub Actions 自動排程：部署在雲端，於每個交易日下午 15:00 (UTC+8) 自動執行，完全免費且無需維護伺服器。🛠️ 安裝與本地執行 (Installation)如果你想在本地電腦上測試或開發，請依照以下步驟：1. 複製專案Bashgit clone https://github.com/你的帳號/taiwan-stock-ai.git
cd taiwan-stock-ai
2. 安裝依賴套件建議使用 Python 3.10 或以上版本。Bashpip install -r requirements.txt
3. 設定 API 金鑰在專案根目錄建立一個名為 token 的檔案（無副檔名），並填入你的金鑰：PlaintextOPENAI_API_KEY=sk-proj-你的OpenAI金鑰
LINE_ACCESS_TOKEN=你的LINE_Channel_Access_Token
LINE_USER_ID=你的LINE_User_ID
STOCK_LIST=2330.TW,2317.TW,2454.TW
注意：token 檔案已被列入 .gitignore，請勿將其上傳至 GitHub。4. 執行程式Bashpython main.py
若設定正確，終端機將顯示分析進度，並在 LINE 上收到通知。⚙️ GitHub Actions 部署設定本專案設計為透過 GitHub Actions 自動運行。你需要將 API 金鑰設定在 GitHub Repository 的 Secrets 中。進入 GitHub 儲存庫頁面，點擊 Settings > Secrets and variables > Actions。點擊 New repository secret，依序新增以下變數：Secret Name說明OPENAI_API_KEY你的 OpenAI API Key (建議使用 GPT-4o-mini 權限)LINE_ACCESS_TOKENLINE Developers Console 取得的 Channel Access TokenLINE_USER_ID你的 LINE User ID (可在 Messaging API 測試區取得)STOCK_LIST欲監控的股票代號，以逗號分隔 (例如: 2330.TW,2317.TW)自動排程時間預設設定於 .github/workflows/daily_report.yml：執行時間：週一至週五 UTC 07:00 (即台灣時間 15:00)。手動觸發：可至 Actions 頁面手動點擊 "Run workflow" 進行測試。📂 專案結構Plaintexttaiwan-stock-ai/
├── .github/
│   └── workflows/
│       └── daily_report.yml  # GitHub Actions 自動化腳本
├── main.py                   # 主程式核心邏輯
├── requirements.txt          # Python 套件依賴清單
├── .gitignore                # 忽略清單 (包含 token 檔)
└── README.md                 # 專案說明文件
⚠️ 免責聲明 (Disclaimer)本專案僅供程式開發學習與技術研究使用。所有分析結果與數據皆來自公開 API 與 AI 生成，不代表任何投資建議。投資者應自行判斷風險，開發者不對任何投資損益負責。📝 貢獻 (Contributing)歡迎提交 Issue 或 Pull Request 來改進這個專案！如果你覺得這個專案對你有幫助，請不吝給予一顆星星 ⭐！
