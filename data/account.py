import json

class Account:

    def __init__(self, id, amount, takerFee=1):
        self.id = id
        self.amount = amount
        self.takerFee = takerFee
    
    def actualize(self, exchange_client=None):
        amount = 0
        fees = 1

        if exchange_client is None:
            print("No client were passed as parameter")
            return None
        
        response = exchange_client.getAccountDetails()
        if response is not None:
            amount = json.loads(response)['amount']

        fees = exchange_client.getAccountFees()
        
        if self.amount != amount:
            print("Uneven account balance between local and remote")
            self.amount = amount
        
        if fees != self.takerFee:
            print("Fees amount changed")
            self.takerFee = fees