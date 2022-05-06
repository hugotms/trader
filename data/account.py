import json

class Account:

    def __init__(self, id, available, makerFee=1, takerFee=1):
        self.id = id
        self.available = available
        self.makerFee = makerFee
        self.takerFee = takerFee
