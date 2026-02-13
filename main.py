import yfinance as yf
import pandas as pd
import requests
import os
import json
from openai import OpenAI
import datetime

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

# ================= 1. 智慧讀取清單 =================
# 優先讀取台股清單
tw_stock_env = os.getenv("STOCK_LIST")
# 新增讀取美股清單
us_stock_env = os.getenv("US_STOCK_LIST")

def get_list_from_env(env_val, default_list):
    if env_val:
        return [s.strip() for s in env_val.split(",")]
    return default_list

# 本地測試時的預設值
TW_LIST = get_list_from_env(tw_stock_env, ["2330.TW", "2317.TW"])
US_LIST = get_list_from_env(us_stock_env, ["NVDA", "TSM", "SOXX"])

# ================= 自動市場判定與清單讀取 =================
def get_current_market_config():
    # 取得台北時間 (UTC+8)
    tz_taiwan = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz_taiwan)
    hour = now.hour

    # 早上 5:00 ~ 9:00 定義為美股收盤分析
    if 5 <= hour <= 9:
        market_mode = "US"
        env_list = os.getenv("US_STOCK_LIST")
        default_list = ["SOXX", "NVDA", "TSM", "AAPL", "MSFT"]
        title = "🇺🇸 美股收盤分析 (盤前指引)"
    else:
        market_mode = "TW"
        env_list = os.getenv("STOCK_LIST")
        default_list = ["2330.TW", "2317.TW", "2454.TW"]
        title = "🇹🇼 台股收盤分析 (每日精選)"

    stock_list = [s.strip() for s in env_list.split(",")] if env_list else default_list
    return market_mode, stock_list, title

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
            # 1. 抓取資料並解決 MultiIndex 問題
            df = yf.download(symbol, period="2mo", interval="1d", progress=False, auto_adjust=True)
            
            # 強制扁平化欄位，確保 df['Close'] 只有一列
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            if len(df) < 35: continue

            # 2. 計算指標
            df['MA5'] = calc_sma(df['Close'], 5)
            df['MA20'] = calc_sma(df['Close'], 20)
            df['RSI'] = calc_rsi(df['Close'], 14)
            df['MACD'], df['MACD_SIGNAL'], _ = calc_macd(df['Close'])

            # 3. 確保取出的數值是 Scalar (單一數值) 並轉為 float
            curr = df.iloc[-1]
            last_close = float(curr['Close'])
            ma5_val = float(curr['MA5'])
            rsi_val = float(curr['RSI'])
            macd_val = float(curr['MACD'])
            signal_val = float(curr['MACD_SIGNAL'])
            
            # --- 修正後的過濾條件判斷 ---
            if last_close > ma5_val and 40 < rsi_val < 75:
                status = "趨勢轉強" if macd_val > signal_val else "區間整理"
                summary = {
                    "symbol": symbol,
                    "price": round(last_close, 2),
                    "rsi": round(rsi_val, 1),
                    "status": status,
                    "ma5": round(ma5_val, 2)
                }
                filtered_list.append(summary)
                print(f"✅ {symbol} 符合過濾條件")
                
        except Exception as e:
            print(f"分析 {symbol} 失敗: {str(e)}")
            
    return filtered_list
# ================= 2. AI 進行選股分析 =================

def get_ai_analysis(data_list, mode):
    if not data_list: return "目前市場標的處於整理期，無符合強勢篩選條件之標的。"
    
    data_str = "\n".join([f"{d['symbol']}: 價{d['price']} ({d['change']}%), RSI:{d['rsi']}" for d in data_list])
    
    # 根據市場切換 Prompt
    if mode == "US":
        role_prompt = "你是一位資深美股宏觀分析師，擅長分析美股對台股的連動影響。"
        user_prompt = f"請分析昨晚美股表現：\n{data_str}\n\n特別注意：\n1. 科技股氣氛與 AI 龍頭動向。\n2. TSM (台積電ADR) 表現對今日台股開盤的具體引導作用。\n3. 提供短線操作觀點。"
    else:
        role_prompt = "你是一位精準的台股量化選股專家。"
        user_prompt = f"請根據以下台股篩選清單進行分析，透過技術指標(5MA, RSI, MACD)\
        篩選出的潛力標的。：\n{data_str}\n\n挑選 3-10 支最值得關注的標的，給出支撐位、壓力位建議，並說明推薦理由。"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": role_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content

# ================= 3. 發送 Line 通知 =================
def send_line_flex(title, content):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    # 動態變更卡片顏色 (美股藍色/台股紅色)
    theme_color = "#0055AA" if "美股" in title else "#E63946"
    
    flex_contents = {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": "#ffffff"}
            ], "backgroundColor": theme_color
        },
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": content, "wrap": True, "size": "sm"}
            ]
        }
    }
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "flex", "altText": title, "contents": flex_contents}]
    }
    requests.post(url, headers=headers, data=json.dumps(payload))



# ================= 1.5 抓取大盤數據與總結 =================
def get_market_summary():
    try:
        idx = yf.download("^TWII", period="5d", interval="1d", progress=False)
        
        # 同樣處理大盤的 MultiIndex
        if isinstance(idx.columns, pd.MultiIndex):
            idx.columns = idx.columns.get_level_values(0)
            
        curr_idx = idx.iloc[-1]
        prev_idx = idx.iloc[-2]
        
        # 確保取值使用 float() 避免 Series 錯誤
        curr_close = float(curr_idx['Close'])
        prev_close = float(prev_idx['Close'])
        curr_vol = float(curr_idx['Volume'])
        
        change = curr_close - prev_close
        percent = (change / prev_close) * 100
        
        market_info = (
            f"今日加權指數收盤: {curr_close:.2f}\n"
            f"漲跌點數: {change:+.2f} ({percent:+.2f}%)\n"
            f"成交量估計: {curr_vol:.0f}"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位專業股市評論員，請用 50 字內簡述今日大盤走勢與市場情緒。"},
                {"role": "user", "content": market_info}
            ]
        )
        return f"📊 【大盤總結】\n{market_info}\n\n💡 AI 評論：{response.choices[0].message.content}"
    except Exception as e:
        print(f"大盤總結錯誤: {e}")
        return "⚠️ 無法取得大盤即時總結"

# ================= 主程式執行 =================
if __name__ == "__main__":
    mode, stocks, title = get_current_market_config()
    print(f"當前模式: {mode}, 準備分析 {len(stocks)} 支標的...")

    print(f"✅ {title} 發送完成！")


    # 1. 抓取大盤總結
    market_overview = get_market_summary()

    # 2. 抓取並自動過濾（只有好的標的才會進入下一關）
    refined_data = fetch_refined_data(stocks)
    
    # 3. AI 分析
    analysis_result = get_ai_analysis(refined_data, mode)
    
    # 4. 整合內容並發送
    full_content = f"{market_overview}\n\n---\n\n{analysis_result}"
    send_line_flex(title, full_content)
    print("✅ 進階分析已完成並發送！")