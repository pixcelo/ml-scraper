import ccxt
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

        # Initialize exchange
        self.exchange = getattr(ccxt, self.exchange_name)({
            "apiKey": self.api_key,
            "secret": self.secret_key,
            "enableRateLimit": True,
            'options': {'defaultType': 'linear'}
        })

        self.logger = Logger("trade")
        self.discord_notifier = DiscordNotifier(config)
        self.account = Account(self.exchange)
        self.recv_window=str(10000)
        self.url="https://api.bybit.com"
        # self.url="https://api-testnet.bybit.com" 
        self.mode = self.set_position_mode(0)
        self.qty = 0.002

    def get_ohlcv(self, timeframe):
        ohlcv = self.exchange.fetch_ohlcv("BTC/USDT", timeframe)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df[f"{timeframe}_timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index(f"{timeframe}_timestamp", inplace=True)
        df.columns = [f"{timeframe}_{col}" for col in df.columns]
        return df

    def get_market_data(self):
        timeframes = ["1m", "5m", "15m", "1h", "4h"]
        # Get OHLCV data for each timeframe
        ohlcv_data = [self.get_ohlcv(timeframe) for timeframe in timeframes]
        self.logger().info("get market data.")
        return ohlcv_data

    def execute_trade(self, prediction):
        self.check_balance()
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
    
    def http_request(self, endpoint, method, params, info):
        try:
            httpClient = requests.Session()
            global time_stamp
            time_stamp = str(int(time.time() * 10 ** 3))
            payload = json.dumps(params)
            signature = self.genSignature(payload)
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-SIGN': signature,
                'X-BAPI-SIGN-TYPE': '2',
                'X-BAPI-TIMESTAMP': time_stamp,
                'X-BAPI-RECV-WINDOW': self.recv_window,
                'Content-Type': 'application/json'
            }
            if method == "POST":
                response = httpClient.request(method, self.url + endpoint, headers=headers, data=payload)
            else:
                payload = urlencode(params)
                response = httpClient.request(method, self.url + endpoint + '?' + payload, headers=headers)

            if response.status_code == 200:
                if response.text:
                    response_data = response.json()
                    summary = f"{info} succeeded. Elapsed Time: {response.elapsed}, Result: {response_data}"
                else:
                    summary = f"{info} succeeded. Elapsed Time: {response.elapsed}, Result: No response data"
            else:
                if response.text:
                    response_data = response.json()
                    summary = f"{info} failed. Elapsed Time: {response.elapsed}, Error: {response_data}"
                else:
                    summary = f"{info} failed. Elapsed Time: {response.elapsed}, Result: No response data"

            self.logger().info(summary)
            self.discord_notifier.notify(summary)
            print(summary)
            return True

        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            print(f"{info} failed. An exception occurred: {e}")
            return False


    def get_best_bid_ask_price(self, symbol, side):
        order_book = self.exchange.fetch_order_book(symbol)
        if side == 'buy':
            return order_book['bids'][0][0]
        else:
            return order_book['ask'][0][0]
        
    def set_position_mode(self, mode):
        endpoint = "/v5/position/switch-mode"
        method = "POST"
        params = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "coin": "USDT",
            "mode": mode  # Position mode. 0: Merged Single. 3: Both Sides
        }
        response = self.http_request(endpoint, method, params, "Set Position Mode")
        return response
        
    def check_balance(self):
        self.account.get_balance()

    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature