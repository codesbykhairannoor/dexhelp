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
TRADE_MODE = "HIT_AND_RUN"  # Cycle 18: Aggressive adaptation to pre-consolidation momentum capture with ultra-fast time bomb and tighter SL to exploit micro-windows before sniper dumps

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 82  # Raised to focus on higher-signal entries post-DeepSeek AI filtering

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 2.5  # NEW: Target the sweet spot — after initial wash-trade dump (0-90s) but before consolidation traps form (post-4min)
MIN_LIQ = 8000         # Lowered to detect organic low-liquidity pumps earlier, trusting DeepSeek 'Vibe Check' to filter scams
MAX_LIQ = 200000       # Slightly reduced to avoid bloated launch pools
MIN_MCAP = 5000        # Slight raise to avoid lowest-cap noise
MIN_VOL_5M = 8000      # Reduced significantly — trust DeepSeek semantic analysis over volume heuristics to avoid honeypots
MIN_TRADES_5M = 20     # Loosened to allow faster entry on emerging consensus

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
