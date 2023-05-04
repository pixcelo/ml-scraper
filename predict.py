import pickle
import pandas as pd
import numpy as np
import talib

class Predictor:
    def __init__(self, config):
        self.model_path = config.get("model", "model_path")

        # Load model
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)

    def preprocess_market_data(self, dfs):
        processed_dfs = []
        for df in dfs:
            prefix = df.columns[0].split('_')[0]
            processed_df = feature_engineering(df, prefix)
            processed_df = create_label(processed_df, prefix, 15)
            processed_dfs.append(processed_df)

        combined_df = pd.concat(processed_dfs, axis=1).dropna()
        return combined_df
    
    def predict(self, market_data):
        # Preprocess market_data
        preprocessed_data = self.preprocess_market_data(market_data)

        # Make prediction based on preprocessed market_data
        preprocessed_data = preprocessed_data.drop("5m_target", axis=1) 
        prediction_proba = self.model.predict(preprocessed_data, raw_score=False, pred_leaf=False, pred_contrib=False)

        # Apply threshold to the predicted probabilities
        action = np.where(prediction_proba > 0.5, 1, 0)

        return action[0]


# feature engineering
def create_label(df, prefix, lookahead=1):
    df[f'{prefix}_target'] = (df[f'{prefix}_close'].shift(-lookahead) > df[f'{prefix}_close']).astype(int)
    df = df.dropna()
    return df       

def log_transform_feature(X):
    X[X <= 0] = np.finfo(float).eps
    return np.log(X)

def feature_engineering(df, prefix):
    # open = df[f'{prefix}_open'].values
    high = df[f'{prefix}_high'].values
    low = df[f'{prefix}_low'].values
    close = df[f'{prefix}_close'].values
    volume = df[f'{prefix}_volume'].values
    hilo = (high + low) / 2

    df[f'{prefix}_RSI_ST'] = talib.RSI(close)/close
    df[f'{prefix}_RSI_LOG'] = log_transform_feature(talib.RSI(close))
    df[f'{prefix}_MACD'], _, _ = talib.MACD(close)
    df[f'{prefix}_MACD_ST'], _, _ = talib.MACD(close)/close
    df[f'{prefix}_ATR'] = talib.ATR(high, low, close)
    df[f'{prefix}_ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df[f'{prefix}_ADXR'] = talib.ADXR(high, low, close, timeperiod=14)
    
    df[f'{prefix}_SMA10'] = talib.SMA(close, timeperiod=10)
    df[f'{prefix}_SMA50'] = talib.SMA(close, timeperiod=50)
    df[f'{prefix}_SMA200'] = talib.SMA(close, timeperiod=200)
    
    df[f'{prefix}_BB_UPPER'], df[f'{prefix}_BB_MIDDLE'], df[f'{prefix}_BB_LOWER'] = talib.BBANDS(close)
    df[f'{prefix}_BBANDS_upperband'] = (df[f'{prefix}_BB_UPPER'] - hilo) / close
    df[f'{prefix}_BBANDS_middleband'] = (df[f'{prefix}_BB_MIDDLE'] - hilo) / close
    df[f'{prefix}_BBANDS_lowerband'] = (df[f'{prefix}_BB_LOWER'] - hilo) / close
    df[f'{prefix}_STOCH_K'], df[f'{prefix}_STOCH_D'] = talib.STOCH(high, low, close)/close
    df[f'{prefix}_MON'] = talib.MOM(close, timeperiod=5)
    df[f'{prefix}_OBV'] = talib.OBV(close, volume)

    df = df.dropna()
    df = df.reset_index(drop=True)

    return df