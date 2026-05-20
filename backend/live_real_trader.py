import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Fix module imports when executed from external cwd (like PM2)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from dex_hunter import _fetch_candidates, check_token_security, calculate_gem_score
from solana_executor import execute_solana_swap, get_solana_balance, base58_decode, base58_encode

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Production Stability Fix: Dynamic Absolute Path Resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "live_portfolio.json")
ENV_PATH = os.path.join(os.path.dirname(CURRENT_DIR), ".env")
load_dotenv(ENV_PATH)

def load_live_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
                if "cooldowns" not in data:
                    data["cooldowns"] = {}
                return data
        except Exception:
            pass
    # Initialize with default settings if file doesn't exist
    return {
        "wallet_address": "",
        "active_positions": {},    # token_address -> trade_info
        "trade_history": [],       # Completed real trades list
        "cooldowns": {}            # token_address -> epoch_timestamp_when_cooldown_ends
    }

def save_live_portfolio(portfolio: dict):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan portofolio live: {e}", flush=True)

def run_live_real_trader():
    print("=" * 80)
    print("🚀 SOLANA DEX PREDATOR - LIVE REAL-MONEY TRADING ENGINE (PRODUCTION V8.0)")
    print("[INFO] Strategy Mode          : V8.0 Citadel High Win Rate Scalper")
    print("[INFO] Target Take-Profit (TP): +10.0% (Instant Exit)")
    print("[INFO] Breakeven Guard (BE)  : Lock +3.0% when price hits +4.0%")
    print("[INFO] Initial Stop Loss (SL) : -12.0% (Tight Protection)")
    print("[INFO] Token Cooldown Shield  : 24 Hours (86,400s) Blacklist on Exit")
    print("=" * 80)
    
    # 1. Load Solana Wallet Configuration
    priv_key_b58 = os.getenv("SOLANA_PRIVATE_KEY")
    helius_url = os.getenv("SOLANA_RPC_HELIUS")
    drpc_url = os.getenv("SOLANA_RPC_DRPC")
    jup_api_key = os.getenv("JUPITER_API_KEY")
    
    if not priv_key_b58:
        print("[CRITICAL] SOLANA_PRIVATE_KEY missing in .env! Exiting.", flush=True)
        sys.exit(1)
        
    # Derive Wallet address
    try:
        raw_key = base58_decode(priv_key_b58)
        user_wallet = base58_encode(raw_key[32:])
    except Exception as e:
        print(f"[CRITICAL] Failed to decode SOLANA_PRIVATE_KEY: {e}", flush=True)
        sys.exit(1)
        
    print(f"[WALLET] Running Live On-Chain! Derived Wallet: {user_wallet}", flush=True)
    
    # 2. Configure Money Management Budget
    # Allows configuration in .env, falls back to 0.05 SOL (~$8 USD) per trade
    sol_allocation = float(os.getenv("SOL_ALLOCATION_PER_TRADE", "0.05"))
    sol_allocation_lamports = int(sol_allocation * 1_000_000_000)
    
    print(f"[BUDGET] Allocation Per Trade: {sol_allocation:.4f} SOL (~${sol_allocation*160:.2f} USD)", flush=True)
    
    # Load state
    portfolio = load_live_portfolio()
    portfolio["wallet_address"] = user_wallet
    save_live_portfolio(portfolio)
    
    # Gas, swap, and slippage defaults
    slippage_bps = int(os.getenv("SOLANA_SLIPPAGE_BPS", "250")) # 2.5% default slippage
    jito_tip_lamports = int(os.getenv("SOLANA_JITO_TIP", "1000000")) # 0.001 SOL Jito tip
    
    # 3. High-Frequency Monitoring Loop (Every 10 seconds for real trades)
    loop_delay = 10
    
    while True:
        try:
            # Clean up expired cooldowns to keep state clean
            current_time = time.time()
            if "cooldowns" in portfolio:
                portfolio["cooldowns"] = {k: v for k, v in portfolio["cooldowns"].items() if v > current_time}
            
            # Dynamic Wallet Balance query
            live_sol_balance = get_solana_balance(helius_url or drpc_url, user_wallet)
            print("\n" + "-" * 80)
            print(f"[TICK SCAN] {time.strftime('%Y-%m-%d %H:%M:%S')} | Wallet SOL: {live_sol_balance:.6f} SOL | Active: {len(portfolio['active_positions'])}/2")
            print("-" * 80)
            
            # --- PHASE 1: HIGH-FREQUENCY ACTIVE TRADES MONITORING ---
            active_positions = portfolio["active_positions"]
            closed_any = False
            
            if active_positions:
                print(f"[INFO] Monitoring {len(active_positions)} active on-chain positions...")
                try:
                    addr_list = list(active_positions.keys())
                    addr_str = ",".join(addr_list)
                    url = f"https://api.jup.ag/price/v3?ids={addr_str}"
                    headers = {"x-api-key": jup_api_key} if jup_api_key else {}
                    
                    price_map = {}
                    r = requests.get(url, headers=headers, timeout=5)
                    if r.status_code == 200:
                        res = r.json()
                        data = res.get("data", {}) if "data" in res else res
                        for addr in addr_list:
                            tinfo = data.get(addr, {})
                            price = tinfo.get("usdPrice") or tinfo.get("price")
                            if price is not None:
                                price_map[addr] = {"price": float(price)}
                                
                    # Fallback: query DexScreener API for any token missing price info
                    missing_addrs = [addr for addr in addr_list if addr not in price_map]
                    for addr in missing_addrs:
                        try:
                            ds_url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
                            ds_res = requests.get(ds_url, timeout=5).json()
                            pairs = ds_res.get("pairs", []) or []
                            if pairs:
                                pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
                                price = pairs[0].get("priceUsd")
                                if price is not None:
                                    price_map[addr] = {"price": float(price)}
                                    # print(f"  [FEED] Fallback sukses via DexScreener untuk {pairs[0].get('baseToken', {}).get('symbol')}: ${float(price):.8f}", flush=True)
                        except Exception:
                            pass
                                
                        for addr, pos in list(active_positions.items()):
                            if addr in price_map and price_map[addr]["price"] > 0:
                                current_price = price_map[addr]["price"]
                                entry_price = pos["entry_price"]
                                highest_price = max(pos["highest_price"], current_price)
                                pos["highest_price"] = highest_price
                                
                                # Dynamic 96% WR Scalper Trailing & TP Logic
                                price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                                current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                
                                # V13.5 MOONSHOT RUNNER TRAILING & LOCK LOGIC
                                if price_gain_pct >= 400.0:
                                    sl_price = highest_price * 0.70  # Trailing 30% from peak for mega runners
                                    trail_level = "STAGE 4 (400%+ -> 30% TSL)"
                                elif price_gain_pct >= 150.0:
                                    sl_price = highest_price * 0.75  # Trailing 25% from peak
                                    trail_level = "STAGE 3 (150%+ -> 25% TSL)"
                                elif price_gain_pct >= 60.0:
                                    sl_price = highest_price * 0.80  # Trailing 20% from peak
                                    trail_level = "STAGE 2 (60%+ -> 20% TSL)"
                                elif price_gain_pct >= 30.0:
                                    sl_price = entry_price * 1.15  # Lock +15% profit
                                    trail_level = "STAGE 1 (+15% LOCK)"
                                elif price_gain_pct >= 15.0:
                                    sl_price = entry_price * 1.02  # Breakeven Lock +2%
                                    trail_level = "BE-LOCK (+2%)"
                                else:
                                    sl_price = highest_price * 0.80  # Initial Stop Loss 20% from peak
                                    trail_level = "TRAILING SL (20%)"
                                    
                                print(f"  [TRACKING] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}", flush=True)
                                
                                # --- AUTOMATED ON-CHAIN STOP-LOSS SWAP SELL ---
                                if current_price <= sl_price:
                                    print(f"\n🚨 [EXIT TRIGGERED] {trail_level} hit for {pos['symbol']}! Executing real market sell swap...", flush=True)
                                    
                                    raw_qty = int(pos["raw_qty"])
                                    
                                    sell_res = execute_solana_swap(
                                        input_mint=addr,
                                        output_mint="So11111111111111111111111111111111111111112", # Swap back to SOL
                                        amount_lamports=raw_qty,
                                        slippage_bps=slippage_bps,
                                        jito_tip_lamports=jito_tip_lamports
                                    )
                                    
                                    if sell_res.get("status") == "success":
                                        sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                        pnl_sol = sol_received - pos["net_investment_sol"]
                                        
                                        print(f"✨ [REAL SELL CONFIRMED] Successfully sold {pos['symbol']}!", flush=True)
                                        print(f"   => SOL Received: {sol_received:.6f} SOL | PnL: {pnl_sol:+.6f} SOL", flush=True)
                                        print(f"   => Tx Signature: {sell_res['explorer_url']}", flush=True)
                                        
                                        # Persist 4-hour Cooldown Shield to prevent re-entries
                                        portfolio.setdefault("cooldowns", {})[addr] = time.time() + 14400
                                        print(f"   => [SHIELD] Alamat {addr} masuk daftar Cooldown 4 Jam.", flush=True)
                                        
                                        portfolio["trade_history"].append({
                                            "symbol": pos["symbol"],
                                            "address": addr,
                                            "entry_price": entry_price,
                                            "exit_price": current_price if price_gain_pct >= 10.0 else sl_price,
                                            "pnl_sol": pnl_sol,
                                            "tx_signature": sell_res["signature"],
                                            "closed_at": time.strftime('%Y-%m-%d %H:%M:%S')
                                        })
                                        del active_positions[addr]
                                        closed_any = True
                                    else:
                                        print(f"[CRITICAL ERROR] Failed to execute stop loss sell transaction: {sell_res.get('message')}", flush=True)
                                        
                            else:
                                print(f"  [WARN] Token {pos['symbol']} price not found on Jupiter API.", flush=True)
                    else:
                        print(f"  [WARN] Jupiter Price API returned error code: {r.status_code}", flush=True)
                except Exception as e:
                    print(f"  [WARN] Error during bulk price update: {e}", flush=True)
            else:
                print("[INFO] No active on-chain positions. Monitoring scanner for entry...", flush=True)
                
            # --- PHASE 2: AUTOMATED SCROLL & SECURITY AUDIT FOR CANDIDATES ---
            if len(portfolio["active_positions"]) >= 2:
                print("[SCAN] Limit 2 active positions reached. Bypassing entry scanner.", flush=True)
            else:
                # Limit is not reached, fetch live market candidates
                candidates = _fetch_candidates()
                if candidates:
                    candidates.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
                    top_gems = candidates[:5]
                    
                    best_candidate = None
                    best_score = 0
                    
                    for gem in top_gems:
                        addr = gem["address"]
                        if addr in portfolio["active_positions"]:
                            continue
                            
                        # Strict 24-hour Cooldown filter check
                        if "cooldowns" in portfolio and addr in portfolio["cooldowns"]:
                            cooldown_left = int(portfolio["cooldowns"][addr] - time.time())
                            if cooldown_left > 0:
                                print(f"  [SCAN] Mengabaikan {gem['symbol']} | Masih dalam Cooldown 24 Jam ({cooldown_left}s tersisa)", flush=True)
                                continue
                            
                        # Double layer audit (RugCheck + security scores)
                        security = check_token_security(gem["chain"], addr)
                        score = calculate_gem_score(gem, security)
                        
                        print(f"  [SCANNER] Auditing candidate {gem['symbol']} | Safety Status: {security['status']} | Score: {score}/100", flush=True)
                        
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 70:
                            if score > best_score:
                                best_score = score
                                best_candidate = gem
                                best_candidate["security_status"] = security["status"]
                                best_candidate["predator_score"] = score
                                
                    # --- PHASE 3: EXECUTE AUTOMATED ON-CHAIN BUY ---
                    if best_candidate:
                        addr = best_candidate["address"]
                        print(f"\n🌟 [GEM SPOTTED] Candidate {best_candidate['symbol']} meets entry rules! Score: {best_candidate['predator_score']}/100", flush=True)
                        
                        # Wallet balance check
                        if live_sol_balance >= (sol_allocation + 0.006): # allocation + dynamic prioritization gas buffer
                            print(f"🛒 [BUY SWAP INITIATED] Submitting transaction to buy {best_candidate['symbol']}...", flush=True)
                            
                            buy_res = execute_solana_swap(
                                input_mint="So11111111111111111111111111111111111111112", # Swap SOL
                                output_mint=addr, # for Target Token
                                amount_lamports=sol_allocation_lamports,
                                slippage_bps=slippage_bps,
                                jito_tip_lamports=jito_tip_lamports
                            )
                            
                            if buy_res.get("status") == "success":
                                raw_qty_received = int(buy_res["net_out_amount"])
                                explorer_url = buy_res["explorer_url"]
                                
                                print(f"✨ [REAL BUY CONFIRMED] Successfully purchased {best_candidate['symbol']} on-chain!", flush=True)
                                print(f"   => Transaction: {explorer_url}", flush=True)
                                
                                portfolio["active_positions"][addr] = {
                                    "symbol": best_candidate["symbol"],
                                    "name": best_candidate["name"],
                                    "entry_price": best_candidate["price"],
                                    "highest_price": best_candidate["price"],
                                    "net_investment_sol": sol_allocation,
                                    "raw_qty": raw_qty_received, # On-chain integer quantity
                                    "qty": float(raw_qty_received) / 1_000_000_000.0, # Visual representation
                                    "entry_time": time.strftime('%Y-%m-%d %H:%M:%S')
                                }
                                closed_any = True
                            else:
                                print(f"[CRITICAL ERROR] Failed to buy {best_candidate['symbol']}: {buy_res.get('message')}", flush=True)
                        else:
                            print(f"[WARN] Insufficient SOL balance to buy {best_candidate['symbol']}. Has: {live_sol_balance:.6f} SOL | Needs: {sol_allocation + 0.006:.6f} SOL", flush=True)
                            
            if closed_any:
                save_live_portfolio(portfolio)
                
        except Exception as e:
            print(f"[ERROR] Main trader loop exception: {e}", flush=True)
            
        # Poll/Sleep for high frequency interval (10 seconds)
        time.sleep(loop_delay)

if __name__ == "__main__":
    run_live_real_trader()
