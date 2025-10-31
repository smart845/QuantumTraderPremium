
import numpy as np
import pandas as pd
import ta
import ccxt
import asyncio
import websockets
import json

class QuantumTradingAI:
    def __init__(self):
        # Binance only per user choice
        self.exchanges = {
            'binance': ccxt.binance()
        }
        self.indicators = {}
        self.signals = {}
        self.models = {}
        self.orderflow_data = {}

    async def fetch_multiple_timeframes(self, symbol, timeframes):
        """Fetch OHLCV for multiple timeframes from Binance"""
        data = {}
        # ccxt expects 'BTC/USDT' while WebSocket uses 'BTCUSDT'
        ccxt_symbol = symbol.replace("USDT", "/USDT")
        for tf in timeframes:
            try:
                ohlcv = self.exchanges['binance'].fetch_ohlcv(ccxt_symbol, tf, limit=500)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                data[tf] = df
            except Exception as e:
                print(f"Error fetching {tf} data: {e}")
        return data

    async def process_orderbook(self, orderbook):
        try:
            bids = np.array([[float(bid[0]), float(bid[1])] for bid in orderbook.get('bids', [])[:20]])
            asks = np.array([[float(ask[0]), float(ask[1])] for ask in orderbook.get('asks', [])[:20]])
            if len(bids) > 0 and len(asks) > 0:
                bid_volume = bids[:, 1].sum()
                ask_volume = asks[:, 1].sum()
                total_volume = bid_volume + ask_volume
                imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
                self.orderflow_data = {
                    'imbalance': imbalance,
                    'spread': asks[0][0] - bids[0][0],
                    'mid_price': (bids[0][0] + asks[0][0]) / 2,
                    'timestamp': pd.Timestamp.now()
                }
        except Exception as e:
            print(f"Orderbook processing error: {e}")

    def calculate_supertrend(self, df, period=10, multiplier=3):
        try:
            hl2 = (df['high'] + df['low']) / 2
            atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
            upper_band = hl2 + (multiplier * atr)
            lower_band = hl2 - (multiplier * atr)
            supertrend = [lower_band.iloc[0]]
            for i in range(1, len(df)):
                if df['close'].iloc[i-1] > supertrend[i-1]:
                    current = max(lower_band.iloc[i], supertrend[i-1])
                else:
                    current = min(upper_band.iloc[i], supertrend[i-1])
                supertrend.append(current)
            return pd.Series(supertrend, index=df.index)
        except:
            return pd.Series([0] * len(df), index=df.index)

    def calculate_hull_ma(self, close, period=14):
        try:
            wma_half = close.rolling(period//2).mean()
            wma_full = close.rolling(period).mean()
            hull_ma = 2 * wma_half - wma_full
            return hull_ma.rolling(int(np.sqrt(period))).mean()
        except:
            return close.rolling(period).mean()

    def calculate_squeeze_momentum(self, df):
        try:
            bb_length, bb_std = 20, 2
            kc_length, kc_mult = 20, 1.5
            basis = df['close'].rolling(bb_length).mean()
            dev = bb_std * df['close'].rolling(bb_length).std()
            upperBB = basis + dev
            lowerBB = basis - dev

            ma = df['close'].rolling(kc_length).mean()
            range_ma = (df['high'] - df['low']).rolling(kc_length).mean()
            upperKC = ma + range_ma * kc_mult
            lowerKC = ma - range_ma * kc_mult

            squeeze_on = (lowerBB > lowerKC) & (upperBB < upperKC)
            squeeze_off = (lowerBB < lowerKC) & (upperBB > upperKC)
            momentum = ta.momentum.ROCIndicator(df['close'], window=1).roc()
            result = squeeze_on.astype(int) - squeeze_off.astype(int) + momentum / 100
            return result.fillna(0)
        except:
            return pd.Series([0] * len(df), index=df.index)

    def calculate_volume_profile(self, df, bins=20):
        try:
            price_range = df['high'].max() - df['low'].min()
            if price_range == 0: return pd.Series([0]*len(df), index=df.index)
            bin_size = price_range / bins
            volume_profile = []
            for i in range(len(df)):
                price = df['close'].iloc[i]
                bin_index = min(int((price - df['low'].min()) / bin_size), bins-1)
                volume_profile.append(bin_index / bins)
            return pd.Series(volume_profile, index=df.index)
        except:
            return pd.Series([0] * len(df), index=df.index)

    def calculate_all_indicators(self, df):
        try:
            h, l, c, v = df['high'], df['low'], df['close'], df['volume']
            df['ema_9'] = ta.trend.EMAIndicator(c, window=9).ema_indicator()
            df['ema_21'] = ta.trend.EMAIndicator(c, window=21).ema_indicator()
            df['ema_50'] = ta.trend.EMAIndicator(c, window=50).ema_indicator()
            df['ema_200'] = ta.trend.EMAIndicator(c, window=200).ema_indicator()
            macd = ta.trend.MACD(c)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            df['adx'] = ta.trend.ADXIndicator(h, l, c).adx()
            ichimoku = ta.trend.IchimokuIndicator(h, l)
            df['ichimoku_a'] = ichimoku.ichimoku_a()
            df['ichimoku_b'] = ichimoku.ichimoku_b()
            df['rsi'] = ta.momentum.RSIIndicator(c).rsi()
            stoch = ta.momentum.StochasticOscillator(h, l, c)
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            df['williams_r'] = ta.momentum.WilliamsRIndicator(h, l, c).williams_r()
            df['cci'] = ta.trend.CCIIndicator(h, l, c).cci()

            boll = ta.volatility.BollingerBands(c)
            df['bb_upper'] = boll.bollinger_hband()
            df['bb_lower'] = boll.bollinger_lband()
            df['bb_middle'] = boll.bollinger_mavg()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            # Position of close within BB channel (0..1)
            bb_range = (df['bb_upper'] - df['bb_lower'])
            df['bb_position'] = (c - df['bb_lower']) / bb_range.replace(0, np.nan)
            df['bb_position'] = df['bb_position'].clip(0, 1).fillna(0.5)

            df['atr'] = ta.volatility.AverageTrueRange(h, l, c).average_true_range()
            df['atr_percent'] = df['atr'] / c

            df['volume_sma_20'] = v.rolling(20).mean()
            df['volume_ratio'] = v / df['volume_sma_20']
            df['obv'] = ta.volume.OnBalanceVolumeIndicator(c, v).on_balance_volume()
            df['cmf'] = ta.volume.ChaikinMoneyFlowIndicator(h, l, c, v).chaikin_money_flow()

            df['supertrend'] = self.calculate_supertrend(df)
            df['hull_ma'] = self.calculate_hull_ma(c)
            df['squeeze'] = self.calculate_squeeze_momentum(df)
            df['volume_profile'] = self.calculate_volume_profile(df)
            df['higher_high'] = h > h.shift(1)
            df['lower_low'] = l < l.shift(1)
            return df
        except Exception as e:
            print(f"Indicator calculation error: {e}")
            return df

    # ---------------- Signals ----------------
    def get_ema_trend_signal(self, df):
        try:
            ema9, ema21, ema50 = df['ema_9'].iloc[-1], df['ema_21'].iloc[-1], df['ema_50'].iloc[-1]
            price = df['close'].iloc[-1]
            bull = bear = 0
            if price > ema9 > ema21 > ema50: bull += 3
            elif price < ema9 < ema21 < ema50: bear += 3
            if df['ema_9'].iloc[-1] > df['ema_9'].iloc[-2]: bull += 1
            else: bear += 1
            return 1 if bull > bear else -1 if bear > bull else 0
        except: return 0

    def get_macd_signal(self, df):
        try:
            macd, signal, hist = df['macd'].iloc[-1], df['macd_signal'].iloc[-1], df['macd_histogram'].iloc[-1]
            if macd > signal and hist > 0: return 1
            elif macd < signal and hist < 0: return -1
            return 0
        except: return 0

    def get_rsi_signal(self, df):
        try:
            rsi = df['rsi'].iloc[-1]
            if rsi < 30: return 1
            elif rsi > 70: return -1
            return 0
        except: return 0

    def get_stochastic_signal(self, df):
        try:
            k, d = df['stoch_k'].iloc[-1], df['stoch_d'].iloc[-1]
            if k < 20 and d < 20 and k > d: return 1
            elif k > 80 and d > 80 and k < d: return -1
            return 0
        except: return 0

    def get_bollinger_squeeze(self, df):
        try:
            bb_width = df['bb_width'].iloc[-1]
            if bb_width < 0.1: return 0.5
            elif bb_width > 0.3: return -0.5
            return 0
        except: return 0

    def get_volume_signal(self, df):
        try:
            vr = df['volume_ratio'].iloc[-1]
            if vr > 2.0:
                return 1 if df['close'].iloc[-1] > df['close'].iloc[-2] else -1
            return 0
        except: return 0

    def get_supertrend_signal(self, df):
        try:
            close, st = df['close'].iloc[-1], df['supertrend'].iloc[-1]
            if close > st: return 1
            elif close < st: return -1
            return 0
        except: return 0

    def get_squeeze_signal(self, df):
        try:
            s = df['squeeze'].iloc[-1]
            if s > 0.5: return 1
            elif s < -0.5: return -1
            return 0
        except: return 0

    def get_adx_trend_signal(self, df):
        try:
            adx = df['adx'].iloc[-1]
            return 1 if adx > 25 else 0
        except: return 0

    def get_orderflow_signal(self, orderflow_data):
        try:
            imb = orderflow_data.get('imbalance', 0)
            if imb > 0.1: return 1
            elif imb < -0.1: return -1
            return 0
        except: return 0

    def calculate_final_signal(self, signals):
        try:
            weights = {
                'ema_trend': 0.15,'macd_trend': 0.12,'adx_trend': 0.08,'rsi_momentum': 0.10,
                'stoch_momentum': 0.08,'bb_squeeze': 0.07,'volume_surge': 0.10,
                'supertrend_signal': 0.10,'squeeze_momentum': 0.08,'orderflow_imbalance': 0.07
            }
            ws, tw = 0, 0
            for name, w in weights.items():
                if name in signals: ws += signals[name]*w; tw += w
            return max(min(ws/tw if tw>0 else 0, 1), -1)
        except: return 0

    def calculate_confidence(self, signals):
        try:
            strong = sum(1 for k,v in signals.items() if k!='final_signal' and abs(v)>0.5)
            total = len([k for k in signals if k!='final_signal'])
            return strong/total if total>0 else 0
        except: return 0

    def generate_comprehensive_signals(self, df, liquidation_data=None, orderflow_data=None):
        try:
            s = {}
            s['ema_trend'] = self.get_ema_trend_signal(df)
            s['macd_trend'] = self.get_macd_signal(df)
            s['adx_trend'] = self.get_adx_trend_signal(df)
            s['rsi_momentum'] = self.get_rsi_signal(df)
            s['stoch_momentum'] = self.get_stochastic_signal(df)
            s['bb_squeeze'] = self.get_bollinger_squeeze(df)
            s['volume_surge'] = self.get_volume_signal(df)
            s['supertrend_signal'] = self.get_supertrend_signal(df)
            s['squeeze_momentum'] = self.get_squeeze_signal(df)
            s['orderflow_imbalance'] = self.get_orderflow_signal(orderflow_data or {})
            s['final_signal'] = self.calculate_final_signal(s)
            s['confidence'] = self.calculate_confidence(s)
            return s
        except Exception as e:
            print(f"Signal generation error: {e}")
            return {'final_signal': 0, 'confidence': 0}
