
import asyncio
from .quantum_ai import QuantumTradingAI
from .ai_engine import AILearningEngine

class QuantumTradingAIWithML(QuantumTradingAI):
    def __init__(self):
        super().__init__()
        self.ai_engine = AILearningEngine()
        self.is_ai_trained = self.ai_engine.load_models()

    def prepare_ai_features(self, df):
        if len(df) < 50: return []
        curr, prev = df.iloc[-1], df.iloc[-2]
        feats = [
            curr['close']/prev['close'] - 1,
            curr['high']/curr['low'] - 1,
            curr['volume']/df['volume'].iloc[-20:].mean() if len(df)>=20 else 1
        ]
        for ind in ['rsi','macd','macd_histogram','adx','atr_percent','bb_position','volume_ratio','obv','cmf']:
            if ind in df.columns: feats.append(curr[ind])
        return feats

    async def run_trading_bot_with_ai_once(self, symbol, timeframes=['5m','15m','1h']):
        """Single-cycle compute: fetch -> indicators -> signals and AI."""
        data = await self.fetch_multiple_timeframes(symbol, timeframes)
        if not data: return None
        primary = data['5m'] if '5m' in data else list(data.values())[0]
        primary = self.calculate_all_indicators(primary)

        ai_sig = 0; ai_conf = 0
        if self.is_ai_trained:
            feats = self.prepare_ai_features(primary)
            if feats:
                ai_sig, ai_conf = self.ai_engine.predict_ensemble(feats)

        trad = self.generate_comprehensive_signals(primary, None, self.orderflow_data)
        # combine
        if ai_conf > 0.7: aw, tw = 0.7, 0.3
        elif ai_conf > 0.5: aw, tw = 0.5, 0.5
        else: aw, tw = 0.3, 0.7
        combined = max(min(ai_sig*aw + trad.get('final_signal',0)*tw, 1), -1)

        return {
            'df': primary,
            'ai_signal': ai_sig,
            'ai_confidence': ai_conf,
            'traditional': trad,
            'combined': combined
        }

    async def run_ai_stream(self, symbol, timeframes=['5m']):
        """Async signal stream for Telegram."""
        while True:
            try:
                res = await self.run_trading_bot_with_ai_once(symbol, timeframes=timeframes)
                if res is not None:
                    if abs(res['combined']) > 0.25:
                        yield {
                            "direction": "LONG" if res['combined'] > 0 else "SHORT",
                            "confidence": max(res['ai_confidence'], res['traditional'].get('confidence',0)),
                            "price": res['df']['close'].iloc[-1]
                        }
                await asyncio.sleep(20)
            except Exception as e:
                print(f"Stream error: {e}")
                await asyncio.sleep(30)
