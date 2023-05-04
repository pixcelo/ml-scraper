import configparser
from trade import Trade
from predict import Predictor
from logger import Logger
from discord_notifier import DiscordNotifier
import time

def main():
    # Read configuration
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Initialize components
    trade = Trade(config)
    predictor = Predictor(config)
    logger = Logger("main")
    discord_notifier = DiscordNotifier(config)

    print("Main function started.")

    # Main loop
    while True:
        try:
            # Get market data
            market_data = trade.get_market_data()

            # Make predictions
            prediction = predictor.predict(market_data)
            print(f"The predicted value is {prediction}.")

            # Execute trade
            trade_result = trade.execute_trade(prediction)
            discord_notifier.notify(trade_result)
            
            wait_time_minutes = 15
            print(f"Waiting for {wait_time_minutes} minutes before continuing...")
            time.sleep(wait_time_minutes * 60)

        except Exception as e:
            logger().error(f"An exception occurred: {e}")
            discord_notifier.notify(f"An exception occurred: {e}")

if __name__ == "__main__":
    main()
