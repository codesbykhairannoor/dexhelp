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
TRADE_MODE = "HIT_AND_RUN"  # Switch to HIT_AND_RUN: Enforce discipline with 20% TP to avoid overstay in manipulated pumps post-consolidation; adapt to reduced volatility window

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 79  # Further loosen: Increase signal count without sacrificing quality; capture early organic flow missed by overfiltered prior cycle

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 6.0  # MAJOR LOOSEN: Per DEGEN WISDOM — buying at <2min with high volume leads to honeypots. Wait 5+ mins for dust to settle, volume to stabilize organically
MIN_LIQ = 75000        # Lowered: Allow earlier participation in genuine low-liquidity pumps that grow organically
MAX_LIQ = 320000       # Raised: Permit slightly larger plays post-consolidation, targeting momentum continuation
MIN_MCAP = 3000        # Slight loosen: Maintain sensitivity to early caps with real traction
MIN_VOL_5M = 48000     # Loosen further: Target coins with authentic but slower volume ramp-up, avoiding honeypot traps from inflated walls
MIN_TRADES_5M = 20     # Loosen: Accept lower trade count threshold to increase entry opportunities in surviving organic pumps

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
