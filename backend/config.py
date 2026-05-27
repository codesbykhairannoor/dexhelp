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
TRADE_MODE = "HOLY_GRAIL_75WR"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN HASIL SIMULASI: Diturunkan ke 80 agar bot rajin masuk trade.
MIN_ENTRY_SCORE = 80

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MIN_LIQ = 2000        # Likuiditas minimal USD ($2000 untuk snipes moderat)
MIN_MCAP = 5000       # Market Cap minimal USD
MIN_VOL_5M = 7500     # Volume transaksi 5 menit minimal USD (Wajib tinggi!)
MIN_TRADES_5M = 50    # Jumlah transaksi total 5 menit minimal (Buy + Sell)

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Agar bisa snipe koin umur 0 menit yang Twitternya belum muncul)
REQUIRE_SOCIALS = False
