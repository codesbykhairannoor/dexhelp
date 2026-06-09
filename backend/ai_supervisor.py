import os
import time
import json
import sqlite3
import requests
from dotenv import load_dotenv

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(CURRENT_DIR), ".env")
DB_PATH = os.path.join(CURRENT_DIR, "historical_candles.db")
PARAMS_FILE = os.path.join(CURRENT_DIR, "dynamic_params.json")

load_dotenv(ENV_PATH)

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

def simulate(candles, entry_price, tp_pct, sl_pct, time_bomb_mins, min_momentum_pct):
    if not candles: return 0.0, "NO_DATA"
    highest_price = entry_price
    sl_price = entry_price * (1 - sl_pct/100.0)
    tp_price = entry_price * (1 + tp_pct/100.0)
    
    for i, c in enumerate(candles):
        high = c["high"]
        low = c["low"]
        close = c["close"]
        
        if high >= tp_price:
            return tp_pct, "WIN (TP)"
        if low <= sl_price:
            pnl = ((sl_price - entry_price) / entry_price) * 100
            return pnl, "LOSS (SL)"
        if i == time_bomb_mins:
            current_pnl_pct = ((close - entry_price) / entry_price) * 100
            if current_pnl_pct < min_momentum_pct:
                return current_pnl_pct, "TIME-BOMB"
                
    final_pnl = ((candles[-1]["close"] - entry_price) / entry_price) * 100
    return final_pnl, "HOLDING"

def run_optimization():
    print("[AI-SUPERVISOR] Extracting last 12 hours of market data...")
    if not os.path.exists(DB_PATH):
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT address, symbol FROM tokens")
    tokens = cursor.fetchall()
    
    datasets = []
    for token in tokens[-50:]: # analyze last 50 tokens
        cursor.execute("SELECT open, high, low, close FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", (token["address"],))
        candles = cursor.fetchall()
        if len(candles) >= 3 and candles[0]["open"] > 0:
            datasets.append({"symbol": token["symbol"], "candles": candles, "entry": candles[0]["open"]})
            
    if not datasets:
        return None
        
    best_pnl = -999999.0
    best_params = (20.0, 15.0, 1.0, 0.0) # default fallback
    
    print(f"[AI-SUPERVISOR] Running high-speed grid optimization on {len(datasets)} recent tokens...")
    for tp in [10, 15, 20, 25, 30]:
        for sl in [5, 10, 15, 20]:
            for tb_mins in [1.0, 2.0, 3.0]:
                for min_mom in [-2.0, 0.0, 2.0]:
                    total_pnl = 0.0
                    for data in datasets:
                        pnl, _ = simulate(data["candles"], data["entry"], tp, sl, tb_mins, min_mom)
                        total_pnl += pnl
                    if total_pnl > best_pnl:
                        best_pnl = total_pnl
                        best_params = (tp, sl, tb_mins, min_mom)
                        
    print(f"[AI-SUPERVISOR] Best params found: TP={best_params[0]}% SL={best_params[1]}% TB={best_params[2]}m PNL={best_pnl:.2f}%")
    return {
        "tp_pct": float(best_params[0]),
        "sl_pct": float(best_params[1]),
        "time_bomb_mins": float(best_params[2]),
        "min_momentum_pct": float(best_params[3]),
        "backtest_pnl": float(best_pnl),
        "data_points": len(datasets)
    }

def ask_qwen_ai(opt_results):
    if not QWEN_API_KEY:
        return "QWEN API KEY is missing. Executed fallback reasoning."
        
    prompt = f"""You are an elite High-Frequency Trading Manager for Solana Memecoins.
I have just backtested the last 12 hours of new memecoins.
The optimal parameters to maximize profit are:
- Take Profit: {opt_results['tp_pct']}%
- Stop Loss: {opt_results['sl_pct']}%
- Time-Bomb Exit: {opt_results['time_bomb_mins']} minutes
This would have yielded a Net PnL of {opt_results['backtest_pnl']}% across {opt_results['data_points']} trades.

Provide a 1-sentence confident summary to log into the bot's awareness state explaining why these parameters are perfect for current market conditions."""

    models = ["qwen-turbo", "qwen-plus", "qwen-max"]
    
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    for model_name in models:
        try:
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}]
            }
            r = requests.post("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions", headers=headers, json=data, timeout=10)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"]
                return f"[{model_name}] {content.strip()}"
            elif r.status_code == 429 or "quota" in r.text.lower():
                print(f"[AI-SUPERVISOR] Model {model_name} quota exhausted or rate-limited. Trying next...")
                continue
            else:
                print(f"[AI-SUPERVISOR] Model {model_name} failed with API Error: {r.status_code}. Trying next...")
                continue
        except Exception as e:
            print(f"[AI-SUPERVISOR] Model {model_name} connection error: {e}. Trying next...")
            continue
            
    return "AI Fallback Error: All models exhausted or failed."

def run_supervisor():
    print("=" * 60)
    print("🤖 [AI SUPERVISOR] AWAKENED - Starting 12-Hour System Audit")
    print("=" * 60)
    
    results = run_optimization()
    if results:
        print("[AI-SUPERVISOR] Generating market awareness report via Qwen LLM...")
        reasoning = ask_qwen_ai(results)
        print(f"[AI-SUPERVISOR] LLM Reasoning: {reasoning}")
        
        new_params = {
            "trade_mode": "HIT_AND_RUN",
            "tp_pct": results["tp_pct"],
            "sl_pct": results["sl_pct"],
            "time_bomb_mins": results["time_bomb_mins"],
            "min_momentum_pct": results["min_momentum_pct"],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ai_reasoning": reasoning
        }
        
        with open(PARAMS_FILE, "w") as f:
            json.dump(new_params, f, indent=4)
            
        print("[AI-SUPERVISOR] Successfully injected new parameters to dynamic_params.json!")
        print("[AI-SUPERVISOR] Executing safe reboot of all trading engines...")
        
        # Soft restart to load new params instantly
        os.system("pm2 restart bot-paper")
        os.system("pm2 restart bot-real")
        print("[AI-SUPERVISOR] PM2 Restart commands issued. The fleet is back online with new brains.")
    else:
        print("[AI-SUPERVISOR] Insufficient data to optimize. Sleeping.")

if __name__ == "__main__":
    while True:
        try:
            run_supervisor()
        except Exception as e:
            print(f"[AI-SUPERVISOR] Critical Error: {e}")
        
        print("[AI-SUPERVISOR] Going to sleep for 12 hours...")
        time.sleep(12 * 3600)
