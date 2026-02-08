import yfinance as yf
import pandas as pd
import requests
import os
import json
from openai import OpenAI

# ================= 配置設定 =================
# 從 GitHub Secrets 讀取設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

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
def calc_sma(series, window):
    return series.rolling(window=window).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

def fetch_refined_data(stocks):
    filtered_list = []
    print(f"開始分析 {len(stocks)} 支標的...")

    for symbol in stocks:
        try:
            # 抓取稍長的時間以計算指標 (需要至少 35 天數據計算 MACD)
            df = yf.download(symbol, period="2mo", interval="1d", progress=False, auto_adjust=True)
            if len(df) < 35: continue

            # 計算指標
            df['MA5'] = calc_sma(df['Close'], 5)
            df['MA20'] = calc_sma(df['Close'], 20)
            df['RSI'] = calc_rsi(df['Close'], 14)

            df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = calc_macd(df['Close'])

            # 取得最新一筆數據
            curr = df.iloc[-1]
            last_close = curr['Close'].item()
            rsi_val = curr['RSI'].item()
            
            # --- 自動過濾機制 ---
            # 條件：股價站上 5MA 且 RSI 介於 40~70 之間（避開超賣與過熱區）
            if last_close > curr['MA5'] and 40 < rsi_val < 75:
                status = "趨勢轉強" if curr['MACD'] > curr['MACD_SIGNAL'] else "區間整理"
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
    
    prompt = f"你是一位專業台股分析師。以下是從 60 支績優股中，透過技術指標(5MA, RSI, MACD)\
        篩選出的潛力標的。請從中精選 5-10 支最具爆發力的股票，\
        並針對它們的技術線型給出具體的「進場點」與「停損建議」。\n數據內容：{data_str}"
    
    response = client.chat.completions.create(
        model="gpt-4o", # 切換模型省錢
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
# ================= 1.5 抓取大盤數據與總結 =================
def get_market_summary():
    try:
        # 抓取加權指數
        idx = yf.download("^TWII", period="5d", interval="1d", progress=False)
        curr_idx = idx.iloc[-1]
        prev_idx = idx.iloc[-2]
        
        change = curr_idx['Close'].item() - prev_idx['Close'].item()
        percent = (change / prev_idx['Close'].item()) * 100
        
        market_info = (
            f"今日加權指數收盤: {curr_idx['Close'].item():.2f}\n"
            f"漲跌點數: {change:+.2f} ({percent:+.2f}%)\n"
            f"成交量估計: {curr_idx['Volume'].item():.0f}"
        )
        
        # 讓 AI 生成總結
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位專業股市評論員，請敘述今日大盤走勢與市場情緒。"},
                {"role": "user", "content": market_info}
            ]
        )
        return f"📊 【大盤總結】\n{market_info}\n\n💡 AI 評論：{response.choices[0].message.content}"
    except Exception as e:
        return "⚠️ 無法取得大盤即時總結"
# ================= 主程式執行 =================
if __name__ == "__main__":
    # 1. 抓取大盤總結
    market_overview = get_market_summary()

    # 2. 抓取並自動過濾（只有好的標的才會進入下一關）
    refined_data = fetch_refined_data(STOCK_LIST)
    
    # 3. AI 分析
    analysis_result = get_ai_recommendation(refined_data)
    
    # 4. 整合內容並發送
    full_content = f"{market_overview}\n\n---\n\n{analysis_result}"
    send_flex_message(full_content)
    print("✅ 進階分析已完成並發送！")