"""
AI SUPERVISOR v3.0 — Autonomous Self-Optimizing Trading Agent
============================================================
Capabilities:
  - Wakes every 6 hours
  - Reads live performance (PnL, WR, trade history)
  - Runs grid backtest optimizer (200+ param combos)
  - Queries Qwen LLM (cheapest model first) for deep analysis
  - CAN EDIT actual Python source code (dex_hunter.py filters, etc.)
  - Adapts dynamic_params.json
  - Soft-restarts bot fleet via PM2
  - Logs all decisions to ai_supervisor_log.json
"""

import os
import re
import time
import json
import sqlite3
import subprocess
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
DEX_HUNTER_FILE = os.path.join(CURRENT_DIR, "dex_hunter.py")
INTERVAL_HOURS = 6

load_dotenv(ENV_PATH)
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# ===================== QWEN LLM (cheapest first) =====================
MODELS = ["qwen-turbo", "qwen-plus", "qwen-max"]

def ask_qwen(prompt: str, max_tokens: int = 400) -> str:
    if not QWEN_API_KEY:
        return "NO_API_KEY"
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
    for model_name in MODELS:
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            r = requests.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers, json=payload, timeout=20
            )
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"].strip()
                print(f"         [AI] Used model: {model_name}")
                return reply
            elif r.status_code in [429, 403] or "quota" in r.text.lower() or "free tier" in r.text.lower():
                print(f"         [AI] {model_name} quota/rate limited. Switching...")
                continue
            else:
                print(f"         [AI] {model_name} error {r.status_code}. Switching...")
                continue
        except Exception as e:
            print(f"         [AI] {model_name} exception: {e}. Switching...")
            continue
    return "ALL_MODELS_FAILED"

# ===================== PORTFOLIO AUDIT =====================
def audit_portfolio() -> dict:
    result = {
        "wallet_balance": 1000.0,
        "initial_capital": 1000.0,
        "total_pnl_usd": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "avg_win_pct": 0.0,
        "avg_loss_pct": 0.0,
        "recent_trades": [],
        "exit_reason_distribution": {}
    }
    try:
        if os.path.exists(PAPER_PORTFOLIO_FILE):
            with open(PAPER_PORTFOLIO_FILE, "r") as f:
                portfolio = json.load(f)
            result["wallet_balance"] = portfolio.get("wallet_balance", 1000.0)
            result["initial_capital"] = portfolio.get("initial_capital", 1000.0)
            result["total_pnl_usd"] = result["wallet_balance"] - result["initial_capital"]
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
                {"symbol": t.get("symbol"), "pnl_pct": round(t.get("pnl_pct", 0), 2),
                 "exit_reason": t.get("exit_reason", t.get("alasan", ""))}
                for t in history[-15:]
            ]
            # Count exit reason distribution
            for t in history:
                reason = t.get("exit_reason", t.get("alasan", "UNKNOWN"))
                result["exit_reason_distribution"][reason] = result["exit_reason_distribution"].get(reason, 0) + 1
    except Exception as e:
        print(f"         [AUDIT] Error reading portfolio: {e}")
    return result

# ===================== GRID BACKTEST OPTIMIZER =====================
def simulate_trade(candles, entry_price, tp_pct, sl_pct, time_bomb_mins, min_momentum_pct):
    if not candles: return 0.0, "NO_DATA"
    sl_price = entry_price * (1 - sl_pct / 100.0)
    tp_price = entry_price * (1 + tp_pct / 100.0)
    for i, c in enumerate(candles):
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
    for token in tokens[-80:]:
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

# ===================== CODE EDITOR TOOL =====================
def safe_edit_python_value(filepath: str, variable_pattern: str, new_value):
    """
    Safely replace a numeric value in a Python file using regex.
    Creates a backup (.bak) before editing.
    Returns True if edit was made, False otherwise.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(variable_pattern, new_value, content)
        if new_content != content:
            # Backup original
            backup_path = filepath + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"         [CODE EDIT] Applied regex patch to {os.path.basename(filepath)}")
            return True
        return False
    except Exception as e:
        print(f"         [CODE EDIT] FAILED: {e}")
        return False

def apply_ai_code_edits(code_edits: list) -> list:
    """
    Apply a list of code edits suggested by the AI.
    Each edit: {"file": "dex_hunter.py", "pattern": r"p5m > \d+\.?\d*", "replacement": "p5m > 35.0", "reason": "..."}
    """
    applied = []
    # Whitelist: only allow editing these files for safety
    ALLOWED_FILES = {
        "dex_hunter.py": DEX_HUNTER_FILE,
    }
    for edit in code_edits:
        filename = edit.get("file", "")
        pattern = edit.get("pattern", "")
        replacement = edit.get("replacement", "")
        reason = edit.get("reason", "")
        if filename not in ALLOWED_FILES:
            print(f"         [CODE EDIT] BLOCKED: {filename} not in whitelist.")
            continue
        if not pattern or not replacement:
            continue
        filepath = ALLOWED_FILES[filename]
        success = safe_edit_python_value(filepath, pattern, replacement)
        if success:
            applied.append({"file": filename, "reason": reason})
    return applied

# ===================== AI DECISION PROMPT =====================
def load_current_params() -> dict:
    try:
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"tp_pct": 20.0, "sl_pct": 15.0, "time_bomb_mins": 1.0, "min_momentum_pct": 0.0}

def build_ai_prompt(portfolio: dict, opt: dict, current_params: dict) -> str:
    return f"""You are an autonomous AI Quant Trading Manager for a Solana Memecoin 0-minute sniper bot.
You have full authority to edit trading parameters AND request code-level changes.

=== LIVE BOT PERFORMANCE (current session) ===
Wallet Balance   : ${portfolio['wallet_balance']:.2f} (started ${ portfolio['initial_capital']:.2f})
Total PnL (USD)  : ${portfolio['total_pnl_usd']:.2f}
Total Trades     : {portfolio['total_trades']}
Win Rate         : {portfolio['win_rate']:.1f}%
Avg Win          : {portfolio['avg_win_pct']:.1f}%
Avg Loss         : {portfolio['avg_loss_pct']:.1f}%
Exit Distribution: {json.dumps(portfolio['exit_reason_distribution'])}
Recent 15 Trades : {json.dumps(portfolio['recent_trades'])}

=== CURRENT ACTIVE PARAMETERS ===
TP={current_params.get('tp_pct', 20)}% | SL={current_params.get('sl_pct', 15)}% | TimeBomb={current_params.get('time_bomb_mins', 1)}min
Last AI Note: {current_params.get('ai_reasoning', 'N/A')}

=== OPTIMIZER RESULT ({opt['data_points']} recent tokens) ===
Recommended: TP={opt['tp_pct']}% SL={opt['sl_pct']}% TB={opt['time_bomb_mins']}min | BT_WR={opt['backtest_wr']:.1f}% | BT_PnL={opt['backtest_pnl']:.2f}%

=== YOUR DECISION ===
Rules:
- If WR > 65%: Be conservative. Minor tweaks only.
- If WR < 40% or PnL negative: Apply optimizer recommendation immediately.
- If TIME-BOMB exits dominate: Consider increasing time_bomb_mins (tokens need more time).
- If SL exits dominate: Consider tightening SL.
- Code edits (optional): You may ONLY request edits to `dex_hunter.py` FOMO filter thresholds.
  Allowed pattern: change the numeric threshold in `p5m > XX.X` (FOMO overbought filter).
  Valid range: 25.0 to 60.0.

Return STRICT JSON (no markdown, no explanation outside JSON):
{{
  "apply_new_params": true or false,
  "tp_pct": <number>,
  "sl_pct": <number>,
  "time_bomb_mins": <number>,
  "min_momentum_pct": <number>,
  "code_edits": [
    {{
      "file": "dex_hunter.py",
      "pattern": "p5m > \\\\d+\\\\.?\\\\d*",
      "replacement": "p5m > 35.0",
      "reason": "..."
    }}
  ],
  "reasoning": "<2-sentence clear explanation>"
}}"""

# ===================== LOG =====================
def append_log(entry: dict):
    logs = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
    except Exception:
        pass
    logs.append(entry)
    logs = logs[-100:]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

# ===================== SYNTAX CHECK =====================
def verify_syntax(filepath: str) -> bool:
    result = subprocess.run(
        ["python3", "-m", "py_compile", filepath],
        capture_output=True, text=True
    )
    return result.returncode == 0

# ===================== CORE SUPERVISOR CYCLE =====================
def run_supervisor():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 65)
    print(f"[AI-SUPERVISOR v3.0] AWAKENED @ {now}")
    print(f"[AI-SUPERVISOR] Next cycle in {INTERVAL_HOURS} hours")
    print("=" * 65)

    print("[STEP 1] Auditing live portfolio performance...")
    portfolio = audit_portfolio()
    print(f"         WR={portfolio['win_rate']:.1f}% | PnL=${portfolio['total_pnl_usd']:+.2f} | Trades={portfolio['total_trades']}")
    print(f"         Exits: {portfolio['exit_reason_distribution']}")

    print("[STEP 2] Running Grid Backtest Optimizer (200+ combos)...")
    opt = run_optimization()
    if not opt:
        print("         Insufficient market data. Skipping cycle.")
        return
    print(f"         Optimizer: TP={opt['tp_pct']}% SL={opt['sl_pct']}% TB={opt['time_bomb_mins']}m | WR={opt['backtest_wr']:.1f}% PnL={opt['backtest_pnl']:.2f}%")

    current_params = load_current_params()
    print("[STEP 3] Consulting Qwen AI for strategic decision...")
    prompt = build_ai_prompt(portfolio, opt, current_params)
    ai_response = ask_qwen(prompt)
    print(f"         AI Raw Response:\n{ai_response[:800]}")

    # Parse AI JSON decision
    decision = None
    try:
        start = ai_response.find("{")
        end = ai_response.rfind("}") + 1
        if start >= 0 and end > start:
            decision = json.loads(ai_response[start:end])
    except Exception:
        pass

    if not decision:
        print("         [WARN] AI returned invalid JSON. Applying rule-based fallback.")
        decision = {
            "apply_new_params": portfolio["total_pnl_usd"] < 0,
            "tp_pct": opt["tp_pct"],
            "sl_pct": opt["sl_pct"],
            "time_bomb_mins": opt["time_bomb_mins"],
            "min_momentum_pct": opt["min_momentum_pct"],
            "code_edits": [],
            "reasoning": f"Rule-based fallback. PnL=${portfolio['total_pnl_usd']:.2f}. Backtest WR={opt['backtest_wr']:.1f}%."
        }

    code_edits = decision.get("code_edits", [])
    applied_edits = []
    if code_edits:
        print(f"[STEP 4] AI requested {len(code_edits)} code edit(s). Applying with safety checks...")
        applied_edits = apply_ai_code_edits(code_edits)
        if applied_edits:
            print("         Verifying Python syntax after edits...")
            if not verify_syntax(DEX_HUNTER_FILE):
                print("         [CRITICAL] Syntax error detected! Rolling back to backup...")
                backup = DEX_HUNTER_FILE + ".bak"
                if os.path.exists(backup):
                    import shutil
                    shutil.copy(backup, DEX_HUNTER_FILE)
                    applied_edits = []
                    print("         Rollback successful.")
            else:
                print(f"         {len(applied_edits)} code edit(s) applied and verified OK.")
    else:
        print("[STEP 4] No code edits requested by AI.")

    if decision.get("apply_new_params"):
        print("[STEP 5] Applying new trading parameters...")
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
        print(f"         Params: TP={new_params['tp_pct']}% SL={new_params['sl_pct']}% TB={new_params['time_bomb_mins']}min")
        print("[STEP 6] Rebooting trading fleet via PM2...")
        os.system("pm2 restart bot-paper")
        os.system("pm2 restart bot-real")
        print("         Fleet rebooted.")
    else:
        print(f"[STEP 5] AI: No param changes needed.")
        print(f"         Reasoning: {decision.get('reasoning', 'N/A')}")

    log_entry = {
        "timestamp": now,
        "portfolio_snapshot": {
            "balance": portfolio["wallet_balance"],
            "pnl_usd": portfolio["total_pnl_usd"],
            "win_rate": portfolio["win_rate"],
            "total_trades": portfolio["total_trades"]
        },
        "optimizer_result": opt,
        "ai_decision": decision,
        "code_edits_applied": applied_edits
    }
    append_log(log_entry)
    print(f"[LOG] Audit entry saved to ai_supervisor_log.json")
    print(f"[AI-SUPERVISOR] Cycle complete. Sleeping {INTERVAL_HOURS} hours...\n")

# ===================== MAIN LOOP =====================
if __name__ == "__main__":
    while True:
        try:
            run_supervisor()
        except Exception as e:
            print(f"[AI-SUPERVISOR] CRITICAL ERROR: {e}")
            import traceback; traceback.print_exc()
        time.sleep(INTERVAL_HOURS * 3600)
