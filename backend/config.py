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
MIN_ENTRY_SCORE = 87  # INCREASED: After repeated 0% WR despite elite execution, we raise bar for signal purity — only strongest predator signals allowed

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 0.8  # NEW RECORD: Enter at 48 seconds or earlier — ultra-early assault window to beat retail flood and anti-sniper traps
MIN_LIQ = 80000        # RAISED: Further increase to ensure dominance over exit flow and crush slippage
MAX_LIQ = 275000       # Slightly lowered to avoid large-cap memecoins with muted volatility
MIN_MCAP = 2500        # Unchanged — still effective at noise filtration
MIN_VOL_5M = 100000    # RAISED: Only accept nuclear-level volume confirmation — filtering out fake momentum
MIN_TRADES_5M = 35     # NEW HIGH: Extreme crowd consensus required — no more whale solo pumps

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
