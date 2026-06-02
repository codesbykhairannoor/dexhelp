# ============================================================================
# DEX PREDATOR - STRATEGY & FILTER CONFIGURATION
# ============================================================================
# Gunakan file ini untuk mengatur kelonggaran filter dan mode trading.
# Jangan letakkan API Keys di sini (biarkan di .env).

# --- PRODUCTION TRADING MODES ---
# Pilihan: 
#   OPTIMIZED       (WR 57% PnL +18%)
#   MOONSHOT        (WR 50% PnL +26%)
#   SCALPER         (WR 75% PnL +4.7%)
#   HOLY_GRAIL_75WR (WR 75-80% PnL +15%) -> Mode agresif TP awal 50%
TRADE_MODE = "OPTIMIZED"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN HASIL SIMULASI: Dinaikkan ke 95 (Sniper Mode) untuk menyaring koin sampah/rugpull.
MIN_ENTRY_SCORE = 95

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MIN_LIQ = 10000       # Likuiditas minimal USD (Dinaikkan agar tidak kena slippage parah)
MIN_MCAP = 5000       # Market Cap minimal USD
MIN_VOL_5M = 25000    # Volume transaksi 5 menit minimal USD (Wajib sangat tinggi!)
MIN_TRADES_5M = 50    # Jumlah transaksi total 5 menit minimal (Buy + Sell)

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: TRUE (90% koin tanpa sosial adalah Rugpull developer malas)
REQUIRE_SOCIALS = True
