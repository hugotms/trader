from server import web
from server import db

import json
import time
import os

from datetime import datetime, timedelta, date

from data import account
from data import assets

class BitpandaPro:
    baseUrl = "https://api.exchange.bitpanda.com/public/v1"

    def __init__(self, api_key, database, watching_cryptos, ignore_cryptos, watching_currencies):
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
            }
        
        self.database = database
        self.watching_cryptos = watching_cryptos
        self.ignore_cryptos = ignore_cryptos
        self.watching_currencies = watching_currencies
    
    def truncate(self, number, precision):
        res = str(float(int(number * (10**precision))/(10**precision)))
        res_precision = len(res.split('.')[1])

        if res_precision == precision:
            return res
        
        for i in range(precision - res_precision):
            res += '0'
        
        return res
    
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

        new = account.Account(id=res['account_id'], available=res['amount'])

        response = self.getAccountFees()
        if response is not None:
            res = json.loads(response)
            new.makerFee = res['makerFee']
            new.takerFee = res['takerFee']

        return new
    
    def actualizeAccount(self, account):
        available = 0
        fees = None
        
        response = self.getAccountDetails()
        if response is not None:
            available = json.loads(response)['amount']
        
        if account.available != available:
            print("Uneven account balance between local and remote")
            account.available = available
        
        response = self.getAccountFees()
        if response is not None:
            fees = json.loads(response)
        
        if fees is not None:
            account.takerFee = fees['takerFee']
            account.makerFee = fees['makerFee']
    
    def getPrices(self, crypto, time_unit=None):
        if time_unit is None:
            return None
        
        header = {
            "Accept": "application/json"
        }

        tz = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        tz2 = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        client = web.Api(BitpandaPro.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=" + time_unit + "&period=1&from=" + tz2 + "&to=" + tz, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get price tickers")
            return None
        
        if client.getData() == []:
            return None

        return json.dumps({
                "open": float(client.getData()[0]['open']),
                "close": float(client.getData()[0]['close']),
                "volume": float(client.getData()[0]['volume'])
            })
    
    def getPrice(self, instrument_code):
        header = {
            "Accept": "application/json"
        }

        client = web.Api(BitpandaPro.baseUrl + "/market-ticker/" + instrument_code, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get market tickers")
            return None

        return float(client.getData()['last_price'])
    
    def calculateDanger(self, crypto, account, max_danger, min_recovered):
        danger = 0

        if self.database.getLastDanger(crypto, min_recovered) > int(max_danger / 2):
            danger += 1

        res = self.getPrices(crypto, time_unit='MINUTES')
        if res is None:
            crypto.danger = -100
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            danger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.02:
            danger += 1
        elif variation > 0.06:
            danger += 2
        
        res = self.getPrices(crypto, time_unit='HOURS')
        if res is None:
            crypto.danger = -100
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            danger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.05:
            danger += 1
        elif variation > 0.08:
            danger += 2
        
        if crypto.loaded == True:
            danger += crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
            crypto.danger += danger
            return self
        
        crypto.dailyDanger = 0
        crypto.weeklyDanger = 0
        crypto.monthlyDanger = 0

        if date.today().weekday() == 4:
            crypto.dailyDanger += 1
        elif date.today().weekday() >= 5:
            crypto.dailyDanger += 2
        
        res = self.getPrices(crypto, time_unit='DAYS')
        if res is None:
            crypto.danger = -100
            return self
        res = json.loads(res)

        if account.available >= res['volume']:
            danger += 2

        if account.available * 10 >= res['volume']:
            danger += 1
        
        elif account.available * 20 < res['volume']:
            danger -= 2

        if res['open'] > res['close']:
            crypto.dailyDanger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.1:
            crypto.dailyDanger += 1
        elif variation > 0.12:
            crypto.dailyDanger += 2

        res = self.getPrices(crypto, time_unit='WEEKS')
        if res is None:
            crypto.danger = -100
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
            crypto.danger = -100
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            crypto.monthlyDanger += 1
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.3:
            crypto.monthlyDanger += 1
        elif variation > 0.4:
            crypto.monthlyDanger += 2

        crypto.danger += danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
        crypto.loaded = True

        return self


    def getAllActiveTrades(self, account, max_danger, min_recovered):
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
            if len(self.ignore_cryptos) != 0 and item['trade']['instrument_code'] in self.ignore_cryptos:
                continue

            elif len(self.watching_cryptos) != 0 and item['trade']['instrument_code'] not in self.watching_cryptos:
                continue
            
            elif len(self.watching_currencies) != 0 and item['trade']['instrument_code'].split("_")[1] not in self.watching_currencies:
                continue
            
            elif item['trade']['instrument_code'] in ignored_trades:
                continue

            elif item['trade']['side'] == "SELL":
                ignored_trades.append(item['trade']['instrument_code'])
                continue

            amount = float(item['trade']['amount']) * self.getPrice(item['trade']['instrument_code']) * account.makerFee
            
            if item['trade']['instrument_code'] not in trade_names:
                active_trades.append(assets.Crypto(
                    instrument_code=item['trade']['instrument_code'],
                    base=item['trade']['instrument_code'].split('_')[0],
                    currency=item['trade']['instrument_code'].split('_')[1],
                    owned=float(item['trade']['amount']) * account.makerFee,
                    placed=float(item['trade']['amount']) * float(item['trade']['price']) * account.makerFee,
                    current=amount,
                    placed_on=item['trade']['time']
                    ).setHigher())
                
                trade_names.append(item['trade']['instrument_code'])
                
            else:
                active = active_trades[trade_names.index(item['trade']['instrument_code'])]
                active.owned += float(item['trade']['amount']) * account.makerFee
                active.placed += float(item['trade']['amount']) * float(item['trade']['price']) * account.makerFee
                active.current += amount
                active.setHigher()
        
        for crypto in self.database.findActives(self.watching_cryptos, self.ignore_cryptos, self.watching_currencies):
            isFound = False

            for trade in active_trades:
                if crypto["_id"] == trade.instrument_code:
                    isFound = True

                    trade.stop_id = crypto["stop_id"]

                    if float(crypto["higher"]) > trade.current:
                        trade.higher = float(crypto["higher"])
                    
                    if bool(crypto["loaded"]) == True:
                        trade.loaded = True
                        trade.dailyDanger = int(crypto["dailyDanger"])
                        trade.weeklyDanger = int(crypto["weeklyDanger"])
                        trade.monthlyDanger = int(crypto["monthlyDanger"])
                        trade.precision = int(crypto["precision"])

            if isFound == False:
                self.database.putInHistory(crypto)

        for trade in active_trades:
            wait = 1
            client = None
            status_code = 0

            if trade.loaded == False:
                header = {
                    "Accept": "application/json"
                }

                client = web.Api(BitpandaPro.baseUrl + "/instruments", headers=header).send()
                status_code = client.getStatusCode()
                
            if status_code == 200:
                for item in client.getData():
                    pair = item["base"]["code"] + "_" + item["quote"]["code"]

                    if pair != trade.instrument_code:
                        continue

                    trade.precision = int(item["amount_precision"])

                wait += 1
            
            self.calculateDanger(trade, account, max_danger, min_recovered)
            self.database.putInActive(trade)
            time.sleep(wait)

        return active_trades
    
    def findProfitable(self, max_concurrent_trades, max_danger, min_recovered, account):
        header = {
            "Accept": "application/json"
        }

        actives = self.database.findActives(self.watching_cryptos, self.ignore_cryptos, self.watching_currencies)
        if len(actives) >= max_concurrent_trades:
            return []
        
        amount_to_return = max_concurrent_trades - len(actives)

        ignored_trades = []
        for trade in actives:
            ignored_trades.append(trade["_id"])
        
        client = web.Api(BitpandaPro.baseUrl + "/instruments", headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get available cryptos")
            return []

        available_cryptos = []
        for item in client.getData():
            if item["state"] != "ACTIVE":
                continue

            pair = item["base"]["code"] + "_" + item["quote"]["code"]

            if pair in ignored_trades:
                continue

            elif len(self.ignore_cryptos) != 0 and pair in self.ignore_cryptos:
                continue

            elif len(self.watching_cryptos) != 0 and pair not in self.watching_cryptos:
                continue
            
            elif len(self.watching_currencies) != 0 and item["quote"]["code"] not in self.watching_currencies:
                continue
            
            new = assets.Crypto(
                pair, 
                item["base"]["code"], 
                item["quote"]["code"], 
                0, 
                0, 
                0, 
                ""
            )
            new.precision = int(item["amount_precision"])

            available_cryptos.append(new)
        
        profitable_trades = []
        for crypto in available_cryptos:
            self.calculateDanger(crypto, account, max_danger, min_recovered)
            
            if crypto.danger != -100 and crypto.danger < int(max_danger / 2):
                profitable_trades.append(crypto)
            
            time.sleep(1)

        profitable_trades.sort(key=lambda x: x.danger)

        return profitable_trades[:amount_to_return]
    
    def incrementTrade(self, crypto, account, min_recovered):
        if crypto.stop_id != "":
            client = web.Api(BitpandaPro.baseUrl + "/account/orders/" + crypto.stop_id, headers=self.headers, method="DELETE").send()
                
            if client.getStatusCode() == 429:
                print("Too many requests at once")
                return False

            time.sleep(1)

            if client.getStatusCode() != 204:
                print("Error while trying to cancel stop order")
                return False
                
            crypto.stop_id = ""
            self.database.putInActive(crypto)

        body = {
            "instrument_code": crypto.instrument_code,
            "side": "SELL",
            "type": "STOP",
            "amount": self.truncate(crypto.owned * account.takerFee, crypto.precision),
            "price": str(round(crypto.higher * min_recovered / crypto.owned, 2)),
            "trigger_price": str(round((crypto.higher / crypto.owned) * account.makerFee * 0.99, 2))
        }
        
        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()
        
        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            client.send()
        
        time.sleep(1)

        if client.getStatusCode() != 201:
            print("Error while trying to create stop order")
        
        if client.getStatusCode() == 201:
            crypto.stop_id = client.getData()["order_id"]
        
        self.database.putInActive(crypto)

        return True
    
    def stopTrade(self, crypto, account):
        if crypto.stop_id != "":
            client = web.Api(BitpandaPro.baseUrl + "/account/orders/" + crypto.stop_id, headers=self.headers, method="DELETE").send()
            
            if client.getStatusCode() == 429:
                print("Too many requests at once")
                time.sleep(60)
                client.send()

            time.sleep(1)

            if client.getStatusCode() != 204:
                print("Error while trying to cancel stop order")
                return False
            
            crypto.stop_id = ""
            self.database.putInActive(crypto)
        
        body = {
            "instrument_code": crypto.instrument_code,
            "side": "SELL",
            "type": "MARKET",
            "amount": self.truncate(crypto.owned * account.takerFee, crypto.precision)
        }

        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            client.send()
        
        time.sleep(1)

        if client.getStatusCode() != 201:
            print("Error while trying to stop trade")
            return False
        
        crypto.current = self.getPrice(crypto.instrument_code) * crypto.owned
        crypto.setHigher()
        self.database.putInActive(crypto)

        return True
    
    def makeTrade(self, crypto, account):
        current_price = self.getPrice(crypto.instrument_code)
        amount = (account.available * 0.99 / crypto.danger) / current_price
        body = {
            "instrument_code": crypto.instrument_code,
            "side": "BUY",
            "type": "MARKET",
            "amount": self.truncate(amount, crypto.precision)
        }

        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()
        
        if client.getStatusCode() == 429:
            print("Too many requests at once")
            time.sleep(60)
            return False

        if client.getStatusCode() != 201:
            print("Error while trying to buy crypto")
            return False
        
        crypto.owned = amount
        crypto.placed = amount * current_price
        crypto.current = amount * current_price
        crypto.setHigher()

        return True
