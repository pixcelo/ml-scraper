import pandas as pd
import requests
import time
import hmac
import uuid
import hashlib
import json
from urllib.parse import urlencode
from position_manager import PositionManager
from discord_notifier import DiscordNotifier
from account import Account
from logger import Logger

class Trade:
    def __init__(self, config):
        self.api_key = config.get("exchange", "api_key")
        self.secret_key = config.get("exchange", "secret_key")
        self.exchange_name = config.get("exchange", "exchange_name")
        self.logger = Logger("trade")
        self.discord_notifier = DiscordNotifier(config)
        self.url = "https://api.twelvedata.com"
        self.qty = 0.002

    def get_ohlcv(self, timeframe):
        endpoint = "/time_series"
        params = {
            "symbol": "SPX",
            "interval": timeframe,
            "apikey": self.api_key,
            "outputsize": 210 # max 1000
        }
        data = self.http_request(endpoint, params)

        if "values" in data:
            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            df = df.astype(float)
            df.columns = [f"{timeframe}_{col}" for col in df.columns]
            df = df.drop(columns=[f"{timeframe}_volume"])
            return df
        else:
            return pd.DataFrame()
    
    def get_market_data(self):
        timeframes = ["1min", "5min", "15min", "1h", "4h", "1day"]
        # Get OHLCV data for each timeframe
        ohlcv_data = []
        ohlcv_data = [self.get_ohlcv(timeframe) for timeframe in timeframes]
        self.logger().info("get market data.")
        return ohlcv_data

    def execute_trade(self, prediction):
        # self.check_balance()
        # Execute trade based on prediction here
        position_manager = PositionManager(self.exchange, "BTCUSDT")
        long_positions, short_positions = position_manager.separate_positions_by_side()

        amount = self.qty
        result = None

        trade_action = self.decide_trade_action(long_positions, short_positions, prediction)

        if trade_action == "BUY_TO_OPEN":
            result = self.place_order("BTCUSDT", "Buy", amount)
        elif trade_action == "SELL_TO_OPEN":
            result = self.place_order("BTCUSDT", "Sell", amount)
        # After executing the settlement order, hold a new position in the same direction
        elif trade_action == "SELL_TO_CLOSE":
            result = self.place_order("BTCUSDT", "Sell", amount)
            if result:
                result = self.place_order("BTCUSDT", "Sell", amount)
        elif trade_action == "BUY_TO_CLOSE":
            result = self.place_order("BTCUSDT", "Buy", amount)
            if result:
                result = self.place_order("BTCUSDT", "Buy", amount)
        elif trade_action == "HOLD_LONG" or trade_action == "HOLD_SHORT" or trade_action == "DO_NOTHING":
            pass

        message = f"{trade_action}: "

        if result is True:
            message += "The order was successful."
        elif result is False:
            message += "The order was failed."
        else:
            message += "Hold current position."
        
        print(message)
        return message
    
    def decide_trade_action(self, long_positions, short_positions, prediction):
        if long_positions:
            if prediction == 1:
                return "HOLD_LONG"
            else:
                return "SELL_TO_CLOSE"
        else:
            if prediction == 1:
                return "BUY_TO_OPEN"
            else:
                pass

        if short_positions:
            if prediction != 1:
                return "HOLD_SHORT"
            else:
                return "BUY_TO_CLOSE"
        else:
            if prediction != 1:
                return "SELL_TO_OPEN"
            else:
                pass

        return "DO_NOTHING"

    def place_order(self, symbol, side, amount):
        endpoint="/v5/order/create"
        method="POST"
        orderLinkId=uuid.uuid4().hex
        params = {
            "category": "linear",
            "symbol": symbol,
            "isLeverage": 1,
            "side": side,
            "orderType": "Market",
            "qty": str(amount),
            "orderLinkId": orderLinkId,
            "positionIdx": 0 # one-way mode
        }
        return self.http_request(endpoint, method, params, "Order")   
    
    def http_request(self, endpoint, params):
        try:
            response = requests.get(self.url + endpoint, params=params)
            data = response.json()
            return data
        
        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            print(f"http_request failed. An exception occurred: {e}")
            return None