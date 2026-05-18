import os
import json
import requests

def audit_live_portfolio():
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")
    
    if not os.path.exists(PORTFOLIO_FILE):
        print("[ERROR] File paper_portfolio.json tidak ditemukan!")
        return
        
    with open(PORTFOLIO_FILE, "r") as f:
        portfolio = json.load(f)
        
    wallet_balance = portfolio["wallet_balance"]
    active_positions = portfolio["active_positions"]
    
    print("=" * 80)
    print("[SYSTEM] AUDIT DETAIL PORTOFOLIO SIMULASI LIVE (DEX PREDATOR)")
    print("=" * 80)
    print(f"[CASH] Saldo Tunai di Dompet : ${wallet_balance:.4f}")
    
    if not active_positions:
        print("[INFO] Tidak ada posisi aktif saat ini.")
        print(f"[PORTFOLIO] Total Nilai Portofolio: ${wallet_balance:.4f}")
        return
        
    # Bulk query active positions from DexScreener
    addr_list = list(active_positions.keys())
    addr_str = ",".join(addr_list)
    url = f"https://api.dexscreener.com/latest/dex/tokens/{addr_str}"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"[ERROR] Gagal memanggil API DexScreener: HTTP {r.status_code}")
            return
            
        res = r.json()
        pairs = res.get("pairs", []) or []
        
        # Map latest price per token
        price_map = {}
        for p in pairs:
            t_addr = p.get("baseToken", {}).get("address")
            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            price = float(p.get("priceUsd", 0) or 0)
            if t_addr:
                if t_addr not in price_map or liq > price_map[t_addr]["liq"]:
                    price_map[t_addr] = {"price": price, "liq": liq}
                    
        print(f"[INFO] Memantau {len(active_positions)} Posisi Aktif Secara Real-Time:")
        print("-" * 80)
        
        total_active_value = 0.0
        total_net_investment = 0.0
        
        for addr, pos in active_positions.items():
            entry_price = pos["entry_price"]
            net_investment = pos["net_investment"]
            qty = pos["qty"]
            
            # Fetch current price or fallback to entry
            current_price = entry_price
            if addr in price_map:
                current_price = price_map[addr]["price"]
                
            current_value = qty * current_price
            pnl_usd = current_value - net_investment
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            total_active_value += current_value
            total_net_investment += net_investment
            
            print(f"   [POSITION] {pos['symbol']:<10} | Qty: {qty:,.2f}")
            print(f"      => Entry Price : ${entry_price:.8f} | Live Price : ${current_price:.8f}")
            print(f"      => Invested    : ${net_investment:.2f} | Current Val: ${current_value:.2f}")
            print(f"      => Unrealized  : {pnl_pct:+.2f}% (${pnl_usd:+.2f})")
            print("-" * 80)
            
        total_portfolio_value = wallet_balance + total_active_value
        net_portfolio_pnl = total_portfolio_value - 100.00 # Starting virtual was 100.00
        
        print("[SUMMARY] RINGKASAN KINERJA PORTOFOLIO:")
        print("-" * 80)
        print(f"  Total Nilai Aset Aktif : ${total_active_value:.2f}")
        print(f"  Saldo Kas Tunai        : ${wallet_balance:.2f}")
        print(f"  TOTAL NILAI NET ASET   : ${total_portfolio_value:.2f}")
        print(f"  Akumulasi PnL Bersih   : {net_portfolio_pnl:+.2f}% ({net_portfolio_pnl:+.2f} USD)")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan saat audit: {e}")

if __name__ == "__main__":
    audit_live_portfolio()
