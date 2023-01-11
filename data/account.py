class Account:

    def __init__(self, available, makerFee=1, takerFee=1):
        self.available = available
        self.makerFee = makerFee
        self.takerFee = takerFee
        self.total = 0
