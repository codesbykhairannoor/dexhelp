"""
AI SUPERVISOR v2.0 — Autonomous Self-Optimizing Trading Agent
============================================================
Capabilities:
  - Wakes every 6 hours
  - Reads live performance (PnL, WR, trade history)
  - Runs grid backtest optimizer (100+ param combos)
  - Queries Qwen LLM (cheapest model first) for analysis
  - Adapts dynamic_params.json accordingly
  - Soft-restarts bot fleet via PM2
  - Logs its own reasoning to ai_supervisor_log.json
"""

import os
import time
import json
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

# ===================== PATH SETUP =====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
ENV_PATH = os.path.join(ROOT_DIR, ".env")
DB_PATH = os.path.join(CURRENT_DIR, "historical_candles.db")
PARAMS_FILE = os.path.join(CURRENT_DIR, "dynamic_params.json")
PAPER_PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")
LOG_FILE = os.path.join(CURRENT_DIR, "ai_supervisor_log.json")
INTERVAL_HOURS = 6

load_dotenv(ENV_PATH)
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# ===================== QWEN LLM =====================
MODELS = ["qwen-turbo", "qwen-plus", "qwen-max"]

def ask_qwen(prompt: str) -> str:
    """Call Qwen with automatic fallback to cheaper models first."""
    if not QWEN_API_KEY:
        return "NO_API_KEY"
    
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
    
    for model_name in MODELS:
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            }
            r = requests.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers, json=payload, timeout=15
            )
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"].strip()
                print(f"    [AI] Model used: {model_name}")
                return reply
            elif r.status_code in [429, 403] or "quota" in r.text.lower() or "free tier" in r.text.lower():
                print(f"    [AI] {model_name} quota/rate limited. Switching...")
                continue
            else:
                print(f"    [AI] {model_name} error {r.status_code}. Switching...")
                continue
        except Exception as e:
            print(f"    [AI] {model_name} exception: {e}. Switching...")
            continue
    return "ALL_MODELS_FAILED"

# ===================== PORTFOLIO AUDIT =====================
def audit_portfolio() -> dict:
    """Read live portfolio stats."""
    result = {
        "wallet_balance": 1000.0,
        "total_pnl_usd": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "avg_win_pct": 0.0,
        "avg_loss_pct": 0.0,
        "recent_trades": []
    }
    
    try:
        if os.path.exists(PAPER_PORTFOLIO_FILE):
            with open(PAPER_PORTFOLIO_FILE, "r") as f:
                portfolio = json.load(f)
            
            result["wallet_balance"] = portfolio.get("wallet_balance", 1000.0)
            initial = portfolio.get("initial_capital", 1000.0)
            result["total_pnl_usd"] = result["wallet_balance"] - initial
            
            history = portfolio.get("trade_history", [])
            wins = [t for t in history if t.get("pnl_usd", 0) > 0]
            losses = [t for t in history if t.get("pnl_usd", 0) <= 0]
            result["total_trades"] = len(history)
            result["wins"] = len(wins)
            result["losses"] = len(losses)
            result["win_rate"] = (len(wins) / len(history) * 100) if history else 0.0
            result["avg_win_pct"] = (sum(t.get("pnl_pct", 0) for t in wins) / len(wins)) if wins else 0.0
            result["avg_loss_pct"] = (sum(t.get("pnl_pct", 0) for t in losses) / len(losses)) if losses else 0.0
            result["recent_trades"] = [
                {"symbol": t.get("symbol"), "pnl_pct": t.get("pnl_pct", 0), "exit_reason": t.get("exit_reason", "")}
                for t in history[-10:]
            ]
    except Exception as e:
        print(f"    [AUDIT] Error reading portfolio: {e}")
    
    return result

# ===================== GRID BACKTEST OPTIMIZER =====================
def simulate_trade(candles, entry_price, tp_pct, sl_pct, time_bomb_mins, min_momentum_pct):
    if not candles: return 0.0, "NO_DATA"
    sl_price = entry_price * (1 - sl_pct/100.0)
    tp_price = entry_price * (1 + tp_pct/100.0)
    highest = entry_price

    for i, c in enumerate(candles):
        if c["high"] > highest:
            highest = c["high"]
        if c["high"] >= tp_price:
            return tp_pct, "WIN (TP)"
        if c["low"] <= sl_price:
            return ((sl_price - entry_price) / entry_price) * 100, "LOSS (SL)"
        if i == int(time_bomb_mins):
            pnl_now = ((c["close"] - entry_price) / entry_price) * 100
            if pnl_now < min_momentum_pct:
                return pnl_now, "TIME-BOMB"

    final_pnl = ((candles[-1]["close"] - entry_price) / entry_price) * 100
    return final_pnl, "HOLDING"

def run_optimization() -> dict | None:
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT address, symbol FROM tokens")
    tokens = cur.fetchall()

    datasets = []
    for token in tokens[-60:]:
        cur.execute("SELECT open, high, low, close FROM candles_1m WHERE address=? ORDER BY timestamp ASC", (token["address"],))
        candles = cur.fetchall()
        if len(candles) >= 3 and candles[0]["open"] > 0:
            datasets.append({"symbol": token["symbol"], "candles": candles, "entry": candles[0]["open"]})
    conn.close()

    if not datasets:
        return None

    best_pnl = -999999.0
    best_params = (20.0, 15.0, 1.0, 0.0)
    best_wr = 0.0

    for tp in [5, 10, 15, 20, 25, 30, 50]:
        for sl in [5, 10, 15, 20]:
            for tb in [0.5, 1.0, 2.0, 3.0]:
                for mm in [-3.0, 0.0, 2.0]:
                    total_pnl = 0.0
                    wins = 0
                    for d in datasets:
                        pnl, _ = simulate_trade(d["candles"], d["entry"], tp, sl, tb, mm)
                        total_pnl += pnl
                        if pnl > 0: wins += 1
                    if total_pnl > best_pnl:
                        best_pnl = total_pnl
                        best_params = (tp, sl, tb, mm)
                        best_wr = (wins / len(datasets)) * 100

    return {
        "tp_pct": float(best_params[0]),
        "sl_pct": float(best_params[1]),
        "time_bomb_mins": float(best_params[2]),
        "min_momentum_pct": float(best_params[3]),
        "backtest_pnl": float(best_pnl),
        "backtest_wr": float(best_wr),
        "data_points": len(datasets)
    }

# ===================== AI ANALYSIS =====================
def build_ai_prompt(portfolio: dict, opt: dict, current_params: dict) -> str:
    return f"""You are an autonomous AI Trading Manager for a Solana Memecoin sniper bot.

=== CURRENT BOT LIVE PERFORMANCE (last session) ===
Wallet Balance    : ${portfolio['wallet_balance']:.2f}
Total PnL (USD)   : ${portfolio['total_pnl_usd']:.2f}
Total Trades      : {portfolio['total_trades']}
Win Rate          : {portfolio['win_rate']:.1f}%
Avg Win           : {portfolio['avg_win_pct']:.1f}%
Avg Loss          : {portfolio['avg_loss_pct']:.1f}%
Recent 10 Trades  : {json.dumps(portfolio['recent_trades'], indent=2)}

=== CURRENT ACTIVE PARAMETERS ===
Take Profit (TP)  : {current_params.get('tp_pct', 20.0)}%
Stop Loss (SL)    : {current_params.get('sl_pct', 15.0)}%
Time-Bomb Exit    : {current_params.get('time_bomb_mins', 1.0)} min
Last AI Reasoning : {current_params.get('ai_reasoning', 'N/A')}

=== GRID BACKTEST OPTIMIZER RESULT (last {opt['data_points']} tokens) ===
Recommended TP    : {opt['tp_pct']}%
Recommended SL    : {opt['sl_pct']}%
Recommended TB    : {opt['time_bomb_mins']} min
Backtest PnL      : {opt['backtest_pnl']:.2f}%
Backtest WR       : {opt['backtest_wr']:.1f}%

=== YOUR TASK ===
1. Analyze the live performance vs backtest data.
2. Decide if the new parameters from the optimizer should be applied.
3. If live WR > 60%, be conservative — make small tweaks only.
4. If live WR < 40% or PnL is negative, apply the optimizer's recommendation immediately.
5. Return your decision in STRICT JSON format:
{{
  "apply_new_params": true or false,
  "tp_pct": <number>,
  "sl_pct": <number>,
  "time_bomb_mins": <number>,
  "min_momentum_pct": <number>,
  "reasoning": "<1-2 sentence explanation>"
}}"""

# ===================== CORE SUPERVISOR CYCLE =====================
def load_current_params() -> dict:
    try:
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"tp_pct": 20.0, "sl_pct": 15.0, "time_bomb_mins": 1.0, "min_momentum_pct": 0.0}

def append_log(entry: dict):
    logs = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
    except Exception:
        pass
    logs.append(entry)
    logs = logs[-50:]  # Keep last 50 audit entries
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

def run_supervisor():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 65)
    print(f"[AI-SUPERVISOR v2.0] AWAKENED @ {now}")
    print(f"[AI-SUPERVISOR] Cycle Interval: Every {INTERVAL_HOURS} Hours")
    print("=" * 65)

    print("[STEP 1] Reading live portfolio performance...")
    portfolio = audit_portfolio()
    print(f"         WR={portfolio['win_rate']:.1f}% | PnL=${portfolio['total_pnl_usd']:.2f} | Trades={portfolio['total_trades']}")

    print("[STEP 2] Running Grid Backtest Optimizer...")
    opt = run_optimization()
    if not opt:
        print("         Insufficient data. Skipping this cycle.")
        return

    print(f"         Best: TP={opt['tp_pct']}% SL={opt['sl_pct']}% TB={opt['time_bomb_mins']}m | BT_WR={opt['backtest_wr']:.1f}%")

    current_params = load_current_params()

    print("[STEP 3] Consulting Qwen AI for strategic decision...")
    prompt = build_ai_prompt(portfolio, opt, current_params)
    ai_response = ask_qwen(prompt)
    print(f"         Raw AI Response:\n{ai_response}")

    # Parse AI JSON response
    decision = None
    try:
        start = ai_response.find("{")
        end = ai_response.rfind("}") + 1
        if start >= 0 and end > start:
            decision = json.loads(ai_response[start:end])
    except Exception:
        pass

    if not decision:
        # Fallback: auto-apply if PnL is negative
        print("         [WARN] AI returned invalid JSON. Falling back to rule-based decision.")
        if portfolio["total_pnl_usd"] < 0:
            decision = {
                "apply_new_params": True,
                "tp_pct": opt["tp_pct"],
                "sl_pct": opt["sl_pct"],
                "time_bomb_mins": opt["time_bomb_mins"],
                "min_momentum_pct": opt["min_momentum_pct"],
                "reasoning": f"Auto-applied optimizer result due to negative PnL (${portfolio['total_pnl_usd']:.2f}). Backtest WR: {opt['backtest_wr']:.1f}%."
            }
        else:
            decision = {"apply_new_params": False, "reasoning": "Fallback: PnL positive, holding current params."}

    log_entry = {
        "timestamp": now,
        "portfolio": portfolio,
        "optimizer": opt,
        "decision": decision
    }

    if decision.get("apply_new_params"):
        print(f"[STEP 4] AI approved parameter update! Applying...")
        new_params = {
            "trade_mode": "HIT_AND_RUN",
            "tp_pct": float(decision.get("tp_pct", opt["tp_pct"])),
            "sl_pct": float(decision.get("sl_pct", opt["sl_pct"])),
            "time_bomb_mins": float(decision.get("time_bomb_mins", opt["time_bomb_mins"])),
            "min_momentum_pct": float(decision.get("min_momentum_pct", 0.0)),
            "last_updated": now,
            "ai_reasoning": decision.get("reasoning", "")
        }
        with open(PARAMS_FILE, "w") as f:
            json.dump(new_params, f, indent=4)
        print(f"         Written: TP={new_params['tp_pct']}% SL={new_params['sl_pct']}% TB={new_params['time_bomb_mins']}m")
        print("[STEP 5] Rebooting trading fleet...")
        os.system("pm2 restart bot-paper")
        os.system("pm2 restart bot-real")
        print("         Fleet rebooted with new parameters.")
    else:
        print(f"[STEP 4] AI decided: No changes needed. Holding current params.")
        print(f"         Reason: {decision.get('reasoning', 'N/A')}")

    append_log(log_entry)
    print(f"[LOG] Audit written to ai_supervisor_log.json")
    print(f"[AI-SUPERVISOR] Cycle complete. Sleeping for {INTERVAL_HOURS} hours...\n")

# ===================== MAIN LOOP =====================
if __name__ == "__main__":
    while True:
        try:
            run_supervisor()
        except Exception as e:
            print(f"[AI-SUPERVISOR] CRITICAL ERROR: {e}")
        time.sleep(INTERVAL_HOURS * 3600)
