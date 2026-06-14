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
MIN_ENTRY_SCORE = 82  # LOOSENED: After multiple cycles of zero win rate despite high score, we now prioritize execution speed over raw score. Allow lower-score but faster-flowing trades.

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 1.1  # SLIGHTLY LOOSENED: From 1.0 to 1.1 minutes — previous entries too early or missed due to latency; 1.1min targets sweet spot between pump initiation and pre-distribution
MIN_LIQ = 70000        # RAISED: From $65k to $70k to further harden against slippage; eliminate mid-tier pools that degrade during exits
MAX_LIQ = 350000       # Slightly lowered to avoid mature coins with diminishing volatility
MIN_MCAP = 2500        # Unchanged — sufficient for filtering micro-noise
MIN_VOL_5M = 90000     # RAISED: From $85k to $90k to demand extreme volume momentum, ensuring follow-through buying pressure
MIN_TRADES_5M = 28     # Increased to 28 to confirm strong crowd engagement, filtering low-participation pumps

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
