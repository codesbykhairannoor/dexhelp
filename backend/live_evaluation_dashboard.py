import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environmental variables from standard locations
load_dotenv()
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(CURRENT_DIR)
load_dotenv(os.path.join(parent_dir, ".env"))
load_dotenv(os.path.join(CURRENT_DIR, ".env"))

def calculate_active_sl(pos, current_price, trade_mode):
    entry_price = pos.get("entry_price")
    highest_price = max(pos.get("highest_price", entry_price), current_price)
    price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
    
    partial_tp_hit = pos.get("partial_tp_hit", False)
    
    sl_price = entry_price * 0.80  # Default fallback
    trail_level = "INITIAL SL (20%)"
    
    if trade_mode == "ULTRA_SCALPER":
        if partial_tp_hit:
            if price_gain_pct >= 800.0:
                sl_price = highest_price * 0.75
                trail_level = "ULTRA TSL 25%"
            elif price_gain_pct >= 300.0:
                sl_price = highest_price * 0.70
                trail_level = "ULTRA TSL 30%"
            elif price_gain_pct >= 100.0:
                sl_price = highest_price * 0.65
                trail_level = "ULTRA TSL 35%"
            else:
                sl_price = entry_price * 1.02
                trail_level = "ULTRA BE-LOCK (+2%)"
        else:
            sl_price = entry_price * 0.80
            trail_level = "ULTRA INITIAL SL (20%)"
    elif trade_mode == "MOONSHOT":
        if price_gain_pct >= 800.0:
            sl_price = highest_price * 0.75
            trail_level = "STAGE 3 (25% TSL)"
        elif price_gain_pct >= 300.0:
            sl_price = highest_price * 0.70
            trail_level = "STAGE 2 (30% TSL)"
        elif price_gain_pct >= 100.0:
            sl_price = highest_price * 0.65
            trail_level = "STAGE 1 (35% TSL)"
        else:
            sl_price = highest_price * 0.70
            trail_level = "MOONSHOT INITIAL SL (30%)"
    elif trade_mode == "SCALPER":
        if price_gain_pct >= 400.0:
            sl_price = highest_price * 0.70
            trail_level = "STAGE 4 (30% TSL)"
        elif price_gain_pct >= 150.0:
            sl_price = highest_price * 0.75
            trail_level = "STAGE 3 (25% TSL)"
        elif price_gain_pct >= 60.0:
            sl_price = highest_price * 0.80
            trail_level = "STAGE 2 (20% TSL)"
        elif price_gain_pct >= 30.0:
            sl_price = entry_price * 1.15
            trail_level = "STAGE 1 (+15% LOCK)"
        elif price_gain_pct >= 15.0:
            sl_price = entry_price * 1.02
            trail_level = "BE-LOCK (+2%)"
        else:
            sl_price = highest_price * 0.80
            trail_level = "TRAILING SL (20%)"
    else:  # OPTIMIZED
        if price_gain_pct >= 150.0:
            sl_price = highest_price * 0.75
            trail_level = "STAGE 3 (25% TSL)"
        elif price_gain_pct >= 60.0:
            sl_price = highest_price * 0.80
            trail_level = "STAGE 2 (20% TSL)"
        elif price_gain_pct >= 20.0:
            sl_price = entry_price * 1.02
            trail_level = "BE-LOCK (+2%)"
        else:
            sl_price = highest_price * 0.90
            trail_level = "OPTIMIZED INITIAL SL (10%)"
            
    return sl_price, trail_level

def run_evaluation_dashboard():
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")
    
    if not os.path.exists(PORTFOLIO_FILE):
        print("[ERROR] File paper_portfolio.json tidak ditemukan! Jalankan bot atau reset database terlebih dahulu.")
        return
        
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            portfolio = json.load(f)
    except Exception as e:
        print(f"[ERROR] Gagal membaca file database: {e}")
        return
        
    wallet_balance = portfolio.get("wallet_balance", 1000.00)
    active_positions = portfolio.get("active_positions", {})
    trade_history = portfolio.get("trade_history", [])
    cooldowns = portfolio.get("cooldowns", {})
    initial_capital = portfolio.get("initial_capital", 1000.00)
    
    # Load JUPITER_API_KEY from .env
    jupiter_key = os.getenv("JUPITER_API_KEY", "jup_0872d0ca9886efca00560439b283c2bc25821ab36727457792ce61ca352c2f60")
    if not os.getenv("JUPITER_API_KEY"):
        parent_dir = os.path.dirname(CURRENT_DIR)
        env_path = os.path.join(parent_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as ef:
                for line in ef:
                    if "JUPITER_API_KEY" in line and "=" in line:
                        jupiter_key = line.split("=")[-1].strip().strip('"').strip("'")
                        break
                        
    # Gather tokens to fetch: active tokens + closed tokens for Post-Exit Audit
    show_all = len(sys.argv) > 1 and sys.argv[1].lower() in ["--all", "all"]
    tokens_to_query = list(active_positions.keys())
    
    if show_all:
        closed_audit_list = trade_history
    else:
        closed_audit_list = trade_history[-10:]
        
    for t in closed_audit_list:
        addr = t.get("address")
        if addr and addr not in tokens_to_query:
            tokens_to_query.append(addr)
            
    # Fetch live prices for selected tokens using Jupiter + DexScreener Fallback
    price_map = {}
    if tokens_to_query:
        # 1. Try Jupiter Price API
        addr_str = ",".join(tokens_to_query)
        url = f"https://api.jup.ag/price/v3?ids={addr_str}"
        headers = {"x-api-key": jupiter_key, "Accept": "application/json"}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                res = r.json()
                data = res.get("data", {}) if "data" in res else res
                for addr in tokens_to_query:
                    tinfo = data.get(addr, {})
                    price = tinfo.get("usdPrice") or tinfo.get("price")
                    if price is not None:
                        price_map[addr] = float(price)
        except Exception:
            pass
            
        # 2. Fallback to DexScreener for any missing prices
        missing_addrs = [addr for addr in tokens_to_query if addr not in price_map]
        for addr in missing_addrs:
            try:
                ds_url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
                res = requests.get(ds_url, timeout=5).json()
                pairs = res.get("pairs", []) or []
                if pairs:
                    pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
                    price = pairs[0].get("priceUsd")
                    if price is not None:
                        price_map[addr] = float(price)
            except Exception:
                pass

    # --- CALCULATIONS ---
    total_active_value = 0.0
    active_positions_list = []
    trade_mode = os.getenv("TRADE_MODE", "OPTIMIZED").upper()
    
    for addr, pos in active_positions.items():
        entry_price = pos["entry_price"]
        net_investment = pos["net_investment"]
        qty = pos["qty"]
        current_price = price_map.get(addr, entry_price)
        current_val = qty * current_price
        pnl_usd = current_val - pos.get("gross_investment", net_investment)
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Calculate active SL and trailing level guard
        sl_price, guard_status = calculate_active_sl(pos, current_price, trade_mode)
        
        if current_price > 0:
            sl_dist_pct = ((current_price - sl_price) / current_price) * 100
        else:
            sl_dist_pct = 0.0
            
        partial_tp = "SECURED (20% Left)" if pos.get("partial_tp_hit", False) else "PENDING"
        highest_price = max(pos.get("highest_price", entry_price), current_price)
        
        total_active_value += current_val
        active_positions_list.append({
            "symbol": pos["symbol"],
            "entry_price": entry_price,
            "current_price": current_price,
            "highest_price": highest_price,
            "invested": pos.get("gross_investment", net_investment),
            "current_val": current_val,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "sl_price": sl_price,
            "sl_dist_pct": sl_dist_pct,
            "partial_tp": partial_tp,
            "guard_status": guard_status
        })
        
    total_portfolio_value = wallet_balance + total_active_value
    net_pnl_usd = total_portfolio_value - initial_capital
    net_pnl_pct = (net_pnl_usd / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    # Win rate analytics (Fix: Prevent default 0 from making all paper losses count as wins)
    wins = []
    losses = []
    for t in trade_history:
        pnl = None
        if "pnl_pct" in t:
            pnl = t["pnl_pct"]
        elif "pnl_usd" in t:
            pnl = t["pnl_usd"]
        elif "pnl_sol" in t:
            pnl = t["pnl_sol"]
            
        if pnl is not None:
            if pnl >= 0:
                wins.append(t)
            else:
                losses.append(t)
        else:
            wins.append(t)  # Fallback for empty transactions
            
    total_closed_trades = len(trade_history)
    win_rate = (len(wins) / total_closed_trades * 100) if total_closed_trades > 0 else 0.0
    
    # Render dashboard
    print("=" * 110)
    print("🛰️  SOLANA DEX PREDATOR - LIVE PERFORMANCE EVALUATION DASHBOARD V13.0 AUDIT")
    print("=" * 110)
    
    # Section 1: Wallet Performance Summary
    print("[1] RINGKASAN PORTOFOLIO:")
    print(f"    Modal Awal (Murni) : ${initial_capital:,.2f} USD")
    print(f"    Saldo Kas Tunai     : ${wallet_balance:,.4f} USD")
    print(f"    Nilai Aset Aktif    : ${total_active_value:,.4f} USD")
    print(f"    TOTAL NILAI PORTO   : ${total_portfolio_value:,.4f} USD")
    print(f"    Akumulasi PnL Neto  : {net_pnl_pct:+.2f}% ({net_pnl_usd:+.2f} USD)")
    print("-" * 110)
    
    # Section 2: Active Positions Table
    print(f"[2] POSISI AKTIF YANG SEDANG DIPANTAU ({len(active_positions_list)}/10) [MODE: {trade_mode}]:")
    if active_positions_list:
        print(f"    {'SYMBOL':<10} | {'INVESTED':<8} | {'ENTRY PRICE':<12} | {'LIVE PRICE':<12} | {'PnL %':<8} | {'PnL USD':<12} | {'PEAK PRICE':<12} | {'SL PRICE':<12} | {'SL DIST %':<9} | {'PARTIAL TP':<15} | {'GUARD STATUS'}")
        print("    " + "-" * 155)
        for pos in active_positions_list:
            print(f"    {pos['symbol']:<10} | ${pos['invested']:<7.2f} | ${pos['entry_price']:<11.8f} | ${pos['current_price']:<11.8f} | {pos['pnl_pct']:+7.2f}% | {pos['pnl_usd']:+8.2f} USD | ${pos['highest_price']:<11.8f} | ${pos['sl_price']:<11.8f} | {pos['sl_dist_pct']:+8.2f}% | {pos['partial_tp']:<15} | {pos['guard_status']}")
    else:
        print("    (Tidak ada posisi aktif saat ini)")
    print("-" * 155)
    
    # Section 3: Closed Trades History Table + Post-Exit Audit
    limit_text = "Semua Transaksi" if show_all else "10 Transaksi Terakhir"
    print(f"[3] RIWAYAT CLOSED TRADES & POST-EXIT AUDIT ({limit_text}):")
    if trade_history:
        print(f"    {'SYMBOL':<10} | {'ENTRY':<12} | {'EXIT':<12} | {'PnL %':<8} | {'EXIT REASON':<26} | {'LIVE NOW':<12} | {'POST-CHG %':<10} | {'AUDIT EVALUATION'}")
        print("    " + "-" * 145)
        
        for t in closed_audit_list:
            addr = t.get("address")
            exit_price = t["exit_price"]
            live_price = price_map.get(addr, 0.0)
            
            pnl_pct = t.get("pnl_pct")
            # Fallback if pnl_pct is not recorded in SOL trades
            if pnl_pct is None:
                pnl_pct = float(t.get("pnl_sol", 0.0)) * 100.0 # Estimate
                
            exit_reason = t.get("exit_reason") or t.get("reason") or "UNKNOWN"
            
            post_exit_chg = 0.0
            audit_eval = "⏱️ NO DATA"
            
            if live_price > 0 and exit_price > 0:
                post_exit_chg = ((live_price - exit_price) / exit_price) * 100
                if post_exit_chg <= -20.0:
                    audit_eval = f"🛡️ GOOD EXIT (Dump {post_exit_chg:+.1f}%)"
                elif post_exit_chg >= 50.0:
                    audit_eval = f"⚠️ MISSED PUMP ({post_exit_chg:+.1f}%)"
                else:
                    audit_eval = "✅ ACCURATE EXIT"
            elif exit_price > 0:
                audit_eval = "💀 RUGGED/DELISTED (0.00)"
                
            print(f"    {t['symbol']:<10} | ${t['entry_price']:<11.8f} | ${exit_price:<11.8f} | {pnl_pct:+7.2f}% | {exit_reason:<26} | ${live_price:<11.8f} | {post_exit_chg:+9.2f}% | {audit_eval}")
            
        if not show_all and len(trade_history) > 10:
            print(f"    ... dan {len(trade_history) - 10} transaksi lama lainnya.")
    else:
        print("    (Belum ada transaksi selesai)")
    print("-" * 145)
    
    # Section 4: Quant Win/Loss Analytics
    print("[4] ANALISIS STATISTIK PRESTASI TRADING:")
    print(f"    Tingkat Kemenangan (Win Rate) : {win_rate:.1f}% ({len(wins)} Menang / {len(losses)} Kalah)")
    print("-" * 110)
    
    # Section 5: Cooldown Shield Tracker
    print("[5] DAFTAR SHIELD COOLDOWN YANG AKTIF:")
    active_cooldowns = []
    current_time = time.time()
    for addr, end_time in cooldowns.items():
        time_left = int(end_time - current_time)
        if time_left > 0:
            # Try to match symbol from history or active, fallback to address
            sym = "UNKNOWN"
            for t in trade_history:
                if t["address"] == addr:
                    sym = t["symbol"]
                    break
            active_cooldowns.append(f"{sym} ({time_left // 3600}j {(time_left % 3600) // 60}m {(time_left % 60)}s)")
            
    if active_cooldowns:
        print("    " + ", ".join(active_cooldowns))
    else:
        print("    (Semua koin bersih dari cooldown, scanner bebas menyisir!)")
    print("=" * 110)

if __name__ == "__main__":
    run_evaluation_dashboard()
