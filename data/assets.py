import json

class Crypto:

    def __init__(self, instrument_code, base, currency, owned, placed, current, placed_on):
        self.instrument_code = instrument_code
        self.base = base
        self.currency = currency
        self.owned = owned
        self.placed = placed
        self.current = current
        self.placed_on = placed_on
        self.danger = 0
        self.loaded = False
        self.dailyDanger = 0
        self.dailyVolume = 0
        self.weeklyDanger = 0
        self.monthlyDanger = 0
        self.precision = 4
        self.stop_id = ""

    def setHigher(self):
        self.higher = self.placed
        if self.current > self.placed:
            self.higher = self.current
        
        return self
    