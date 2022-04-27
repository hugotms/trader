import json

class Crypto:

    def __init__(self, order_id, cryptoName, owned, placed, current):
        self.order_id = order_id
        self.cryptoName = cryptoName
        self.owned = owned
        self.placed = placed
        self.current = current
        self.higher = current
        self.loaded = False
        self.dailyDanger = 0
        self.weeklyDanger = 0
        self.monthlyDanger = 0
    
    def to_csv(self):
        return (self.cryptoName + ","
            + str(self.owned) + "," 
            + str(self.current) + "," 
            + str(self.higher) + ","
            + str(self.danger)) 