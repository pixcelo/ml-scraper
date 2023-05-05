import pandas as pd
import requests
from urllib.parse import urlencode
from discord_notifier import DiscordNotifier
from scraper import Scraper
from logger import Logger

class Trade:
    def __init__(self, config):
        self.api_key = config.get("exchange", "api_key")
        self.secret_key = config.get("exchange", "secret_key")
        self.exchange_name = config.get("exchange", "exchange_name")
        self.logger = Logger("trade")
        self.discord_notifier = DiscordNotifier(config)
        self.scraper = Scraper()
        self.url = "https://api.twelvedata.com"
        self.qty = 1

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
        self.scraper.login()
        position = self.scraper.exists_open_interest()
        trade_action = self.decide_trade_action(position["buy"], position["sell"], prediction)

        amount = self.qty
        result = None

        if trade_action == "BUY_TO_OPEN":
            result = self.scraper.place_order("Buy", amount)
        elif trade_action == "SELL_TO_OPEN":
            result = self.scraper.place_order("Sell", amount)
        # After executing the settlement order, hold a new position in the same direction
        elif trade_action == "SELL_TO_CLOSE":
            result = self.scraper.place_order("Sell", amount)
            if result:
                result = self.scraper.place_order("Sell", amount)
        elif trade_action == "BUY_TO_CLOSE":
            result = self.scraper.place_order("Buy", amount)
            if result:
                result = self.scraper.place_order("Buy", amount)
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
        if long_positions != "0":
            if prediction == 1:
                return "HOLD_LONG"
            else:
                return "SELL_TO_CLOSE"
        else:
            if prediction == 1:
                return "BUY_TO_OPEN"
            else:
                pass

        if short_positions != "0":
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
    
    def http_request(self, endpoint, params):
        try:
            response = requests.get(self.url + endpoint, params=params)
            data = response.json()
            return data
        
        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            print(f"http_request failed. An exception occurred: {e}")
            return None