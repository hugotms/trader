import json

class Account:

    def __init__(self, id, amount, makerFee=1, takerFee=1):
        self.id = id
        self.amount = amount
        self.makerFee = makerFee
        self.takerFee = takerFee
    
    def actualize(self, exchange_client=None):
        amount = 0
        fees = None

        if exchange_client is None:
            print("No client were passed as parameter")
            return None
        
        response = exchange_client.getAccountDetails()
        if response is not None:
            amount = json.loads(response)['amount']
        
        if self.amount != amount:
            print("Uneven account balance between local and remote")
            self.amount = amount
        
        response = exchange_client.getAccountFees()
        if response is not None:
            fees = json.loads(response)
        
        if fees is not None:
            self.takerFee = fees['takerFee']
            self.makerFee = fees['makerFee']
