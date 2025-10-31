
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Conv1D, MaxPooling1D, BatchNormalization
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

class AILearningEngine:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.training_data = []
        self.model_performance = {}

    def create_ensemble_models(self):
        self.models = {
            'random_forest': RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42),
            'xgboost': XGBClassifier(n_estimators=200, max_depth=10, learning_rate=0.1, random_state=42, eval_metric='mlogloss'),
            'gradient_boosting': GradientBoostingClassifier(n_estimators=200, random_state=42),
            'neural_network': MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42),
            'svm': SVC(probability=True, random_state=42)
        }

    def create_deep_learning_model(self, input_shape):
        model = Sequential([
            Conv1D(64, 3, activation='relu', input_shape=input_shape),
            BatchNormalization(),
            MaxPooling1D(2),
            Conv1D(128, 3, activation='relu'),
            BatchNormalization(),
            MaxPooling1D(2),
            LSTM(64, return_sequences=True, dropout=0.2),
            LSTM(32, dropout=0.2),
            Dense(64, activation='relu'),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(3, activation='softmax')
        ])
        model.compile(optimizer=Adam(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])
        return model

    def prepare_training_data(self, df, lookback_window=50):
        features, targets = [], []
        for i in range(lookback_window, len(df)-1):
            price_features = [
                df['close'].iloc[i] / df['close'].iloc[i-1] - 1,
                df['high'].iloc[i] / df['low'].iloc[i] - 1,
                (df['volume'].iloc[i] / df['volume'].iloc[i-20:i].mean()) if i >= 20 else 1,
            ]
            tech_cols = ['rsi', 'macd', 'macd_histogram', 'adx', 'atr_percent', 'bb_position', 'volume_ratio', 'obv', 'cmf']
            tech_features = [df[c].iloc[i] for c in tech_cols if c in df.columns]
            features.append(price_features + tech_features)

            future_return = df['close'].iloc[i+1] / df['close'].iloc[i] - 1
            if future_return > 0.002:     targets.append(2)  # BUY
            elif future_return < -0.002:  targets.append(0)  # SELL
            else:                          targets.append(1)  # HOLD
        return np.array(features), np.array(targets)

    def train_models(self, df):
        print("🤖 Training AI Models...")
        X, y = self.prepare_training_data(df)
        if len(X) == 0:
            print("❌ Not enough data for training")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        self.scalers['standard'] = StandardScaler()
        X_train_scaled = self.scalers['standard'].fit_transform(X_train)
        X_test_scaled = self.scalers['standard'].transform(X_test)

        self.create_ensemble_models()
        for name, model in self.models.items():
            model.fit(X_train_scaled, y_train)
            self.model_performance[name] = {
                'train_accuracy': model.score(X_train_scaled, y_train),
                'test_accuracy': model.score(X_test_scaled, y_test)
            }
            print(f"✅ {name}: Train={self.model_performance[name]['train_accuracy']:.3f}, Test={self.model_performance[name]['test_accuracy']:.3f}")

        # Deep model
        X_lstm = X_train_scaled.reshape(X_train_scaled.shape[0], X_train_scaled.shape[1], 1)
        X_test_lstm = X_test_scaled.reshape(X_test_scaled.shape[0], X_test_scaled.shape[1], 1)
        from tensorflow.keras.utils import to_categorical
        y_train_c = to_categorical(y_train, 3)
        y_test_c = to_categorical(y_test, 3)
        self.models['deep_learning'] = self.create_deep_learning_model((X_lstm.shape[1], 1))
        history = self.models['deep_learning'].fit(X_lstm, y_train_c, epochs=25, batch_size=32, validation_data=(X_test_lstm, y_test_c), verbose=0)
        dl_score = self.models['deep_learning'].evaluate(X_test_lstm, y_test_c, verbose=0)[1]
        self.model_performance['deep_learning'] = {'train_accuracy': max(history.history['accuracy']), 'test_accuracy': dl_score}
        print(f"✅ deep_learning: Test Accuracy={dl_score:.3f}")

    def predict_ensemble(self, current_features):
        if not self.models: return 0, 0
        features_scaled = self.scalers['standard'].transform([current_features])
        preds, confs = {}, {}
        for name, model in self.models.items():
            if name == 'deep_learning':
                proba = model.predict(features_scaled.reshape(1, -1, 1), verbose=0)[0]
            else:
                proba = model.predict_proba(features_scaled)[0]
            buy, sell = proba[2], proba[0]
            total = buy + sell
            buy_n = buy/total if total>0 else 0.5
            sell_n = sell/total if total>0 else 0.5
            if buy_n > 0.6: preds[name], confs[name] = 1, buy_n
            elif sell_n > 0.6: preds[name], confs[name] = -1, sell_n
            else: preds[name], confs[name] = 0, max(buy_n, sell_n)
        final = sum(preds.values())/len(preds)
        avgc = sum(confs.values())/len(confs)
        return final, avgc

    def online_learning(self, new_data_point, actual_result):
        self.training_data.append((new_data_point, actual_result))
        if len(self.training_data) % 100 == 0:
            print("🔄 Online learning placeholder — add incremental fit here")

    def save_models(self, path='data/ai_models/'):
        import os
        os.makedirs(path, exist_ok=True)
        for name, model in self.models.items():
            if name == 'deep_learning':
                model.save(f'{path}{name}_model.h5')
            else:
                joblib.dump(model, f'{path}{name}_model.pkl')
        joblib.dump(self.scalers['standard'], f'{path}scaler.pkl')
        print("💾 Models saved")

    def load_models(self, path='data/ai_models/'):
        try:
            self.scalers['standard'] = joblib.load(f'{path}scaler.pkl')
            from tensorflow.keras.models import load_model
            import os
            files = {
                'random_forest': f'{path}random_forest_model.pkl',
                'xgboost': f'{path}xgboost_model.pkl',
                'gradient_boosting': f'{path}gradient_boosting_model.pkl',
                'neural_network': f'{path}neural_network_model.pkl',
                'svm': f'{path}svm_model.pkl',
                'deep_learning': f'{path}deep_learning_model.h5'
            }
            loaded = False
            for n, p in files.items():
                if os.path.exists(p):
                    if n == 'deep_learning':
                        self.models[n] = load_model(p)
                    else:
                        self.models[n] = joblib.load(p)
                    loaded = True
            return loaded
        except Exception as e:
            print(f"Load error: {e}")
            return False
