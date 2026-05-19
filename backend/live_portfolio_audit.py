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
        
    # Load JUPITER_API_KEY from env or .env file
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

    # Bulk query active positions from Jupiter Premium Price API V3
    addr_list = list(active_positions.keys())
    addr_str = ",".join(addr_list)
    url = f"https://api.jup.ag/price/v3?ids={addr_str}"
    headers = {
        "x-api-key": jupiter_key,
        "Accept": "application/json"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"[ERROR] Gagal memanggil API Jupiter V3: HTTP {r.status_code}")
            return
            
        res = r.json()
        
        # Map latest price per token
        price_map = {}
        for addr in addr_list:
            tinfo = res.get(addr, {})
            price = tinfo.get("usdPrice")
            if price is not None:
                price_map[addr] = {"price": float(price)}
                    
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
        
        # Read starting capital directly from JSON state to avoid dynamic math discrepancies
        initial_capital = portfolio.get("initial_capital", 1000.00)
            
        net_portfolio_pnl_usd = total_portfolio_value - initial_capital
        net_portfolio_pnl_pct = (net_portfolio_pnl_usd / initial_capital) * 100 if initial_capital > 0 else 0.0
        
        print("[SUMMARY] RINGKASAN KINERJA PORTOFOLIO:")
        print("-" * 80)
        print(f"  Total Nilai Aset Aktif : ${total_active_value:.2f}")
        print(f"  Saldo Kas Tunai        : ${wallet_balance:.2f}")
        print(f"  TOTAL NILAI NET ASET   : ${total_portfolio_value:.2f}")
        print(f"  Modal Awal (Murni)     : ${initial_capital:.2f}")
        print(f"  Akumulasi PnL Bersih   : {net_portfolio_pnl_pct:+.2f}% ({net_portfolio_pnl_usd:+.2f} USD)")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan saat audit: {e}")

if __name__ == "__main__":
    audit_live_portfolio()
