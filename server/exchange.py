from server import web
from server import fs

import json
import time
import os

from datetime import datetime, timedelta

from data import account
from data import assets

class BitpandaPro:
    baseUrl = "https://api.exchange.bitpanda.com/public/v1"

    def __init__(self):
        self.filesystem = fs.File().new()

    def new(self):
        if self.filesystem is None:
            print("Unable to use file. Please check permissions")
            return None
        
        if os.getenv('EXCHANGE_API_KEY') is None:
            print("Required API key was not set")
            return None
        
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + os.getenv('EXCHANGE_API_KEY')
            }
        
        return self
    
    def getAccountDetails(self):
        amount = 0

        client = web.Api(BitpandaPro.baseUrl + '/account/balances', headers=self.headers).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            client.send()

        time.sleep(1)
        
        if client.getStatusCode() != 200:
            print("Error while trying to access account balance data")
            return None
        
        for item in client.getData()['balances']:
            if item['currency_code'] == 'EUR':
                amount += float(item['available'])

        return json.dumps({
                "account_id": client.getData()['account_id'],
                "amount": amount
            })
    
    def getAccountFees(self):
        makerFee = 1
        takerFee = 1

        client = web.Api(BitpandaPro.baseUrl + '/account/fees', headers=self.headers).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            client.send()

        time.sleep(1)
        
        if client.getStatusCode() != 200:
            print("Error while trying to access account fees data")
            return None
        
        running_trading_volume = client.getData()['running_trading_volume']

        for tier in client.getData()['fee_tiers']:
            if tier['volume'] >= running_trading_volume:
                makerFee = 1 - float(tier['maker_fee']) / 100
                takerFee = 1 - float(tier['taker_fee']) / 100

        return json.dumps({
                "makerFee": makerFee,
                "takerFee": takerFee
            })
    
    def getAccount(self):
        response = self.getAccountDetails()
        if response is None:
            print("No account could be found")
            return None
        
        res = json.loads(response)

        new = account.Account(id=res['account_id'], amount=res['amount'])

        response = self.getAccountFees()
        if response is not None:
            res = json.loads(response)
            new.makerFee = res['makerFee']
            new.takerFee = res['takerFee']

        return new
    
    def getPrices(self, crypto, time_unit=None):
        if time_unit is None:
            return None
        
        header = {
            "Accept": "application/json"
        }

        tz = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        tz2 = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        client = web.Api(BitpandaPro.baseUrl + "/candlesticks/" + crypto.cryptoName + "?unit=" + time_unit + "&period=1&from=" + tz2 + "&to=" + tz, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get price tickers")
            return None
        
        if client.getData() == []:
            print("No prices data were found for time unit " + time_unit)
            return None

        return json.dumps({
                "open": float(client.getData()[0]['open']),
                "close": float(client.getData()[0]['close'])
            })
    
    def getPrice(self, cryptoName):
        header = {
            "Accept": "application/json"
        }

        client = web.Api(BitpandaPro.baseUrl + "/market-ticker/" + cryptoName, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get market tickers")
            return None

        return float(client.getData()['last_price'])
    
    def calculateDanger(self, crypto):
        danger = 0

        res = self.getPrices(crypto, time_unit='MINUTES')
        if res is None:
            crypto.danger = danger
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            danger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.05:
            danger += 1
        elif variation > 0.1:
            danger += 2
        
        res = self.getPrices(crypto, time_unit='HOURS')
        if res is None:
            crypto.danger = danger
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            danger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.05:
            danger += 1
        elif variation > 0.1:
            danger += 2
        
        if crypto.loaded == True:
            danger += crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
            crypto.danger = danger
            return self
        
        crypto.dailyDanger = 0
        crypto.weeklyDanger = 0
        crypto.monthlyDanger = 0
        
        res = self.getPrices(crypto, time_unit='DAYS')
        if res is None:
            crypto.danger = danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            crypto.dailyDanger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.1:
            crypto.dailyDanger += 1
        elif variation > 0.2:
            crypto.dailyDanger += 2

        res = self.getPrices(crypto, time_unit='WEEKS')
        if res is None:
            crypto.danger = danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            crypto.weeklyDanger += 1
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.1:
            crypto.weeklyDanger += 1
        elif variation > 0.2:
            crypto.weeklyDanger += 2
        
        res = self.getPrices(crypto, time_unit='MONTHS')
        if res is None:
            crypto.danger = danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            crypto.monthlyDanger += 1
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.4:
            crypto.monthlyDanger += 1
        elif variation > 0.6:
            crypto.monthlyDanger += 2

        crypto.danger = danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
        crypto.loaded = True

        return self


    def getAllActiveTrades(self, listCrypto, account, max_danger):
        active_trades = []

        client = web.Api(BitpandaPro.baseUrl + "/account/trades", headers=self.headers).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            client.send()
        
        time.sleep(1)

        if client.getStatusCode() != 200:
            print("Error while trying to access account active trades")
            return []

        trades = client.getData()['trade_history']

        trade_names = []
        ignored_trades = []
        for item in trades:
            if item['trade']['side'] == "SELL":
                ignored_trades.append(item['trade']['instrument_code'])

            elif item['trade']['instrument_code'] not in ignored_trades:
                amount = float(item['trade']['amount']) * self.getPrice(item['trade']['instrument_code']) * account.makerFee

                if item['trade']['instrument_code'] not in trade_names:
                    active_trades.append(assets.Crypto(
                        cryptoName=item['trade']['instrument_code'],
                        owned=float(item['trade']['amount']),
                        placed=float(item['trade']['amount']) * float(item['trade']['price']),
                        current=amount
                        ))
                else:
                    for active in active_trades:
                        if active.cryptoName == item['trade']['instrument_code']:
                            active.owned += float(item['trade']['amount'])
                            active.placed += float(item['trade']['amount']) * float(item['trade']['price'])
                            active.current += amount
                            active.higher += amount
                            break
                
                trade_names.append(item['trade']['instrument_code'])
        
        for crypto in listCrypto:
            isFound = False

            for trade in active_trades:
                if crypto.cryptoName == trade.cryptoName:
                    isFound = True
                    trade.placed = crypto.placed

                    if crypto.higher > trade.current:
                        trade.higher = crypto.higher
                    
                    if crypto.loaded:
                        trade.loaded = True
                        trade.weeklyDanger = crypto.weeklyDanger
                        trade.monthlyDanger = crypto.monthlyDanger
                
                if isFound and int(self.filesystem.getLastDanger(trade)) > max_danger % 2:
                    trade.danger += 1

            if not isFound:
                self.filesystem.putInFile(crypto)

        for trade in active_trades:
            self.calculateDanger(trade)

        return active_trades
    
    def stopTrade(self, crypto, account):
        percentage = (1 - ((0.01 * crypto.owned / crypto.current) / crypto.current)) * account.takerFee * account.makerFee
        body = {
            "instrument_code": crypto.cryptoName,
            "side": "SELL",
            "type": "MARKET",
            "amount": str(round(crypto.owned * percentage, 4))
        }

        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            client.send()
        
        time.sleep(1)

        if client.getStatusCode() != 201:
            print("Error while trying to stop trade")
            return 0

        return percentage
    