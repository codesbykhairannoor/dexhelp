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
TRADE_MODE = "SCALPER"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 75  # DITURUNKAN: Filter terlalu ketat, perlu entry untuk dapat data

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 5  # DILONGGARKAN: 2 menit terlalu sempit, beri waktu 5 menit untuk entry
MIN_LIQ = 2000        # Likuiditas minimal USD (Anti-Slippage)
MAX_LIQ = 500000      # Likuiditas maksimal USD (Anti-Koin Raksasa/Lamban)
MIN_MCAP = 2000       # Market Cap minimal USD
MIN_VOL_5M = 8000      # DITURUNKAN: $25k terlalu tinggi, $8k cukup untuk validasi aktivitas
MIN_TRADES_5M = 25    # DITURUNKAN: 60 trades terlalu ketat, 25 cukup untuk validasi

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
