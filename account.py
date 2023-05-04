class Account:
    def __init__(self, exchange):
        self.exchange = exchange

    def get_balance(self):
        balance = self.exchange.fetch_balance()
        
        usdt_balance = balance['total']['USDT']
        print(f'USDT balance: {usdt_balance}')
        
        btc_balance = balance['total']['BTC']
        print(f'BTC balance: {btc_balance}')
        
        margin_balance = self.exchange.fetch_balance(params={'type': 'margin'})
        usdt_margin_balance = margin_balance['total']['USDT']
        print(f'USDT margin balance: {usdt_margin_balance}')
        btc_margin_balance = margin_balance['total']['BTC']
        print(f'BTC margin balance: {btc_margin_balance}')
        
        free_margin = margin_balance['free']['USDT']
        print(f'Free margin (USDT): {free_margin}')
        
        if usdt_margin_balance != 0:
            margin_utilization_rate = (usdt_balance - free_margin) / usdt_margin_balance * 100
            print(f'Margin utilization rate: {margin_utilization_rate}%')
        else:
            print("No margin balance available.")