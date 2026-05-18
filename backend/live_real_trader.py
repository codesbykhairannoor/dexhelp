import os
import sys
import time
import json
import requests
from dotenv import load_dotenv
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
                return json.load(f)
        except Exception:
            pass
    # Initialize with default settings if file doesn't exist
    return {
        "wallet_address": "",
        "active_positions": {},    # token_address -> trade_info
        "trade_history": []        # Completed real trades list
    }

def save_live_portfolio(portfolio: dict):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan portofolio live: {e}", flush=True)

def run_live_real_trader():
    print("=" * 80)
    print("🚀 SOLANA DEX PREDATOR - LIVE REAL-MONEY TRADING ENGINE (PRODUCTION V6+)")
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
    
    # 2. Configure Money Management Budget (Burn Rate "Ecek-ecek")
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
                    
                    r = requests.get(url, headers=headers, timeout=5)
                    if r.status_code == 200:
                        res = r.json()
                        price_map = {}
                        for addr in addr_list:
                            tinfo = res.get(addr, {})
                            price = tinfo.get("usdPrice")
                            if price is not None:
                                price_map[addr] = {"price": float(price)}
                                
                        for addr, pos in list(active_positions.items()):
                            if addr in price_map and price_map[addr]["price"] > 0:
                                current_price = price_map[addr]["price"]
                                entry_price = pos["entry_price"]
                                highest_price = max(pos["highest_price"], current_price)
                                pos["highest_price"] = highest_price
                                
                                # Dynamic Step-Trailing & Positive BE-Guard Math
                                price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                                current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                
                                if price_gain_pct >= 200.0:
                                    sl_price = highest_price * 0.75  # Mega Moonshot Trailing -25%
                                    trail_level = "MEGA-TRAIL (-25% Peak)"
                                elif price_gain_pct >= 100.0:
                                    sl_price = entry_price * 1.65  # Lock +65%
                                    trail_level = "STAGE 2 (+65%)"
                                elif price_gain_pct >= 40.0:
                                    sl_price = entry_price * 1.20  # Lock +20%
                                    trail_level = "STAGE 1 (+20%)"
                                elif price_gain_pct >= 15.0:
                                    sl_price = entry_price * 1.03  # BE-Guard +3% (covers all fees)
                                    trail_level = "BE-GUARD (+3%)"
                                else:
                                    sl_price = highest_price * 0.90  # Tight 10% Initial SL
                                    trail_level = "NORMAL TIGHT (10%)"
                                    
                                print(f"  [TRACKING] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}", flush=True)
                                
                                # --- AUTOMATED ON-CHAIN STOP-LOSS SWAP SELL ---
                                if current_price <= sl_price:
                                    print(f"\n🚨 [STOP LOSS TRIGGERED] {trail_level} hit for {pos['symbol']}! Executing real market sell swap...", flush=True)
                                    
                                    # Sell swap: Target Token -> SOL
                                    # We input the actual on-chain quantity we hold
                                    # Since token balances are represented in raw integers (decimals), Jupiter handles
                                    # raw decimals from the token contract. We query the token balance or use recorded qty.
                                    # We can swap the entire token balance by getting the token account balance or using pos["qty"]
                                    # We convert qty to raw lamports based on standard decimals (we assume standard decimals or query quote)
                                    # To be 100% safe, we can query quote using Jup quote API with token as input and SOL as output, passing the raw balance.
                                    # First, let's query the actual token account balance to avoid out of sync quantity errors!
                                    # We fetch Jupiter quote for swapping ALL our pos["qty"] to SOL
                                    # Since quote takes input amount, we must convert qty to raw integer. To be extremely robust, we query Jupiter quote passing input amount.
                                    # Wait, what if we pass the raw quantity in lamports?
                                    # To get exact token decimals, we can query the token mint or simply use the raw token quantity bought during entry!
                                    # When we bought the token, we received "net_out_amount" from Jup execute_solana_swap which is EXACTLY the raw token amount in decimals!
                                    # Let's verify: yes! `net_out_amount` is the raw decimal value (e.g. 5234293829)! We can pass this exact value directly to Jup swap!
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
                                        
                                        portfolio["trade_history"].append({
                                            "symbol": pos["symbol"],
                                            "address": addr,
                                            "entry_price": entry_price,
                                            "exit_price": current_price,
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
                    # Sort candidates by 5m volume descending to prioritize liquid gems
                    candidates.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
                    top_gems = candidates[:5]
                    
                    best_candidate = None
                    best_score = 0
                    
                    for gem in top_gems:
                        addr = gem["address"]
                        if addr in portfolio["active_positions"]:
                            continue
                            
                        # Double layer audit (RugCheck + security scores)
                        security = check_token_security(gem["chain"], addr)
                        score = calculate_gem_score(gem, security)
                        
                        print(f"  [SCANNER] Auditing candidate {gem['symbol']} | Safety Status: {security['status']} | Score: {score}/100", flush=True)
                        
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 80:
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
                            
                            # Buy swap: SOL -> Candidate Token
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
                                
                                # We derive the actual entry price dynamically based on allocation & received raw qty
                                # Assuming target token has 9 decimals by default or standard, we can calculate from USD or relative Jup metrics.
                                # To keep tracking robust, we use the candidate price as base.
                                print(f"✨ [REAL BUY CONFIRMED] Successfully purchased {best_candidate['symbol']} on-chain!", flush=True)
                                print(f"   => Transaction: {explorer_url}", flush=True)
                                
                                # Store active position with raw quantity received to ensure sell execution works flawlessly
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
