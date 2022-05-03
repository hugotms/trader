from server import web
from server import db

import json
import time
import os

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from data import account
from data import assets

class BitpandaPro:
    baseUrl = "https://api.exchange.bitpanda.com/public/v1"

    def __init__(self):
        self.database = db.Mongo().new()

    def new(self):
        if self.database is None:
            return None
        
        if os.getenv('EXCHANGE_API_KEY') is None:
            print("Required API key was not set")
            return None
        
        self.watching_cryptos = []
        if os.getenv('WATCHING_CRYPTOS') is not None:
            self.watching_cryptos = os.getenv('WATCHING_CRYPTOS').split(',')
        
        self.watching_currencies = []
        if os.getenv('WATCHING_CURRENCIES') is not None:
            self.watching_currencies = os.getenv('WATCHING_CURRENCIES').split(',')
        
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

        new = account.Account(id=res['account_id'], available=res['amount'])

        response = self.getAccountFees()
        if response is not None:
            res = json.loads(response)
            new.makerFee = res['makerFee']
            new.takerFee = res['takerFee']
        
        response = self.database.getPastPerformance((datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), self.watching_cryptos, self.watching_currencies)
        if response is not None:
            response = json.loads(response)
            new.dailyProfit = float(response["profit"])
            new.dailyLoss = float(response["loss"])
        
        response = self.database.getPastPerformance((datetime.utcnow() - timedelta(weeks=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), self.watching_cryptos, self.watching_currencies)
        if response is not None:
            response = json.loads(response)
            new.weeklyProfit = float(response["profit"])
            new.weeklyLoss = float(response["loss"])
        
        response = self.database.getPastPerformance((datetime.utcnow() - relativedelta(months=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), self.watching_cryptos, self.watching_currencies)
        if response is not None:
            response = json.loads(response)
            new.monthlyProfit = float(response["profit"])
            new.monthlyLoss = float(response["loss"])

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
            print("No prices data were found for time unit " + time_unit)
            return None

        return json.dumps({
                "open": float(client.getData()[0]['open']),
                "close": float(client.getData()[0]['close'])
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
    
    def calculateDanger(self, crypto, max_danger):
        danger = 0

        if int(self.database.getLastDanger(crypto)) > max_danger % 2:
            danger += 1

        res = self.getPrices(crypto, time_unit='MINUTES')
        if res is None:
            crypto.danger += danger
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
            crypto.danger += danger
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
        
        res = self.getPrices(crypto, time_unit='DAYS')
        if res is None:
            crypto.danger += danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
            return self
        res = json.loads(res)

        if res['open'] > res['close']:
            crypto.dailyDanger += 2
        
        variation = abs((res['open'] - res['close']) / res['close'])
        
        if variation > 0.1:
            crypto.dailyDanger += 1
        elif variation > 0.12:
            crypto.dailyDanger += 2

        res = self.getPrices(crypto, time_unit='WEEKS')
        if res is None:
            crypto.danger += danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
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
            crypto.danger += danger + crypto.dailyDanger + crypto.weeklyDanger + crypto.monthlyDanger
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


    def getAllActiveTrades(self, account, max_danger):
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
            if (
                (len(self.watching_cryptos) == 0 and len(self.watching_currencies) == 0) 
                or (len(self.watching_cryptos) != 0 and item['trade']['instrument_code'] in self.watching_cryptos)
                or (len(self.watching_currencies) != 0 and item['trade']['instrument_code'].split("_")[1] in self.watching_currencies)
                ):
                if item['trade']['side'] == "SELL":
                    ignored_trades.append(item['trade']['instrument_code'])

                elif item['trade']['instrument_code'] not in ignored_trades:
                    amount = float(item['trade']['amount']) * self.getPrice(item['trade']['instrument_code']) * account.makerFee

                    if item['trade']['instrument_code'] not in trade_names:
                        active_trades.append(assets.Crypto(
                            instrument_code=item['trade']['instrument_code'],
                            base=item['trade']['instrument_code'].split('_')[0],
                            currency=item['trade']['instrument_code'].split('_')[1],
                            owned=float(item['trade']['amount']) * account.makerFee,
                            placed=float(item['trade']['amount']) * float(item['trade']['price']) * account.makerFee,
                            current=amount
                            ).setHigher())
                        
                        trade_names.append(item['trade']['instrument_code'])
                        
                    else:
                        for active in active_trades:
                            if active.instrument_code == item['trade']['instrument_code']:
                                active.owned += float(item['trade']['amount']) * account.makerFee
                                active.placed += float(item['trade']['amount']) * float(item['trade']['price']) * account.makerFee
                                active.current += amount
                                active.setHigher()
                                break
        
        for crypto in self.database.findActives(self.watching_cryptos, self.watching_currencies):
            isFound = False

            for trade in active_trades:
                if crypto["_id"] == trade.instrument_code:
                    isFound = True

                    if float(crypto["higher"]) > trade.current:
                        trade.higher = float(crypto["higher"])
                    
                    if bool(crypto["loaded"]) == True:
                        trade.loaded = True
                        trade.dailyDanger = int(crypto["dailyDanger"])
                        trade.weeklyDanger = int(crypto["weeklyDanger"])
                        trade.monthlyDanger = int(crypto["monthlyDanger"])

            if isFound == False:
                self.database.putInHistory(crypto)

        for trade in active_trades:
            self.calculateDanger(trade, max_danger)
            self.database.putInActive(trade)

        return active_trades
    
    def stopTrade(self, crypto, account):
        percentage = (1 - ((0.01 * crypto.owned / crypto.current) / crypto.owned)) * account.takerFee * account.makerFee
        body = {
            "instrument_code": crypto.instrument_code,
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
        
        crypto.current = self.getPrice(crypto.instrument_code) * crypto.owned
        crypto.setHigher()
        self.database.putInActive(crypto)

        return percentage
    