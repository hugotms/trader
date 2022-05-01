import json

class Account:

    def __init__(self, id, amount, makerFee=1, takerFee=1):
        self.id = id
        self.amount = amount
        self.makerFee = makerFee
        self.takerFee = takerFee
