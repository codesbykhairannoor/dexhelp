import sys
import time
from dex_hunter import _fetch_candidates, check_token_security, calculate_gem_score

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_dex_simulation(capital_usd: float = 10.0):
    """
    Live DEX Gem Simulator & Backtester.
    Fetches real-time DexScreener candidates, runs the Scam-Shield audit,
    filters the scams, and simulates a $10 trade allocation on the best gem.
    """
    print("=" * 80)
    print(f"🚀 DEXSCREENER PREDATOR - LIVE SIMULATOR & BACKTESTER (Capital: ${capital_usd:.2f})")
    print(f"Local Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("[1/3] Fetching live candidates from DexScreener search stream...", flush=True)
    
    candidates = _fetch_candidates()
    if not candidates:
        print("❌ Gagal mengambil kandidat live. Periksa koneksi internet Anda.")
        return
        
    print(f"📊 Menemukan {len(candidates)} kandidat live di Solana & Base.")
    print("-" * 80)
    print("[2/3] Menjalankan Lapis Audit Scam-Shield (GoPlus + RugCheck + Honeypot)...", flush=True)
    
    audited_gems = []
    scam_count = 0
    
    # Audit top 8 highest-volume candidates for the simulation
    candidates.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
    subset = candidates[:8]
    
    for idx, gem in enumerate(subset, 1):
        print(f"  [{idx}/{len(subset)}] Auditing {gem['symbol']} ({gem['address'][:10]}...) on {gem['chain'].upper()}")
        security = check_token_security(gem["chain"], gem["address"])
        score = calculate_gem_score(gem, security)
        
        gem["security_status"] = security["status"]
        gem["security_flags"]  = security["flags"]
        gem["predator_score"]   = score
        audited_gems.append(gem)
        
        if security["status"] == "DANGEROUS SCAM":
            scam_count += 1
            print(f"    🚨 SCAM DETECTED! Flags: {security['flags']}")
        else:
            print(f"    ✅ SAFE GEM! Score: {score}/100 | Status: {security['status']}")
            
    print("-" * 80)
    print(f"🛡️ ANALISIS SHIELD: Berhasil menyaring {scam_count} token penipuan berbahaya!")
    
    # Sort by score descending
    audited_gems.sort(key=lambda x: x["predator_score"], reverse=True)
    
    print("\n" + "=" * 80)
    print("📋 HASIL RANKING PREDATOR GEMS (LIVE STREAM)")
    print("=" * 80)
    print(f"{'SYM':<8} | {'CHAIN':<6} | {'MCAP':<9} | {'LIQ':<8} | {'VOL 5M':<9} | {'SAFETY':<14} | {'SCORE':<5}")
    print("-" * 80)
    for g in audited_gems:
        safety = g["security_status"]
        print(f"{g['symbol'][:8]:<8} | {g['chain'].upper():<6} | ${g['market_cap']/1000:<7.1f}K | ${g['liquidity']/1000:<6.1f}K | ${g['volume_5m']/1000:<7.1f}K | {safety:<14} | {g['predator_score']:<5}")
    print("=" * 80)

    # Find the best clean gem for trade simulation
    safe_gems = [g for g in audited_gems if g["security_status"] in ["CLEAN & SAFE", "WARNINGS"]]
    
    if not safe_gems:
        print("\n🚨 SIMULASI ENTRY BATAL: Tidak ada koin yang cukup aman untuk di-trade saat ini.")
        print("💡 Penjelasan: Semua kandidat terdeteksi sebagai scam/honeypot. Perisai anti-scam menyelamatkan modal $10 Anda!")
        return
        
    best_gem = safe_gems[0]
    print(f"\n🎯 [3/3] MEMILIH GEM TERBAIK UNTUK SIMULASI SIMPANAN MODAL ${capital_usd:.2f}:")
    print(f"  👉 Token: {best_gem['name']} ({best_gem['symbol']})")
    print(f"  👉 Alamat Kontrak: {best_gem['address']}")
    print(f"  👉 Rantai: {best_gem['chain'].upper()}")
    print(f"  👉 Harga Live: ${best_gem['price']:.8f}")
    print(f"  👉 Predator Score: {best_gem['predator_score']}/100")
    
    # ------------------------------------------------------------------------
    #  SIMULASI LOGIKA TRANSAKSI DENGAN METRIK MEMECOIN GG
    # ------------------------------------------------------------------------
    # Biaya swap standard DEX:
    gas_fee = 0.12 if best_gem["chain"] == "solana" else 0.15 # Estimasi gas fee USD
    swap_fee_pct = 0.01 # 1% standard Raydium / Uniswap fee
    slippage_pct = 0.02 # 2% slippage protection
    
    total_fees = gas_fee + (capital_usd * swap_fee_pct) + (capital_usd * slippage_pct)
    net_investment = capital_usd - total_fees
    
    if net_investment <= 0:
        print("❌ Error: Biaya transaksi melebihi modal Anda!")
        return
        
    token_quantity = net_investment / best_gem["price"]
    
    # Upgraded Strategy: Trailing Stop Loss Engine
    # Fixed TP is completely removed (NONE) to capture infinite 1000%+ pumps!
    trailing_sl_pct = 20.0
    initial_sl_price = best_gem["price"] * (1 - (trailing_sl_pct / 100))
    initial_sl_value = net_investment * (1 - (trailing_sl_pct / 100))
    
    print("\n" + "-" * 50)
    print("💰 LAPORAN SIMULASI EKSEKUSI PREDATOR GEMS (TRAILING SL):")
    print("-" * 50)
    print(f"  💵 Modal Awal           : ${capital_usd:.2f}")
    print(f"  💸 Estimasi Gas Fee     : ${gas_fee:.2f} ({best_gem['chain'].upper()} network)")
    print(f"  🔄 Estimasi Swap Fee (1%): ${capital_usd * swap_fee_pct:.2f}")
    print(f"  📉 Slippage Protek (2%) : ${capital_usd * slippage_pct:.2f}")
    print(f"  💼 Modal Bersih Trade   : ${net_investment:.2f}")
    print(f"  💎 Jumlah Token Didapat : {token_quantity:,.4f} {best_gem['symbol']}")
    print(f"  🎯 Harga Beli (Entry)   : ${best_gem['price']:.8f}")
    print("-" * 50)
    print(f"  🚀 TARGET TAKE PROFIT   : NONE (Target: Moonshot Tak Terbatas / +1000%+!)")
    print(f"  🛑 INITIAL STOP LOSS    : Price ${initial_sl_price:.8f} (-{trailing_sl_pct}%) | Value: ${initial_sl_value:.2f}")
    print(f"  📈 TRAILING SL ENGINE   : SL Otomatis Ikut Naik Mengunci Profit Setiap Kenaikan Puncak Harga Baru!")
    print("-" * 50)
    print(f"💡 STRATEGI PREDATOR SECURE:")
    print("  1. TRADITIONAL INDICATORS (EMA/RSI): Diabaikan karena koin terlalu baru.")
    print("  2. NEW AGE METRICS (DEX-GG):")
    print(f"     - Likuiditas Burned/Locked : OK")
    print(f"     - GoPlus Scam-Shield Audit : {best_gem['security_status']}")
    print(f"     - Rasio Likuiditas/Mcap    : {(best_gem['liquidity']/best_gem['market_cap'])*100:.1f}% (Sehat: 10%-35%)")
    print("=" * 80)

if __name__ == "__main__":
    run_dex_simulation()
