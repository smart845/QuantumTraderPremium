
import io
import mplfinance as mpf

def _candles_df(df):
    c = df[['timestamp','open','high','low','close','volume']].copy()
    c = c.set_index('timestamp')
    return c

def plot_technical_chart(df, symbol, entry=None, sl=None, tp=None):
    """
    TradingView-style: candlesticks + Supertrend overlay + RSI + MACD.
    Optionally marks Entry/SL/TP.
    """
    buf = io.BytesIO()
    candles = _candles_df(df)

    addplots = []
    if 'supertrend' in df.columns:
        addplots.append(mpf.make_addplot(df['supertrend'].values, panel=0, color='cyan', width=1.0))

    if 'rsi' in df.columns:
        addplots.append(mpf.make_addplot(df['rsi'].values, panel=1, ylabel='RSI', width=1.0))
    if all(k in df.columns for k in ['macd','macd_signal','macd_histogram']):
        addplots.append(mpf.make_addplot(df['macd'].values, panel=2, color='lime', width=1.0))
        addplots.append(mpf.make_addplot(df['macd_signal'].values, panel=2, color='magenta', width=1.0))
        addplots.append(mpf.make_addplot(df['macd_histogram'].values, type='bar', panel=2, alpha=0.4))

    # Price markers
    hlines = []
    hcolors = []
    if entry is not None:
        hlines.append(entry); hcolors.append('dodgerblue')
    if sl is not None:
        hlines.append(sl); hcolors.append('red')
    if tp is not None:
        hlines.append(tp); hcolors.append('lime')

    mpf.plot(
        candles,
        type='candle',
        style='nightclouds',
        addplot=addplots,
        hlines=dict(hlines=hlines, colors=hcolors, linewidths=1.0, alpha=0.8) if hlines else None,
        volume=True,
        title=f'{symbol} — Quantum AI Chart',
        ylabel='Price',
        ylabel_lower='Volume',
        panel_ratios=(6,2,2),
        figratio=(12,8),
        savefig=dict(fname=buf, dpi=120, bbox_inches='tight')
    )
    buf.seek(0)
    return buf
