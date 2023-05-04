class PositionManager:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol
        self.position = []
        self.update_positions()

    def update_positions(self):
        try:
            response = self.exchange.fetch_positions([self.symbol])
            positions = response
            self.positions = []  # init self.positions
            for position in positions:
                if position['entryPrice'] is not None and \
                   position['symbol'].split(':')[0].replace("/", "") == self.exchange.market_id(self.symbol).replace("/", ""):
                    self.positions.append(position)
        except Exception as e:
            print(f"An error occurred while fetching positions: {e}")

    def get_position_pnl(self, positions):
        for position in positions:
            if position is not None:
                info = position['info']
                print(f"{info['side']}: unrealisedPnl {info['unrealisedPnl']}")
    
    def separate_positions_by_side(self):
        long_positions = []
        short_positions = []

        for position in self.positions:
            if position['info']['side'] == 'Buy':
                long_positions.append(position)
            elif position['info']['side'] == 'Sell':
                short_positions.append(position)

        self.get_position_pnl(long_positions)
        self.get_position_pnl(short_positions)

        return long_positions, short_positions
