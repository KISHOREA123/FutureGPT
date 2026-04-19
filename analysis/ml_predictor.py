"""
ML Price Direction Predictor
Uses GradientBoosting classifier to predict short-term price direction.
Features: 16+ technical indicators
Output: Direction (UP/DOWN), confidence, accuracy, feature importance.
"""
import numpy as np
import pandas as pd
import logging
from config import ML_LOOKAHEAD

logger = logging.getLogger(__name__)


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute ML features from OHLCV data.
    All features are derived in-DataFrame to avoid look-ahead bias.
    """
    features = pd.DataFrame(index=df.index)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Price-based features
    features["returns_1"] = close.pct_change(1)
    features["returns_3"] = close.pct_change(3)
    features["returns_5"] = close.pct_change(5)
    features["returns_10"] = close.pct_change(10)

    # Volatility features
    features["volatility_5"] = close.pct_change().rolling(5).std()
    features["volatility_10"] = close.pct_change().rolling(10).std()
    features["range_pct"] = (high - low) / close

    # Moving average features
    ema_9 = close.ewm(span=9, adjust=False).mean()
    ema_21 = close.ewm(span=21, adjust=False).mean()
    sma_50 = close.rolling(50).mean()
    features["price_vs_ema9"] = (close - ema_9) / close
    features["price_vs_ema21"] = (close - ema_21) / close
    features["price_vs_sma50"] = (close - sma_50) / close
    features["ema_9_21_diff"] = (ema_9 - ema_21) / close

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    rs = avg_gain / avg_loss
    features["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    features["macd_histogram"] = macd_line - signal_line

    # Stochastic
    low_14 = low.rolling(14).min()
    high_14 = high.rolling(14).max()
    denom = high_14 - low_14
    denom = denom.replace(0, 1)
    features["stoch_k"] = 100 * (close - low_14) / denom

    # Volume features
    vol_sma = volume.rolling(20).mean()
    features["volume_ratio"] = volume / vol_sma
    features["volume_change"] = volume.pct_change(1)

    # ATR-based
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    features["atr_pct"] = atr / close

    # ADX (simplified)
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_smooth = tr.ewm(alpha=1/14, min_periods=14).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_smooth)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_smooth)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    features["adx"] = dx.ewm(alpha=1/14, min_periods=14).mean()

    # Bollinger Band position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    features["bb_position"] = (close - bb_lower) / (bb_upper - bb_lower)

    return features


def _create_target(df: pd.DataFrame, lookahead: int = ML_LOOKAHEAD) -> pd.Series:
    """Create binary target: 1 if price goes up in N candles, 0 otherwise."""
    future_close = df["close"].shift(-lookahead)
    target = (future_close > df["close"]).astype(int)
    return target


def run_ml_prediction(df: pd.DataFrame) -> dict:
    """
    Train a model on historical data and predict next direction.

    Returns:
        dict with prediction, confidence, accuracy, top features
    """
    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import cross_val_score
    except ImportError:
        return {
            "prediction": "N/A",
            "confidence": 0,
            "accuracy": 0,
            "features": [],
            "error": "scikit-learn not installed",
        }

    if len(df) < 100:
        return {
            "prediction": "N/A",
            "confidence": 0,
            "accuracy": 0,
            "features": [],
            "error": "Insufficient data (need 100+ candles)",
        }

    try:
        # Prepare features and target
        features = _prepare_features(df)
        target = _create_target(df)

        # Align and drop NaN rows
        combined = pd.concat([features, target.rename("target")], axis=1)
        combined = combined.dropna()

        if len(combined) < 80:
            return {
                "prediction": "N/A",
                "confidence": 0,
                "accuracy": 0,
                "features": [],
                "error": "Insufficient clean data after feature computation",
            }

        X = combined.drop("target", axis=1)
        y = combined["target"]

        # Split: train on all but last row (which we predict)
        X_train = X.iloc[:-1]
        y_train = y.iloc[:-1]
        X_latest = X.iloc[-1:].copy()

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_latest_scaled = scaler.transform(X_latest)

        # Train model
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
        )
        model.fit(X_train_scaled, y_train)

        # Cross-validation accuracy
        try:
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=min(5, len(X_train) // 20), scoring="accuracy")
            accuracy = round(float(cv_scores.mean()) * 100, 1)
        except Exception:
            accuracy = 0.0

        # Predict
        prediction_proba = model.predict_proba(X_latest_scaled)[0]
        prediction_class = model.predict(X_latest_scaled)[0]

        direction = "UP 📈" if prediction_class == 1 else "DOWN 📉"
        confidence = round(float(max(prediction_proba)) * 100, 1)

        # Feature importance
        importance = model.feature_importances_
        feature_names = X.columns.tolist()
        top_features = sorted(
            zip(feature_names, importance),
            key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "prediction": direction,
            "confidence": confidence,
            "accuracy": accuracy,
            "direction_raw": "UP" if prediction_class == 1 else "DOWN",
            "up_probability": round(float(prediction_proba[1]) * 100, 1) if len(prediction_proba) > 1 else 0,
            "down_probability": round(float(prediction_proba[0]) * 100, 1),
            "features": [
                {"name": name, "importance": round(float(imp) * 100, 1)}
                for name, imp in top_features
            ],
            "lookahead": ML_LOOKAHEAD,
            "training_samples": len(X_train),
            "total_features": len(feature_names),
        }

    except Exception as e:
        logger.error(f"ML prediction error: {e}")
        return {
            "prediction": "N/A",
            "confidence": 0,
            "accuracy": 0,
            "features": [],
            "error": str(e),
        }
