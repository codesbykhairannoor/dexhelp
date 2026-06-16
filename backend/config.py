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
TRADE_MODE = "HIT_AND_RUN"  # Cycle 17: Wider SL (15%) absorbs memecoin volatility; higher TP (25%) captures stronger momentum; tighter entry filters reduce trap exposure

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 75  # RESET: Turunkan agar bot bisa menemukan trade

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 4.0  # RESET: Berikan waktu lebih panjang agar koin organik bisa bernafas
MIN_LIQ = 10000        # RESET: Kembalikan ke angka normal untuk memancing koin baru
MAX_LIQ = 250000       # Slightly raised to allow slightly larger but still early-stage launches
MIN_MCAP = 4000        # RAISED: Further filter out noise and dust caps with fake momentum
MIN_VOL_5M = 15000     # RESET: Volume yang sangat realistis untuk koin berusia 4 menit
MIN_TRADES_5M = 30     # Reset ke standar normal

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
