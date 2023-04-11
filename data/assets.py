class Crypto:

    def __init__(self, instrument_code, base, currency, owned, placed, current, placed_on):
        self.instrument_code = instrument_code
        self.base = base
        self.currency = currency
        self.owned = owned
        self.placed = placed
        self.current = current
        self.placed_on = placed_on
        self.macd = 0
        self.signal = 0
        self.rsi = 0
        self.stochastic_k = 0
        self.stochastic_d = 0
        self.danger = 1
        self.hourlyVolume = 0
        self.dailyVolume = 0
        self.precision = 0
        self.stop_id = ""
        self.market_id = ""
        self.failed = False
        self.alerted = False
        self.last_price = 0

    def setHigher(self):
        self.higher = self.placed
        if self.current > self.placed:
            self.higher = self.current
        
        return self
    