import yfinance as yf
import pandas as pd
import requests
from openai import OpenAI
import os
import json

# ================= 配置設定 =================
# 從 GitHub Secrets 讀取設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# 將字串轉回清單
STOCK_LIST = os.getenv("STOCK_LIST").split(",")

client = OpenAI(api_key=OPENAI_API_KEY)

# ================= 1. 抓取數據與技術分析 =================
def fetch_market_data(stocks):
    summary_list = []
    for symbol in stocks:
        try:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False)
            if df.empty: continue
            
            # 計算簡單技術指標
            last_close = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
            volume_ratio = df['Volume'].iloc[-1] / df['Volume'].rolling(window=5).mean().iloc[-1]
            
            status = "多頭排列" if last_close > ma5 > ma20 else "整理中"
            summary = f"{symbol}: 現價 {last_close:.2f}, 5MA {ma5:.2f}, 20MA {ma20:.2f}, 量增比 {volume_ratio:.2f}, 形態: {status}"
            summary_list.append(summary)
        except Exception as e:
            print(f"抓取 {symbol} 失敗: {e}")
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
    LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
    LINE_USER_ID = os.getenv("LINE_USER_ID")
    
    url = "https://api.line.me/v2/bot/message/push"
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
    if response.status_code != 200:
        print(f"發送失敗: {response.text}")

# ================= 主程式執行 =================
if __name__ == "__main__":
    print("正在抓取市場數據...")
    raw_data = fetch_market_data(STOCK_LIST)
    
    print("AI 正在分析中...")
    ai_analysis = get_ai_recommendation(raw_data)
    
    print("發送 Line 通知...")
    send_line_messaging_api(ai_analysis)
    print("完成！請檢查您的 Line。")