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
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 85  # RAISED: To enforce elite signal integrity after repeated failure of lower-score entries which were hunted by anti-sniper mechanics

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 0.7  # TIGHTENED: To enter before public snipers detect — targeting 42s mark to be first real buyer post-dev
MIN_LIQ = 90000        # RAISED: Ensures deep enough liquidity to survive initial dump and attract momentum buyers
MAX_LIQ = 220000       # Slightly tightened to avoid overly mature launches
MIN_MCAP = 3000        # RAISED: Filters out extremely low-cap traps that lack organic momentum
MIN_VOL_5M = 110000    # RAISED: Confirms strong buy pressure within first minute
MIN_TRADES_5M = 40     # RAISED: Validates crowd consensus — high trader count reduces single-wallet manipulation risk

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
