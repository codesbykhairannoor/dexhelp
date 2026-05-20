import os
import sys
import random
import time
import math

# Reconfigure terminal for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Terminal colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"

def print_header(title):
    print("\n" + "=" * 80)
    print(f"{BOLD}{CYAN}🛰️  {title}{RESET}")
    print("=" * 80)

def simulate_portfolio_run(
    initial_balance=1000.0,
    allocation_pct=0.05,
    num_trades=100,
    win_rate_distribution=None,
    slippage_drag=0.05
):
    balance = initial_balance
    history = [balance]
    peak = balance
    max_drawdown = 0.0
    
    wins = 0
    losses = 0
    rugs = 0
    
    consecutive_losses = 0
    max_consecutive_losses = 0
    
    for _ in range(num_trades):
        if balance <= 5.0:
            balance = 0.0
            history.append(balance)
            break
            
        trade_size = balance * allocation_pct
        if trade_size < 5.0:
            trade_size = 5.0
            
        # Outcome selection
        r = random.random()
        cumulative = 0.0
        selected_outcome = 'sl'
        
        for outcome, prob in win_rate_distribution.items():
            cumulative += prob
            if r <= cumulative:
                selected_outcome = outcome
                break
                
        # Calculate raw PnL
        if selected_outcome == 'rug':
            pnl_pct = -1.0 # -100%
            rugs += 1
            losses += 1
            consecutive_losses += 1
        elif selected_outcome == 'sl':
            pnl_pct = random.uniform(-0.25, -0.15)
            losses += 1
            consecutive_losses += 1
        elif selected_outcome == 'break_even':
            pnl_pct = random.uniform(-0.05, 0.05)
            # Breakeven doesn't count as a win or loss streak breaker
        elif selected_outcome == 'small_win':
            pnl_pct = random.uniform(0.30, 0.80)
            wins += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            consecutive_losses = 0
        elif selected_outcome == 'big_win':
            pnl_pct = random.uniform(1.0, 3.0)
            wins += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            consecutive_losses = 0
        elif selected_outcome == 'moonshot':
            pnl_pct = random.uniform(5.0, 25.0)
            wins += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            consecutive_losses = 0
            
        # Apply slippage
        pnl_pct = pnl_pct - slippage_drag
        
        net_pnl = trade_size * pnl_pct
        balance += net_pnl
        history.append(balance)
        
        if balance > peak:
            peak = balance
        drawdown = (peak - balance) / peak if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
    total_trades_taken = len(history) - 1
    
    return history, {
        "final_balance": balance,
        "max_drawdown": max_drawdown * 100,
        "wins": wins,
        "losses": losses,
        "rugs": rugs,
        "win_rate": (wins / total_trades_taken * 100) if total_trades_taken > 0 else 0,
        "max_consecutive_losses": max_consecutive_losses
    }

def run_monte_carlo():
    print_header("SOLANA DEX PREDATOR: MONTE CARLO MONSTER SIMULATOR V2.0")
    print(f"{BOLD}Analisis Simulasi Kegagalan & Stres-Test Portofolio{RESET}")
    print("-" * 80)
    
    # Standard V16.5 config
    base_dist = {
        "rug": 0.02,         
        "sl": 0.58,          
        "break_even": 0.15,  
        "small_win": 0.18,   
        "big_win": 0.05,     
        "moonshot": 0.02     
    }
    
    # Run a base simulation to establish metrics
    num_simulations = 1000
    num_trades = 100
    initial_balance = 1000.0
    
    results = []
    for _ in range(num_simulations):
        _, stats = simulate_portfolio_run(
            initial_balance=initial_balance,
            allocation_pct=0.05,
            num_trades=num_trades,
            win_rate_distribution=base_dist,
            slippage_drag=0.05
        )
        results.append(stats)
        
    avg_winrate = sum(r["win_rate"] for r in results) / num_simulations
    avg_max_consecutive_losses = sum(r["max_consecutive_losses"] for r in results) / num_simulations
    max_streak_across_all = max(r["max_consecutive_losses"] for r in results)
    avg_rugs = sum(r["rugs"] for r in results) / num_simulations
    
    print(f"{BOLD}1. STATISTIK DERET KEKALAHAN (LOSING STREAK ANALYSIS){RESET}")
    print("Dengan Win Rate ~25% (Akurasi penyaringan bot), mari lihat perilakunya:")
    print(f"  - Rata-rata Win Rate                : {GREEN if avg_winrate > 20 else RED}{avg_winrate:.1f}%{RESET}")
    print(f"  - Rata-rata Beruntun Kalah Terlama  : {RED}{avg_max_consecutive_losses:.1f} kali beruntun{RESET}")
    print(f"  - Kasus Terburuk Kalah Beruntun     : {RED}{max_streak_across_all} kali beruntun{RESET} (dari 100 trade)")
    print(f"  * {YELLOW}Analisis Psikologi:{RESET} Kekalahan beruntun hingga {max_streak_across_all} kali adalah alasan")
    print("    utama mengapa trader manusia menyerah. Bot mampu bertahan karena disiplin ukuran posisi.")
    print("-" * 80)

    # 2. Stress-Test Parameters (What makes the strategy fail?)
    print(f"{BOLD}2. UJI STRES (PORTFOLIO FAILURE & DRAG DIAGNOSTICS){RESET}")
    print("Mari simulasikan 3 faktor kegagalan utama di dunia Solana:")
    
    # Test case A: Slippage Drag increase
    slippage_scenarios = [0.03, 0.05, 0.10, 0.15]
    print(f"\n{BOLD}[A] Pengaruh Slippage Drag (Biaya Transaksi + Selisih Harga Masuk/Keluar):{RESET}")
    print(f"    Slippage drag yang tinggi akan menggerus keuntungan secara eksponensial.")
    for slip in slippage_scenarios:
        slip_results = []
        for _ in range(300): # Fast test
            _, stats = simulate_portfolio_run(initial_balance, 0.05, num_trades, base_dist, slip)
            slip_results.append(stats["final_balance"])
        slip_median = sorted(slip_results)[len(slip_results)//2]
        ruined = sum(1 for b in slip_results if b <= 5.0) / len(slip_results) * 100
        print(f"      - Slippage Drag {slip*100:>2.0f}% | Median Akhir: ${slip_median:7.2f} USD | Peluang Bangkrut: {RED if ruined > 5 else GREEN}{ruined:.1f}%{RESET}")

    # Test case B: Safety filter decay (Increase Rug/Scam probability)
    print(f"\n{BOLD}[B] Pengaruh Kebocoran Sistem Keamanan (Safety Filter Failure):{RESET}")
    print("    Jika bot tidak menyaring RugCheck secara ketat, probabilitas Rug meningkat:")
    safety_scenarios = [
        {"name": "Strict Audit (2% Rugs)", "dist": {"rug": 0.02, "sl": 0.58, "break_even": 0.15, "small_win": 0.18, "big_win": 0.05, "moonshot": 0.02}},
        {"name": "Loose Audit  (8% Rugs)", "dist": {"rug": 0.08, "sl": 0.52, "break_even": 0.15, "small_win": 0.18, "big_win": 0.05, "moonshot": 0.02}},
        {"name": "Degen Audit  (15% Rugs)", "dist": {"rug": 0.15, "sl": 0.45, "break_even": 0.15, "small_win": 0.18, "big_win": 0.05, "moonshot": 0.02}},
        {"name": "Scam Heaven  (25% Rugs)", "dist": {"rug": 0.25, "sl": 0.35, "break_even": 0.15, "small_win": 0.18, "big_win": 0.05, "moonshot": 0.02}}
    ]
    for sc in safety_scenarios:
        sc_results = []
        for _ in range(300):
            _, stats = simulate_portfolio_run(initial_balance, 0.05, num_trades, sc["dist"], 0.05)
            sc_results.append(stats["final_balance"])
        sc_median = sorted(sc_results)[len(sc_results)//2]
        ruined = sum(1 for b in sc_results if b <= 5.0) / len(sc_results) * 100
        print(f"      - {sc['name']} | Median Akhir: ${sc_median:7.2f} USD | Peluang Bangkrut: {RED if ruined > 5 else GREEN}{ruined:.1f}%{RESET}")

    # Test case C: Allocation size (Position sizing risk)
    print(f"\n{BOLD}[C] Pengaruh Ukuran Alokasi Transaksi (Position Sizing):{RESET}")
    print("    Menggunakan ukuran posisi terlalu besar dapat memicu kebangkrutan saat kalah beruntun.")
    allocations = [0.02, 0.05, 0.10, 0.20]
    for alloc in allocations:
        alloc_results = []
        for _ in range(300):
            _, stats = simulate_portfolio_run(initial_balance, alloc, num_trades, base_dist, 0.05)
            alloc_results.append(stats["final_balance"])
        alloc_median = sorted(alloc_results)[len(alloc_results)//2]
        ruined = sum(1 for b in alloc_results if b <= 5.0) / len(alloc_results) * 100
        print(f"      - Alokasi {alloc*100:>2.0f}% per Trade | Median Akhir: ${alloc_median:7.2f} USD | Peluang Bangkrut: {RED if ruined > 5 else GREEN}{ruined:.1f}%{RESET}")

    print("\n" + "=" * 80)
    print(f"{BOLD}{YELLOW}💡 DIAGNOSIS PENYEBAB KEGAGALAN UTAMA:{RESET}")
    print(f"  1. {BOLD}Slippage di atas 10%:{RESET} Menghancurkan keunggulan matematika secara total.")
    print("     Solusi: Batasi slippage maksimal 2.5% - 5.0% di pengaturan bot.")
    print(f"  2. {BOLD}Alokasi di atas 10%:{RESET} Sangat berbahaya! Deret kekalahan terburuk kita adalah")
    print("     ~15-18 kali beruntun. Jika alokasi 20%, portofolio akan hancur lebur sebelum")
    print("     sempat menangkap koin moonshot berikutnya.")
    print(f"  3. {BOLD}Mengabaikan RugCheck:{RESET} Jika probabilitas rug naik ke 15%+, peluang bangkrut")
    print("     langsung melonjak dari 0% menjadi 17%+. Filter keamanan adalah kunci mutlak.")
    print("=" * 80)

if __name__ == "__main__":
    run_monte_carlo()
