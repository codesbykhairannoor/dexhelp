import ast, sys

filepath = 'cryptoscreenerai-main/backend/crypto_engine.py'

# Read the file
with open(filepath, encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines(keepends=True)
print(f"Original line count: {len(lines)}")

# Find the line index of "def run_crypto_engine():"
target_line = None
for i, line in enumerate(lines):
    if line.strip().startswith('def run_crypto_engine():'):
        target_line = i
        break

if target_line is None:
    print("ERROR: Could not find 'def run_crypto_engine():'")
    sys.exit(1)

print(f"Found def run_crypto_engine() at line {target_line + 1} (1-indexed)")

# Keep everything up to (but not including) that line
preserved = lines[:target_line]

new_func = '''def run_crypto_engine():
    """
    CRYPTO SCALPER v5.1 - Direct Execution Mode
    =============================================
    Restored to profitable May 5 logic:
    - Scan top 20 coins every 10 seconds
    - If coin passes filters -> execute immediately (no 15-min observation)
    - Session filter: 08:00-22:00 WIB only (hard stop off-hours)
    - Cooldown: 120 seconds between trades
    """
    executor = BitgetExecutor()

    from database import check_pending_trades, get_performance_stats
    from sentiment import get_market_news_digest

    print("[CRYPTO SCALPER v5.1] Direct Execution Mode AKTIF!", flush=True)
    print(f"  Strategy : 1 trade terbaik | {LEVERAGE}x leverage", flush=True)
    print(f"  Cooldown : {COOLDOWN_AFTER_TRADE}s antara trade", flush=True)
    print(f"  Session  : 08:00-22:00 WIB (01:00-15:00 UTC)", flush=True)

    try:
        print("[SYSTEM] Sinkronisasi awal dengan Bitget...", flush=True)
        executor.sync_state_with_exchange()
        print("[SYSTEM] Sinkronisasi Bitget SUKSES.", flush=True)
    except Exception as e:
        print(f"[SYSTEM WARNING] Gagal sinkronisasi awal: {e}", flush=True)

    last_exec_time      = 0
    last_news_report    = 0
    last_global_report  = 0
    last_deepseek_report = 0
    _dxy_cache          = {"trend": "NEUTRAL", "ts": 0}
    _recently_exited    = {}
    _loss_tracker       = {}
    _consec_losses      = 0
    _consec_pause_until = 0

    while True:
        try:
            now = time.time()
            if int(now) % 60 < 10:
                print("[CRYPTO ENGINE] Heartbeat: Loop is running...", flush=True)

            #  1. MANAGE EXISTING POSITIONS
            executor.manage_open_positions()
            check_pending_trades()

            #  2. NEWS VELOCITY (setiap 10 menit)
            if now - last_news_report > NEWS_REPORT_INTERVAL:
                digest = get_market_news_digest()
                print(f"[NEWS VELOCITY] Sentiment: {digest[\'sentiment\']} | Top: {digest[\'crypto_top\']}", flush=True)
                last_news_report = now

            #  3. GLOBAL CONTEXT (setiap 5 menit)
            if now - last_global_report > GLOBAL_REPORT_INTERVAL:
                global_ctx = get_global_market_data()
                print(f"[GLOBAL] {global_ctx}")
                last_global_report = now

            #  4. CIRCUIT BREAKER
            stats     = get_performance_stats(\'crypto\')
            daily_pnl = stats.get(\'daily_pnl\', 0)
            if daily_pnl < DAILY_LOSS_LIMIT_PCT:
                print(f"[CIRCUIT BREAKER] Daily loss {daily_pnl}% melewati limit. Standby 30 menit.")
                time.sleep(1800)
                continue

            #  4b. CONSECUTIVE LOSS PAUSE
            if now < _consec_pause_until:
                remaining = round((_consec_pause_until - now) / 60, 1)
                if int(now) % 60 < 10:
                    print(f"[CONSEC LOSS] Pause aktif. {remaining} menit lagi.")
                time.sleep(SCAN_INTERVAL)
                continue

            #  4c. SESSION FILTER — HARD STOP off-hours
            # DATA: 13 trade jam 01:00-08:00 WIB = 9 loss 3 win (commit e97e2ab)
            import datetime as _dt
            utc_hour = _dt.datetime.utcnow().hour
            if not (CRYPTO_SESSION_START_UTC <= utc_hour < CRYPTO_SESSION_END_UTC):
                if int(now) % 300 < 10:
                    wib_hour = (utc_hour + 7) % 24
                    print(f"[CRYPTO SESSION] Off-hours ({wib_hour:02d}:xx WIB). Aktif jam 08:00-22:00 WIB.")
                time.sleep(60)
                continue

            #  5. POSITION CHECK
            positions  = executor.get_all_positions()
            open_count = len(positions) if isinstance(positions, list) else 0
            open_bases = [executor._clean_symbol(p[\'symbol\']) for p in positions] \\
                         if isinstance(positions, list) else []

            if open_count >= MAX_POSITIONS:
                print(f"[LIMIT] {open_count}/{MAX_POSITIONS} posisi aktif. Manage existing.")
                time.sleep(SCAN_INTERVAL)
                continue

            #  6. COOLDOWN CHECK
            elapsed_since_trade = now - last_exec_time
            cooldown_remaining  = COOLDOWN_AFTER_TRADE - elapsed_since_trade
            if cooldown_remaining > 0:
                if int(now) % 30 < 10:
                    print(f"[COOLDOWN] {round(cooldown_remaining)}s remaining")
                time.sleep(SCAN_INTERVAL)
                continue

            #  7. BERSIHKAN recently_exited + TRACK LOSSES
            _recently_exited = {k: v for k, v in _recently_exited.items() if now - v < 1800}
            try:
                from shared_state import state as _state
                if hasattr(_state, \'recently_exited\'):
                    for k, v in list(_state.recently_exited.items()):
                        if now - v < 1800:
                            if k not in _recently_exited:
                                last_pnl = getattr(_state, \'exit_pnl\', {}).get(k, -1.0)
                                if last_pnl < 0:
                                    if k not in _loss_tracker:
                                        _loss_tracker[k] = []
                                    _loss_tracker[k].append(v)
                                    _consec_losses += 1
                                    print(f"[CONSEC LOSS] Loss ke-{_consec_losses} ({k}) | PnL: {last_pnl}%")
                                    if _consec_losses >= CONSEC_LOSS_LIMIT:
                                        pause_minutes = CONSEC_LOSS_PAUSE_MIN * (2 ** (_consec_losses - CONSEC_LOSS_LIMIT))
                                        pause_minutes = min(pause_minutes, 240)
                                        _consec_pause_until = now + (pause_minutes * 60)
                                        print(f"[CONSEC LOSS] {_consec_losses}x loss! Pause {pause_minutes} menit.")
                                        _consec_losses = CONSEC_LOSS_LIMIT
                                else:
                                    print(f"[WIN TRACKER] {k} take profit ({last_pnl}%)! Reset consec loss.")
                                    _consec_losses = 0
                            _recently_exited[k] = v
                        else:
                            del _state.recently_exited[k]
            except Exception:
                pass

            #  8. MARKET SENTIMENT & DXY
            digest           = get_market_news_digest()
            market_sentiment = digest.get(\'sentiment\', \'NEUTRAL\')

            if now - _dxy_cache["ts"] > 300:
                try:
                    from data_fetcher import get_forex_data
                    dxy = get_forex_data("DXY")
                    _dxy_cache["trend"]  = dxy.get(\'trend\', \'NEUTRAL\') if dxy else \'NEUTRAL\'
                    _dxy_cache["change"] = dxy.get(\'change\', 0) if dxy else 0
                    _dxy_cache["ts"]     = now
                except Exception:
                    pass
            dxy_trend  = _dxy_cache.get("trend", "NEUTRAL")
            dxy_change = _dxy_cache.get("change", 0)

            #  9. SCAN & LANGSUNG EKSEKUSI (tidak ada WhaleObserver)
            raw_data   = fetch_all_tickers()
            candidates = analyze_and_sort(raw_data)

            if not candidates:
                if int(now) % 60 < 10:
                    print("[CRYPTO WARNING] Tidak ada kandidat. Retrying...")
                time.sleep(SCAN_INTERVAL)
                continue

            # Bersihkan loss tracker
            cutoff = now - (REPEAT_LOSS_BLACKLIST_HOURS * 3600)
            for base in list(_loss_tracker.keys()):
                _loss_tracker[base] = [t for t in _loss_tracker[base] if t > cutoff]
                if not _loss_tracker[base]:
                    del _loss_tracker[base]
            _repeat_losers = {b for b, ts in _loss_tracker.items() if len(ts) >= REPEAT_LOSS_MAX_COUNT}

            btc_ctx = _get_btc_context()
            print(f"[CRYPTO ENGINE] Scan {min(20, len(candidates))} koin | "
                  f"Sentiment: {market_sentiment} | DXY: {dxy_trend} | "
                  f"BTC: {btc_ctx[\'trend\']} ({btc_ctx[\'change_1h\']:+.1f}%/1h)", flush=True)

            traded_this_cycle = False
            for coin in candidates[:20]:
                if traded_this_cycle:
                    break

                symbol     = coin.get(\'symbol\', \'\')
                clean_base = executor._clean_symbol(symbol)

                # Filter dasar
                if clean_base in open_bases:                                          continue
                if clean_base in (\'BTC\', \'ETH\'):                                      continue
                if any(x in clean_base for x in (\'USD\',\'DAI\',\'BUSD\',\'TUSD\',\'WBTC\',\'WETH\')): continue
                if clean_base in _recently_exited:                                    continue
                if clean_base in _repeat_losers:                                      continue

                pump_sc = float(coin.get(\'pump_score\', 0))
                dump_sc = float(coin.get(\'dump_score\', 0))
                best_sc = max(pump_sc, dump_sc)
                if best_sc < MIN_PUMP_SCORE:
                    continue

                # Ambil indikator teknikal
                tech = get_technical_indicators(symbol)
                if not tech:
                    continue

                mark_price = tech.get(\'mark_price\', 0) or float(coin.get(\'lastPrice\', 0))
                if mark_price == 0:
                    continue

                rsi       = tech.get(\'rsi\', _calc_rsi(symbol))
                vwap_dist = _calc_vwap_dist(mark_price, symbol)

                side, reason, tech_score = _determine_trade_side(tech, rsi, vwap_dist, market_sentiment)

                combined_score = round((pump_sc * 0.5) + (tech_score * 0.5))

                print(f"[EVAL] {clean_base} | Pump:{pump_sc:.0f} Tech:{tech_score} "
                      f"Combined:{combined_score} | RSI:{rsi} VWAP:{vwap_dist}% | "
                      f"1h:{tech.get(\'trend_1h\',\'?\')} 4h:{tech.get(\'trend_4h\',\'?\')}")

                if side is None or combined_score < MIN_MOMENTUM_SCORE or tech_score < MIN_TECH_SCORE:
                    continue

                # DXY override
                if abs(dxy_change) > 0.0001 and side == "buy" and dxy_trend == "BULLISH" and dxy_change > 0.2:
                    print(f"[DXY OVERRIDE] Dollar terlalu kuat, skip {clean_base} Long.")
                    continue

                # BTC correlation filter
                btc_signal = btc_ctx.get("signal", "NEUTRAL")
                if btc_signal == "AVOID_LONG" and side == "buy":
                    continue
                if btc_signal == "AVOID_SHORT" and side == "sell":
                    continue

                # Order book confirmation
                from data_fetcher import get_order_book_details
                ob_data  = get_order_book_details(symbol)
                ob_ratio = ob_data.get(\'ratio\', 0)
                if side == "buy"  and ob_ratio < -0.1: continue
                if side == "sell" and ob_ratio > 0.1:  continue

                # Hitung TP/SL
                tp, sl = _calc_tp_sl(mark_price, side, tech)

                # Hitung size
                amount = executor.get_max_available(symbol, leverage=LEVERAGE)
                if amount <= 0:
                    print(f"[MARGIN GUARD] Insufficient margin for {clean_base}.")
                    continue

                # EKSEKUSI LANGSUNG
                print(f"\\n{\'=\'*60}")
                print(f"[SCALPER v5.1] {clean_base} {side.upper()} | Score: {combined_score}/100")
                print(f"  Reason : {reason}")
                print(f"  Price  : {mark_price} | RSI: {rsi} | VWAP: {vwap_dist}%")
                print(f"  TP: {tp} | SL: {sl} | Amount: {amount}")
                print(f"  1h: {tech.get(\'trend_1h\',\'?\')} | 4h: {tech.get(\'trend_4h\',\'?\')}")
                print(f"{\'=\'*60}\\n")

                print(f"[EXECUTOR] Mengirim order {side.upper()} {symbol} ke Bitget...", flush=True)
                success, order = executor.place_order(symbol, side, amount, tp=tp, sl=sl, leverage=LEVERAGE)

                if success:
                    from database import log_trade
                    log_trade(symbol, mark_price, tp, sl,
                              side=side, score=combined_score, reason=reason)
                    last_exec_time = time.time()
                    traded_this_cycle = True
                    _consec_losses = 0
                    print(f"[TRADE LOGGED] {clean_base} {side.upper()} @ {mark_price} | Score: {combined_score}")
                else:
                    print(f"[ORDER FAILED] {clean_base}: {order}")

            time.sleep(SCAN_INTERVAL)

        except Exception as e:
            print(f"[ENGINE ERROR] {e}")
            time.sleep(30)
'''

new_lines = new_func.splitlines(keepends=True)
# Ensure last line ends with newline
if new_lines and not new_lines[-1].endswith('\n'):
    new_lines[-1] += '\n'

final_lines = preserved + new_lines
final_content = ''.join(final_lines)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"New line count: {len(final_lines)}")
print("File written successfully.")

# Verify with ast.parse
try:
    with open(filepath, encoding='utf-8') as f:
        source = f.read()
    ast.parse(source)
    print("AST PARSE: OK - file is syntactically valid Python.")
except SyntaxError as e:
    print(f"AST PARSE ERROR: {e}")
    sys.exit(1)
