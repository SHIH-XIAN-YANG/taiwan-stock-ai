import yfinance as yf
import pandas as pd
import requests
from openai import OpenAI
import os
import json

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
def fetch_market_data(stocks):
    summary_list = []
    for symbol in stocks:
        try:
            # 確保 progress=False 避免干擾，auto_adjust=True 確保價格正確
            df = yf.download(symbol, period="1mo", interval="1d", progress=False, auto_adjust=True)
            
            # 使用 len() 判斷比 .empty 更安全
            if len(df) < 20: 
                print(f"{symbol} 數據不足 20 筆，跳過")
                continue
            
            # 確保取到的是數值而不是 Series (加上 .item() 或取最後一個值)
            last_close = df['Close'].iloc[-1].item()
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1].item()
            ma5 = df['Close'].rolling(window=5).mean().iloc[-1].item()

            current_vol = df['Volume'].iloc[-1].item()
            avg_vol = df['Volume'].rolling(window=5).mean().iloc[-1].item()
            volume_ratio = current_vol / avg_vol if avg_vol != 0 else 0
            
            status = "多頭排列" if last_close > ma5 > ma20 else "整理中"
            summary = f"{symbol}: 現價 {last_close:.2f}, 5MA {ma5:.2f}, 20MA {ma20:.2f}, 量增比 {volume_ratio:.2f}, 形態: {status}"
            summary_list.append(summary)
            print(f"成功抓取 {symbol}")
        except Exception as e:
            print(f"抓取 {symbol} 失敗: {str(e)}")
    return "\n".join(summary_list)

# ================= 2. AI 進行選股分析 =================
def get_ai_recommendation(data):
    prompt = f"""
    你是一位專業台股分析師。請根據以下數據，挑選出今日最值得關注的股票（最多10支），
    並給出簡短的推薦理由（包含支撐位或壓力位預測）。
    
    數據內容：
    {data}
    
    格式要求：
    1. 股票代號 - 名稱
    2. 推薦理由
    3. 操作建議
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "你是一位精準的投資顧問。"},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ================= 3. 發送 Line 通知 =================
def send_line_messaging_api(text_message):
    url = "https://api.line.me/v2/bot/message/push"
    # 確保 Authorization 的 Bearer 後面有一個空格
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": f"🚀 【AI 台股每日推薦】\n\n{text_message}"
            }
        ]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print(f"LINE 伺服器回應狀態碼: {response.status_code}")
    if response.status_code != 200:
        print(f"發送失敗原因: {response.text}")
    else:
        print("✅ LINE 發送成功！")

# ================= 主程式執行 =================
if __name__ == "__main__":
    print("正在抓取市場數據...")
    raw_data = fetch_market_data(STOCK_LIST)
    
    print("AI 正在分析中...")
    ai_analysis = get_ai_recommendation(raw_data)
    
    print("發送 Line 通知...")
    send_line_messaging_api(ai_analysis)
    print("完成！請檢查您的 Line。")