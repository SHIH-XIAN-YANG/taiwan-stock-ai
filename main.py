import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
import json
from openai import OpenAI

# ================= 配置設定 =================
# 從 GitHub Secrets 讀取設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "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"
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN") or "HyqYqASnzFr550Y8pRjv0OF4cx5jO9rRE4w03fU3ubDsQnZRLzc8bXqj5AcBSA9OVxyLP32t1uxohW+wi0aJJa1nJpa8iiDwnUjJ+wx0g1Axnm8K3tTiydEJWj+pZN65VVVFKJi3c5uba+BdvJCXnwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = os.getenv("LINE_USER_ID") or "Ua4a4bf08f13b92898a8bfdf201d104fc"

# 檢查 OpenAI Key 是否存在，避免初始化失敗
if not OPENAI_API_KEY or "在這裡貼上" in OPENAI_API_KEY:
    print("⚠️ 警告：找不到 OpenAI API Key，AI 功能將無法執行，僅能測試 LINE 傳送。")
    client = None
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

# 股票清單讀取
stock_str = os.getenv("STOCK_LIST")
if stock_str:
    STOCK_LIST = stock_str.split(",")
else:
    STOCK_LIST = ["2330.TW", "2317.TW", "2454.TW"]
    print("提示：未偵測到環境變數 STOCK_LIST，使用預設測試名單。")

# ================= 1. 抓取數據與技術分析 =================
def fetch_refined_data(stocks):
    filtered_list = []
    print(f"開始分析 {len(stocks)} 支標的...")

    for symbol in stocks:
        try:
            # 抓取稍長的時間以計算指標 (需要至少 35 天數據計算 MACD)
            df = yf.download(symbol, period="2mo", interval="1d", progress=False, auto_adjust=True)
            if len(df) < 35: continue

            # 計算指標
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)

            # 取得最新一筆數據
            curr = df.iloc[-1]
            last_close = float(curr['Close'])
            rsi_val = float(curr['RSI'])
            
            # --- 自動過濾機制 ---
            # 條件：股價站上 5MA 且 RSI 介於 40~70 之間（避開超賣與過熱區）
            if last_close > curr['MA5'] and 40 < rsi_val < 75:
                status = "趨勢轉強" if curr['MACD_12_26_9'] > curr['MACDs_12_26_9'] else "區間整理"
                summary = {
                    "symbol": symbol,
                    "price": round(last_close, 2),
                    "rsi": round(rsi_val, 1),
                    "status": status,
                    "ma5": round(curr['MA5'], 2)
                }
                filtered_list.append(summary)
                print(f"✅ {symbol} 符合過濾條件")
                
        except Exception as e:
            print(f"分析 {symbol} 失敗: {e}")
            
    return filtered_list

# ================= 2. AI 進行選股分析 =================
def get_ai_recommendation(data_list):
    if not data_list: return "今日無符合條件之標的"
    
    # 格式化給 AI 的字串
    data_str = "\n".join([f"{d['symbol']}: 價{d['price']}, RSI{d['rsi']}, {d['status']}" for d in data_list])
    
    prompt = f"你是台股專家，請從以下篩選出的標的中，挑選 10 支最推薦的並提供簡短分析：\n{data_str}"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini", # 切換模型省錢
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
# ================= 3. 發送 Line 通知 =================
def send_flex_message(ai_content):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    # Flex Message 結構
    flex_contents = {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "📈 AI 選股日報", "weight": "bold", "size": "xl", "color": "#ffffff"}
            ], "backgroundColor": "#0367D3"
        },
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": ai_content, "wrap": True, "size": "sm", "margin": "md"}
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "button", "action": {"type": "uri", "label": "查看詳細行情", "uri": "https://tw.stock.yahoo.com/"}, "style": "primary", "color": "#0367D3"}
            ]
        }
    }

    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "flex", "altText": "AI 選股日報", "contents": flex_contents}]
    }
    
    requests.post(url, headers=headers, data=json.dumps(payload))

# ================= 主程式執行 =================
if __name__ == "__main__":
    # 1. 抓取並自動過濾（只有好的標的才會進入下一關）
    refined_data = fetch_refined_data(STOCK_LIST)
    
    # 2. AI 分析
    analysis_result = get_ai_recommendation(refined_data)
    
    # 3. 發送漂亮卡片
    send_flex_message(analysis_result)
    print("✅ 進階分析已完成並發送！")