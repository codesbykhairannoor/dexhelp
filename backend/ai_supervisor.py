"""
AI SUPERVISOR v4.0 — Fully Autonomous Self-Evolving Trading Agent
=================================================================
Capabilities:
  - Wakes every 6 hours (configurable)
  - Reads ALL backend/*.py files for context
  - Edits any Python file in backend/ safely (backup + syntax check + rollback)
  - Creates NEW files in backend/ if needed
  - Auto git commit + push to GitHub after every change
  - Portfolio audit + grid backtest optimizer
  - Qwen LLM decision (cheapest model first — TOKEN EFFICIENT)
  - Full audit log to ai_supervisor_log.json
  
Design Principles (Token & Memory Efficient):
  - Prompts kept SHORT — only essential data sent to LLM
  - max_tokens=400 per call (sufficient for JSON decision)
  - Files read on demand only — not all loaded at once
  - Optimizer works on last 80 tokens max (no memory bloat)
"""

import os
import sys
import re
import time
import json
import sqlite3
import subprocess
import requests
from datetime import datetime
from duckduckgo_search import DDGS

def search_web(query: str, max_results: int = 3) -> str:
    """Search DuckDuckGo and return summary."""
    try:
        results = DDGS().text(query, max_results=max_results)
        return json.dumps([{"title": r.get("title"), "body": r.get("body")} for r in results])
    except Exception as e:
        return f"[SEARCH ERROR] {e}"
from dotenv import load_dotenv

# ===================== PATH SETUP =====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
ENV_PATH = os.path.join(ROOT_DIR, ".env")
DB_PATH = os.path.join(CURRENT_DIR, "historical_candles.db")
PARAMS_FILE = os.path.join(CURRENT_DIR, "dynamic_params.json")
PAPER_PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")
LOG_FILE = os.path.join(CURRENT_DIR, "ai_supervisor_log.json")
JOURNAL_FILE = os.path.join(CURRENT_DIR, "ai_lab_journal.json")
INTERVAL_HOURS = 6
BACKEND_DIR = CURRENT_DIR

load_dotenv(ENV_PATH)
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "codesbykhairannoor/dexhelp")

# ===================== QWEN LLM (cheapest first, token-efficient) =====================
def ask_qwen(prompt: str, max_tokens: int = 2500) -> str:
    """Send prompt to Qwen API via Alibaba DashScope (OpenAI Compatible) with 5-tier graceful fallback."""
    # List 5 model Alibaba dari yang paling hemat (murah/cepat) sampai yang paling canggih (mahal)
    models = [
        "qwen3.5-plus-2026-02-15",     # Model terbaru, kuota 1 Miliar
        "qwen-plus-2025-07-28",        # Kuota 1 Miliar
        "qwen3-max",                   # Paling pintar, kuota 1 Miliar
        "qwen-coder-plus",             # Spesialis JSON/Kode
        "qwen-turbo"                   # Cepat dan ringan
    ]
    if not QWEN_API_KEY:
        return "NO_API_KEY"
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    for model_name in models:
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            r = requests.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers, json=payload, timeout=60
            )
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"].strip()
                print(f"         [AI] Model used: {model_name}")
                return reply
            elif r.status_code in [429, 403] or "quota" in r.text.lower() or "free tier" in r.text.lower():
                print(f"         [AI] {model_name} quota/rate-limited. Switching...")
                continue
            else:
                print(f"         [AI] {model_name} HTTP {r.status_code}. Switching...")
                continue
        except Exception as e:
            print(f"         [AI] {model_name} error: {e}. Switching...")
            continue
    return "ALL_MODELS_FAILED"

# ===================== GITHUB AUTO-PUSH =====================
def git_push_changes(commit_message: str, changed_files: list) -> bool:
    """Stage specific files, commit, and push using GITHUB_TOKEN."""
    try:
        if not GITHUB_TOKEN:
            print("         [GIT] No GITHUB_TOKEN configured. Skipping push.")
            return False

        # Configure git remote with token auth (works on VPS)
        remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        subprocess.run(["git", "remote", "set-url", "origin", remote_url],
                       cwd=ROOT_DIR, capture_output=True)

        # Stage only the changed files
        for f in changed_files:
            subprocess.run(["git", "add", f], cwd=ROOT_DIR, capture_output=True)

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", f"[AI-SUPERVISOR] {commit_message}"],
            cwd=ROOT_DIR, capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout:
            print("         [GIT] No changes to commit.")
            return True

        # Push
        push = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=ROOT_DIR, capture_output=True, text=True
        )
        if push.returncode == 0:
            print(f"         [GIT] Pushed to GitHub: {commit_message}")
            return True
        else:
            print(f"         [GIT] Push failed: {push.stderr[:200]}")
            return False
    except Exception as e:
        print(f"         [GIT] Exception: {e}")
        return False

# ===================== FILE SYSTEM TOOLS =====================
def list_backend_files() -> list:
    """Return list of all Python files in backend directory."""
    py_files = []
    for f in sorted(os.listdir(BACKEND_DIR)):
        if f.endswith(".py") and not f.startswith("__"):
            py_files.append(f)
    return py_files

def read_file_snippet(filename: str, max_chars: int = 800) -> str:
    """Read first N chars of a file for context (memory efficient)."""
    filepath = os.path.join(BACKEND_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_chars)
        return content
    except Exception as e:
        return f"[ERROR reading {filename}: {e}]"

def safe_edit_file(filename: str, old_snippet: str, new_snippet: str) -> bool:
    """
    Replace old_snippet with new_snippet in filename.
    Creates backup. Verifies Python syntax. Rolls back on failure.
    """
    filepath = os.path.join(BACKEND_DIR, filename)
    if not os.path.exists(filepath):
        print(f"         [EDIT] File not found: {filename}")
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if old_snippet not in content:
            print(f"         [EDIT] Snippet not found in {filename}. Skipping.")
            return False
        new_content = content.replace(old_snippet, new_snippet, 1)
        # Backup
        with open(filepath + ".bak", "w", encoding="utf-8") as f:
            f.write(content)
        # Write new
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        # Verify syntax
        check = subprocess.run(
            [sys.executable, "-m", "py_compile", filepath],
            capture_output=True, text=True
        )
        if check.returncode != 0:
            print(f"         [EDIT] Syntax error! Rolling back {filename}...")
            with open(filepath + ".bak", "r", encoding="utf-8") as f:
                original = f.read()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(original)
            return False
        print(f"         [EDIT] {filename} edited and syntax verified OK.")
        return True
    except Exception as e:
        print(f"         [EDIT] Exception: {e}")
        return False

def create_new_file(filename: str, content: str) -> bool:
    """Create a new Python file in backend/."""
    if not filename.endswith(".py"):
        filename += ".py"
    filepath = os.path.join(BACKEND_DIR, filename)
    if os.path.exists(filepath):
        print(f"         [CREATE] {filename} already exists. Skipping.")
        return False
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        # Verify syntax
        import sys
        check = subprocess.run(
            [sys.executable, "-m", "py_compile", filepath],
            capture_output=True, text=True
        )
        if check.returncode != 0:
            print(f"         [CREATE] Syntax error in new file! Deleting...")
            os.remove(filepath)
            return False
        print(f"         [CREATE] New file {filename} created and verified.")
        return True
    except Exception as e:
        print(f"         [CREATE] Exception: {e}")
        return False

# ===================== PORTFOLIO AUDIT =====================
def audit_portfolio() -> dict:
    result = {
        "wallet_balance": 1000.0, "initial_capital": 1000.0,
        "total_pnl_usd": 0.0, "total_trades": 0,
        "wins": 0, "losses": 0, "win_rate": 0.0,
        "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
        "recent_trades": [], "exit_distribution": {}
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
                {"sym": t.get("symbol", "?"), "pnl": round(t.get("pnl_pct", 0), 1),
                 "exit": t.get("exit_reason", t.get("alasan", "?"))}
                for t in history[-10:]
            ]
            for t in history:
                r = t.get("exit_reason", t.get("alasan", "UNKNOWN"))
                result["exit_distribution"][r] = result["exit_distribution"].get(r, 0) + 1
    except Exception as e:
        print(f"         [AUDIT] Error: {e}")
    return result

# ===================== GRID BACKTEST OPTIMIZER =====================
def simulate_trade(candles, entry, tp, sl, tb, mm):
    sl_p = entry * (1 - sl / 100.0)
    tp_p = entry * (1 + tp / 100.0)
    for i, c in enumerate(candles):
        if c["high"] >= tp_p: return tp, "W"
        if c["low"] <= sl_p: return ((sl_p - entry) / entry) * 100, "L"
        if i == int(tb):
            pnl = ((c["close"] - entry) / entry) * 100
            if pnl < mm: return pnl, "TB"
    return ((candles[-1]["close"] - entry) / entry) * 100, "H"

def run_optimization() -> dict | None:
    if not os.path.exists(DB_PATH): return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT address, symbol FROM tokens")
    tokens = cur.fetchall()
    datasets = []
    for tok in tokens[-80:]:
        cur.execute("SELECT open,high,low,close FROM candles_1m WHERE address=? ORDER BY timestamp ASC", (tok["address"],))
        c = cur.fetchall()
        if len(c) >= 3 and c[0]["open"] > 0:
            datasets.append({"c": c, "e": c[0]["open"]})
    conn.close()
    if not datasets: return None
    best_pnl, best_p, best_wr = -999999.0, (20, 15, 1, 0), 0.0
    for tp in [5,10,15,20,25,30,50]:
        for sl in [5,10,15,20]:
            for tb in [0.5,1,2,3]:
                for mm in [-3,0,2]:
                    tot, w = 0.0, 0
                    for d in datasets:
                        p, _ = simulate_trade(d["c"], d["e"], tp, sl, tb, mm)
                        tot += p
                        if p > 0: w += 1
                    if tot > best_pnl:
                        best_pnl = tot
                        best_p = (tp, sl, tb, mm)
                        best_wr = w / len(datasets) * 100
    return {"tp_pct": float(best_p[0]), "sl_pct": float(best_p[1]),
            "time_bomb_mins": float(best_p[2]), "min_momentum_pct": float(best_p[3]),
            "backtest_pnl": round(best_pnl, 2), "backtest_wr": round(best_wr, 1),
            "data_points": len(datasets)}

def load_current_params() -> dict:
    try:
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE) as f: return json.load(f)
    except: pass
    return {"tp_pct": 20.0, "sl_pct": 15.0, "time_bomb_mins": 1.0, "min_momentum_pct": 0.0}
# ===================== AI DECISION PROMPT (AGENTIC LOOP) =====================
def build_prompt(portfolio: dict, opt: dict, cur_p: dict, file_list: list, config_content: str, journal_context: str) -> str:
    return f"""You are an elite AI Quant Trading Manager. You have full freedom to adapt strategies. Return JSON only.

LIVE PERFORMANCE: WR={portfolio['win_rate']:.0f}% PnL=${portfolio['total_pnl_usd']:+.2f} Trades={portfolio['total_trades']}
EXIT BREAKDOWN: {json.dumps(portfolio['exit_distribution'])}
LAST 10: {json.dumps(portfolio['recent_trades'])}
CURRENT PARAMS: TP={cur_p.get('tp_pct')}% SL={cur_p.get('sl_pct')}% TB={cur_p.get('time_bomb_mins')}min
OPTIMIZER SAYS: TP={opt['tp_pct']}% SL={opt['sl_pct']}% TB={opt['time_bomb_mins']}min WR={opt['backtest_wr']}% PnL={opt['backtest_pnl']}%

--- CURRENT config.py ---
{config_content}
-------------------------

--- LAB JOURNAL (MEMORY) ---
{journal_context}
----------------------------

AVAILABLE FILES: {file_list}

RULES & CAPABILITIES:
1. "time_bomb_mins", "sl_pct", "tp_pct" MUST be updated via the JSON fields below. Do NOT edit .py files for these.
2. You have FULL AUTHORITY to edit `config.py` to adapt to the market. For example, if trades are losing, you can increase `MIN_ENTRY_SCORE` or `MIN_LIQ` to be more selective. If trades are too few, you can lower them.
3. To edit `config.py`, provide the EXACT `old_snippet` as it appears in the code above, and your `new_snippet`.
4. You may create new .py modules if you invent a new strategy component.
5. CRITICAL: Read the LAB JOURNAL. If your previous hypothesis failed or was repeated, DO NOT repeat it. Invent a COMPLETELY NEW hypothesis and try editing different parameters.
6. CRITICAL: If Trades=0, your filters are TOO STRICT. You MUST loosen MIN_ENTRY_SCORE, MIN_VOL_5M, or MAX_AGE_MINUTES to get trades!
7. Available actions: "read_file", "search_web", "commit_changes".
7. If you want to read a file, return: {{"action": "read_file", "file": "filename.py"}}
8. If you want to research the market, return: {{"action": "search_web", "query": "solana memecoin meta today"}}
9. If you are ready to apply changes and finish the cycle, return: {{"action": "commit_changes", "apply_new_params": true, "tp_pct": 20.0, "sl_pct": 15.0, "time_bomb_mins": 1.0, "file_edits": [], "new_files": [], "hypothesis": "Explain your logic"}}
10. When committing file edits, you MUST provide the filename: {{"file": "config.py", "old_snippet": "exact old", "new_snippet": "exact new"}}
11. You MUST write a unique `hypothesis` when you commit changes so you can review it in the next cycle's LAB JOURNAL.

Return STRICT JSON:"""

# ===================== LOG & JOURNAL =====================
def append_log(entry: dict):
    logs = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f: logs = json.load(f)
    except: pass
    logs.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs[-100:], f, indent=2)

def load_journal() -> list:
    try:
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE) as f: return json.load(f)
    except: pass
    return []

def append_journal(entry: dict):
    journal = load_journal()
    journal.append(entry)
    with open(JOURNAL_FILE, "w") as f:
        json.dump(journal[-10:], f, indent=2)

# ===================== CORE CYCLE =====================
def run_supervisor():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 65)
    print(f"[AI-SUPERVISOR v5.0 AGI] AWAKENED @ {now}")
    print("=" * 65)

    print("[1] Auditing portfolio...")
    portfolio = audit_portfolio()
    print(f"    WR={portfolio['win_rate']:.0f}% PnL=${portfolio['total_pnl_usd']:+.2f} Trades={portfolio['total_trades']}")

    print("[2] Running optimizer...")
    opt = run_optimization()
    cur_p = load_current_params()
    if not opt:
        print("    [WARN] No historical data. Skipping optimizer, falling back to current params.")
        opt = {
            "tp_pct": cur_p.get("tp_pct", 20.0),
            "sl_pct": cur_p.get("sl_pct", 15.0),
            "time_bomb_mins": cur_p.get("time_bomb_mins", 1.0),
            "min_momentum_pct": cur_p.get("min_momentum_pct", 0.0),
            "backtest_wr": portfolio["win_rate"],
            "backtest_pnl": portfolio["total_pnl_usd"],
            "data_points": 0
        }
    print(f"    Best: TP={opt['tp_pct']}% SL={opt['sl_pct']}% TB={opt['time_bomb_mins']}m WR={opt['backtest_wr']}%")

    file_list = list_backend_files()
    config_content = read_file_snippet("config.py", 2000)
    
    # Format Journal Context
    journal_entries = load_journal()
    journal_context = "No previous memory."
    if journal_entries:
        journal_context = "\n".join([f"Cycle {e['ts']} - Hypothesis: {e['hypothesis']}" for e in journal_entries[-3:]])

    print("[3] Consulting Qwen AI (Agentic Loop)...")
    prompt = build_prompt(portfolio, opt, cur_p, file_list, config_content, journal_context)
    
    decision = None
    for iteration in range(5): # Max 5 turns
        print(f"    Iteration {iteration+1}...")
        ai_raw = ask_qwen(prompt, max_tokens=2500)
        
        parsed = None
        try:
            clean_raw = ai_raw.replace("```json", "").replace("```", "").strip()
            s = clean_raw.find("{"); e = clean_raw.rfind("}") + 1
            if s >= 0 and e > s:
                parsed = json.loads(clean_raw[s:e])
        except Exception as e: 
            print(f"    [WARN] JSON Parse Error: {e}")

        if not parsed:
            print("    [WARN] Invalid JSON from AI. Retrying...")
            prompt += f"\n\n[SYSTEM] Invalid JSON format. Return ONLY valid JSON block. Error preview: {ai_raw[:50]}"
            continue
            
        action = parsed.get("action", "commit_changes")
        
        if action == "read_file":
            target_file = parsed.get("file")
            print(f"    [AI ACTION] Reading file: {target_file}")
            content = read_file_snippet(target_file, 5000)
            prompt += f"\n\n[USER: File {target_file} Content]\n{content}\nWhat is your next action?"
            continue
            
        elif action == "search_web":
            query = parsed.get("query")
            print(f"    [AI ACTION] Web Search: {query}")
            results = search_web(query)
            prompt += f"\n\n[USER: Web Search Results for '{query}']\n{results}\nWhat is your next action?"
            continue
            
        elif action == "commit_changes":
            decision = parsed
            print(f"    [AI ACTION] Commit Changes. Hypothesis: {decision.get('hypothesis', 'None')}")
            break
            
        else:
            print(f"    [WARN] Unknown action: {action}")
            break

    if not decision:
        print("    [WARN] No final decision reached. Rule-based fallback.")
        needs_action = portfolio["total_pnl_usd"] < 0 or portfolio["total_trades"] == 0
        decision = {
            "apply_new_params": needs_action,
            "tp_pct": opt["tp_pct"], "sl_pct": opt["sl_pct"],
            "time_bomb_mins": opt["time_bomb_mins"], "min_momentum_pct": opt["min_momentum_pct"],
            "file_edits": [], "new_files": [],
            "hypothesis": f"Fallback. PnL={portfolio['total_pnl_usd']:.2f} Trades={portfolio['total_trades']}"
        }

    changed_files = []

    # --- Apply file edits ---
    file_edits = decision.get("file_edits", [])
    if file_edits:
        print(f"[4] Applying {len(file_edits)} file edit(s)...")
        for edit in file_edits:
            fname = edit.get("file", "")
            old_snip = edit.get("old_snippet", "")
            new_snip = edit.get("new_snippet", "")
            reason = edit.get("reason", "")
            if not fname or not old_snip or not new_snip:
                continue
            success = safe_edit_file(fname, old_snip, new_snip)
            if success:
                changed_files.append(f"backend/{fname}")
                print(f"    Edited: {fname} — {reason}")
    else:
        print("[4] No file edits requested.")

    # --- Create new files ---
    new_files = decision.get("new_files", [])
    if new_files:
        print(f"[5] Creating {len(new_files)} new file(s)...")
        for nf in new_files:
            fname = nf.get("filename", "")
            content = nf.get("content", "")
            reason = nf.get("reason", "")
            if not fname or not content:
                continue
            success = create_new_file(fname, content)
            if success:
                changed_files.append(f"backend/{fname}")
                print(f"    Created: {fname} — {reason}")
    else:
        print("[5] No new files requested.")

    # --- Apply trading params ---
    if decision.get("apply_new_params"):
        print("[6] Updating trading parameters...")
        new_params = {
            "trade_mode": "HIT_AND_RUN",
            "tp_pct": float(decision.get("tp_pct", opt["tp_pct"])),
            "sl_pct": float(decision.get("sl_pct", opt["sl_pct"])),
            "time_bomb_mins": float(decision.get("time_bomb_mins", opt["time_bomb_mins"])),
            "min_momentum_pct": float(decision.get("min_momentum_pct", 0.0)),
            "last_updated": now,
            "ai_reasoning": decision.get("hypothesis", "")
        }
        with open(PARAMS_FILE, "w") as f:
            json.dump(new_params, f, indent=4)
        changed_files.append("backend/dynamic_params.json")
        print(f"    Params: TP={new_params['tp_pct']}% SL={new_params['sl_pct']}% TB={new_params['time_bomb_mins']}m")
        print("[7] Rebooting fleet via PM2...")
        os.system("pm2 restart bot-paper")
        os.system("pm2 restart bot-real")
    else:
        print(f"[6] No param changes. {decision.get('hypothesis', '')}")

    # --- Git push if anything changed ---
    if changed_files:
        print(f"[8] Pushing {len(changed_files)} changed file(s) to GitHub...")
        summary = decision.get("hypothesis", "Auto-optimization cycle")
        git_push_changes(summary, changed_files)
    else:
        print("[8] No changes to push.")

    # --- Log & Journal ---
    append_log({
        "ts": now,
        "portfolio": {"bal": portfolio["wallet_balance"], "pnl": portfolio["total_pnl_usd"],
                      "wr": portfolio["win_rate"], "trades": portfolio["total_trades"]},
        "opt": opt, "decision": decision,
        "changed_files": changed_files
    })
    
    append_journal({
        "ts": now,
        "hypothesis": decision.get("hypothesis", "No hypothesis provided")
    })
    
    print(f"[LOG] Saved to ai_supervisor_log.json and ai_lab_journal.json")
    print(f"[AI-SUPERVISOR] Done. Sleeping {INTERVAL_HOURS}h...\n")

# ===================== MAIN =====================
if __name__ == "__main__":
    while True:
        try:
            run_supervisor()
        except Exception as e:
            import traceback
            print(f"[AI-SUPERVISOR] CRITICAL: {e}")
            traceback.print_exc()
        time.sleep(INTERVAL_HOURS * 3600)
