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
MIN_ENTRY_SCORE = 85  # ADJUSTED: 92 too restrictive, only 2 trades. 85 allows more opportunities while maintaining quality

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 1.5  # ADJUSTED: 0.75min too tight, missing viable entries. 1.5min balances freshness with opportunity
MIN_LIQ = 50000       # CRITICAL FIX: $35k FAILED - DICKFACE -34% loss proves insufficient. $50k+ needed for clean SL execution
MAX_LIQ = 450000      # Slightly tighter: Hindari koin yang mulai melambat karena ukuran
MIN_MCAP = 1800       # Turun sedikit untuk cap bottoming new launches
MIN_VOL_5M = 75000    # TIGHTER: $55k still allowed weak momentum. $75k ensures strong sustained volume for reliable exits
MIN_TRADES_5M = 20    # Turun ke 20: Validasi partisipasi user tetap ada tanpa batasi terlalu ketat

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
