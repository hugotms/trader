import json

class Account:

    def __init__(self, id, available, makerFee=1, takerFee=1):
        self.id = id
        self.available = available
        self.makerFee = makerFee
        self.takerFee = takerFee
        self.dailyProfit = 0
        self.dailyLoss = 0
        self.dailyTrade = 0
        self.weeklyProfit = 0
        self.weeklyLoss = 0
        self.weeklyTrade = 0
        self.monthlyProfit = 0
        self.monthlyLoss = 0
        self.monthlyTrade = 0
    
    def addTrade(self):
        self.dailyTrade += 1
        self.weeklyTrade += 1
        self.monthlyTrade += 1
    
    def addProfit(self, profit):
        self.dailyProfit += profit
        self.weeklyProfit += profit
        self.monthlyProfit += profit
        self.addTrade()
    
    def addLoss(self, loss):
        self.dailyLoss += loss
        self.weeklyLoss += loss
        self.monthlyLoss += loss
        self.addTrade()
