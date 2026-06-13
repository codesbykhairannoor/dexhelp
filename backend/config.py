# ============================================================================
# DEX PREDATOR - STRATEGY & FILTER CONFIGURATION
# ============================================================================
# Gunakan file ini untuk mengatur kelonggaran filter dan mode trading.
# Jangan letakkan API Keys di sini (biarkan di .env).

# --- PRODUCTION TRADING MODES ---
# Pilihan: 
#   HIT_AND_RUN     (Konsisten Cuan Harian: Langsung TP 100% di +20%, tidak rakus)
#   RUNNER          (Murni Sniper: TP 50% di +30%, sisa dibiarkan Moonshot)
#   OPTIMIZED       (WR 57% PnL +18%)
#   MOONSHOT        (WR 50% PnL +26%)
#   SCALPER         (WR 75% PnL +4.7%)
#   HOLY_GRAIL_75WR (WR 75-80% PnL +15%) -> Mode agresif TP awal 50%
TRADE_MODE = "HIT_AND_RUN"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 92  # CRITICAL: 85 still produced 0% WR. Only highest conviction signals (90+) have shown profitability in backtests

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 0.75  # CRITICAL FIX: 1.5min still catches post-pump dumps. Need sub-1min for TRUE fresh entries before first wave
MIN_LIQ = 35000       # CRITICAL FIX: $20k FAILED - DICKFACE still -34% vs 10% SL. Need $35k+ for reliable exit execution without catastrophic slippage
MAX_LIQ = 450000      # Slightly tighter: Hindari koin yang mulai melambat karena ukuran
MIN_MCAP = 1800       # Turun sedikit untuk cap bottoming new launches
MIN_VOL_5M = 55000    # TIGHTER: $35k still allowed dump candidates. $55k ensures sustained momentum and reduces rug risk
MIN_TRADES_5M = 20    # Turun ke 20: Validasi partisipasi user tetap ada tanpa batasi terlalu ketat

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
