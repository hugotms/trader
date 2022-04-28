import json

class Crypto:

    def __init__(self, cryptoName, owned, placed, current):
        self.cryptoName = cryptoName
        self.owned = owned
        self.placed = placed
        self.current = current
        self.danger = 0
        self.loaded = False
        self.dailyDanger = 0
        self.weeklyDanger = 0
        self.monthlyDanger = 0

    def setHigher(self):
        self.higher = self.placed
        if self.current > self.placed:
            self.higher = self.current
        
        return self
    
    def to_csv(self):
        return (self.cryptoName + ","
            + str(self.owned) + "," 
            + str(self.current) + "," 
            + str(self.higher) + ","
            + str(self.danger)) 