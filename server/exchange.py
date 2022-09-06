from server import web
from server import db

import json
import time
import os

from datetime import time as timed
from datetime import datetime, timedelta, date

from data import account
from data import assets

class BitpandaPro:
    baseUrl = "https://api.exchange.bitpanda.com/public/v1"

    def __init__(self, api_key, database, watching_currencies, ignore_currencies):
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
            }
        
        self.database = database
        self.watching_currencies = watching_currencies
        self.ignore_currencies = ignore_currencies
    
    def truncate(self, number, precision):
        res = str(float(int(number * (10**precision))/(10**precision)))
        rounded = round(number, precision)

        if rounded < number:
            res = str(rounded)

        res_precision = len(res.split('.')[1])

        if res_precision == precision:
            return res
        
        for i in range(precision - res_precision):
            res += '0'
        
        return res
    
    def getCurrencyBalance(self, currency_code):
        amount = 0

        client = web.Api(BitpandaPro.baseUrl + '/account/balances', headers=self.headers).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            return None

        time.sleep(1)
        
        if client.getStatusCode() != 200:
            print("Error while trying to access balance data")
            return None
        
        for item in client.getData()['balances']:
            if item['currency_code'] == currency_code:
                amount += float(item['available'])

        return amount
    
    def getAccountFees(self):
        makerFee = 1
        takerFee = 1

        client = web.Api(BitpandaPro.baseUrl + '/account/fees', headers=self.headers).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            return None

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
        response = self.getCurrencyBalance('EUR')
        if response is None:
            print("No account could be found")
            return None

        new = account.Account(available=response)

        response = self.getAccountFees()
        if response is not None:
            res = json.loads(response)
            new.makerFee = res['makerFee']
            new.takerFee = res['takerFee']

        return new
    
    def actualizeAccount(self, account):
        fees = None
        
        response = self.getCurrencyBalance('EUR')
        if response is not None:
            account.available = response
        
        response = self.getAccountFees()
        if response is not None:
            fees = json.loads(response)
        
        if fees is not None:
            account.takerFee = fees['takerFee']
            account.makerFee = fees['makerFee']
    
    def getStats(self, crypto, fma_unit, mma_unit, sma_unit, period):
        header = {
            "Accept": "application/json"
        }

        today = datetime.utcnow()
        tz = today.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        tz2 = (today - timedelta(minutes=sma_unit * period)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        client = web.Api(BitpandaPro.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=MINUTES&period=" + str(period) + "&from=" + tz2 + "&to=" + tz, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get price tickers")
            return None
        
        time.sleep(1)
        
        length = len(client.getData())
        if length < 2:
            return None
        
        values = []

        for i in range(1, length + 1):
            if length - i - 1 < 0:
                break
            
            previous_time = datetime.strptime(client.getData()[length - i - 1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            current_time = datetime.strptime(client.getData()[length - i]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            
            while previous_time.strftime("%Y-%m-%dT%H:%M") != current_time.strftime("%Y-%m-%dT%H:%M"):
                values.append({
                    'open': float(client.getData()[length - i]['open']),
                    'close': float(client.getData()[length - i]['close'])
                })
                current_time = current_time - timedelta(minutes=5)
        
        missing = sma_unit - len(values)
        if missing > 0:
            last_item = values[len(values) - 1]
            
            for i in range(missing):
                values.append(last_item)
        
        fma_mean = 0
        for i in range(fma_unit):
            fma_mean += values[i]['close'] * (fma_unit - i)
        
        fma_mean = fma_mean / (fma_unit * (fma_unit + 1) / 2)

        mma_mean = 0
        for i in range(mma_unit):
            mma_mean += values[i]['close'] * (mma_unit - i)
        
        mma_mean = mma_mean / (mma_unit * (mma_unit + 1) / 2)
        
        sma_mean = 0
        avg_gain = 0
        avg_loss = 0
        for i in range(sma_unit):
            open_price = values[i]['open']
            close_price = values[i]['close']

            sma_mean += close_price * (sma_unit - i)

            if close_price - open_price > 0:
                avg_gain += (close_price - open_price) * (sma_unit - i)
                continue

            avg_loss += abs(close_price - open_price) * (sma_unit - i)
        
        sma_mean = sma_mean / (sma_unit * (sma_unit + 1) / 2)
        avg_gain = avg_gain / (sma_unit * (sma_unit + 1) / 2)
        avg_loss = avg_loss / (sma_unit * (sma_unit + 1) / 2)

        crypto.fma = fma_mean
        crypto.mma = mma_mean
        crypto.sma = sma_mean

        if avg_loss == 0:
            crypto.rsi = 100
        
        else:
            crypto.rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))

        tz2 = (today - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        client = web.Api(BitpandaPro.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=HOURS&period=1&from=" + tz2 + "&to=" + tz, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get price tickers")
            return None
        
        time.sleep(1)

        length = len(client.getData())

        if length == 0:
            return None
        
        crypto.hourlyVolume = float(client.getData()[length - 1]['volume'])

        for item in client.getData():
            crypto.dailyVolume += float(item['volume'])

        return True
    
    def getPrice(self, instrument_code):
        header = {
            "Accept": "application/json"
        }

        client = web.Api(BitpandaPro.baseUrl + "/market-ticker/" + instrument_code, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get market tickers")
            return None

        return float(client.getData()['last_price'])
    
    def getAllActiveTrades(self):
        active_trades = []

        client = web.Api(BitpandaPro.baseUrl + "/account/trades", headers=self.headers).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            return []
        
        time.sleep(1)

        if client.getStatusCode() != 200:
            print("Error while trying to access account active trades")
            return []

        trades = client.getData()['trade_history']

        trade_names = []
        ignored_trades = []
        for item in trades:
            if len(self.ignore_currencies) != 0 and item['trade']['instrument_code'] in self.ignore_currencies:
                continue

            elif len(self.watching_currencies) != 0 and item['trade']['instrument_code'] not in self.watching_currencies:
                continue
            
            elif item['trade']['instrument_code'] in ignored_trades:
                continue

            elif item['trade']['side'] == "SELL":
                ignored_trades.append(item['trade']['instrument_code'])
                continue

            amount = (float(item['trade']['amount']) - float(item['fee']['fee_amount'])) * self.getPrice(item['trade']['instrument_code'])

            if item['trade']['instrument_code'] not in trade_names:
                active_trades.append(assets.Crypto(
                    instrument_code=item['trade']['instrument_code'],
                    base=item['trade']['instrument_code'].split('_')[0],
                    currency=item['trade']['instrument_code'].split('_')[1],
                    owned=float(item['trade']['amount']) - float(item['fee']['fee_amount']),
                    placed=float(item['trade']['amount']) * float(item['trade']['price']),
                    current=amount,
                    placed_on=item['trade']['time']
                    ).setHigher())
                
                trade_names.append(item['trade']['instrument_code'])
                
            else:
                active = active_trades[trade_names.index(item['trade']['instrument_code'])]
                active.owned += float(item['trade']['amount']) - float(item['fee']['fee_amount'])
                active.placed += float(item['trade']['amount']) * float(item['trade']['price'])
                active.current += amount
                active.setHigher()
        
        for crypto in self.database.findActives(self.watching_currencies, self.ignore_currencies):
            isFound = False

            for trade in active_trades:
                if crypto["_id"] == trade.instrument_code:
                    isFound = True

                    trade.stop_id = crypto["stop_id"]
                    trade.market_id = crypto["market_id"]
                    trade.failed = bool(crypto["failed"])
                    trade.alerted = bool(crypto["alerted"])
                    trade.precision = int(crypto["precision"])

                    if float(crypto["higher"]) > trade.current:
                        trade.higher = float(crypto["higher"])

            if isFound == True:
                continue
            
            order_id = ""

            if crypto['stop_id'] != "":
                order_id = crypto['stop_id']
            
            elif crypto['market_id'] != "":
                order_id = crypto['market_id']
            
            if order_id == "":
                self.database.putInHistory(crypto)
                continue
            
            client = web.Api(BitpandaPro.baseUrl + "/account/orders/" + order_id, headers=self.headers).send()

            time.sleep(1)

            if client.getStatusCode() != 200:
                self.database.putInHistory(crypto)
                continue

            if client.getData()['order']['status'] != "FILLED_FULLY":
                self.database.putInHistory(crypto)
                continue
            
            crypto['current'] = float(crypto['owned']) * float(client.getData()['order']['price'])

            self.database.putInHistory(crypto)

        for trade in active_trades:
            header = {
                "Accept": "application/json"
            }

            status_code = 0
            if trade.precision == 0:
                client = web.Api(BitpandaPro.baseUrl + "/instruments", headers=header).send()
                status_code = client.getStatusCode()
                time.sleep(1)
                
            if status_code == 200:
                for item in client.getData():
                    pair = item["base"]["code"] + "_" + item["quote"]["code"]

                    if pair != trade.instrument_code:
                        continue
                    
                    trade.precision = int(item["amount_precision"])
            
            self.database.putInActive(trade)

        return active_trades
    
    def findProfitable(self, max_concurrent_currencies, fma_unit, mma_unit, sma_unit, candlesticks_period, max_danger, min_recovered, account, wait_time):
        header = {
            "Accept": "application/json"
        }

        actives = self.database.findActives(self.watching_currencies, self.ignore_currencies)
        if len(actives) >= max_concurrent_currencies:
            return []
        
        amount_to_return = max_concurrent_currencies - len(actives)

        ignored_trades = []
        for trade in actives:
            ignored_trades.append(trade["_id"])
        
        client = web.Api(BitpandaPro.baseUrl + "/instruments", headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get available cryptos")
            return []
        
        time.sleep(1)

        available_cryptos = []
        for item in client.getData():
            if item["state"] != "ACTIVE":
                continue

            pair = item["base"]["code"] + "_" + item["quote"]["code"]

            if pair in ignored_trades:
                continue

            elif len(self.ignore_currencies) != 0 and pair in self.ignore_currencies:
                continue

            elif len(self.watching_currencies) != 0 and pair not in self.watching_currencies:
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
            if crypto.precision == 0:
                continue

            res = self.getStats(crypto, fma_unit, mma_unit, sma_unit, candlesticks_period)
            if res is None:
                continue

            if self.database.getLastDanger(crypto, min_recovered, max_danger, wait_time) == 0:
                crypto.danger += 1
            
            if account.available >= crypto.hourlyVolume:
                crypto.danger += max_danger
            
            if account.available * 10 >= crypto.hourlyVolume / 2:
                crypto.danger += 2

            if account.available * 10 >= crypto.hourlyVolume:
                crypto.danger += max_danger
            
            if account.available * 20 < crypto.hourlyVolume / 2:
                crypto.danger -= 2
            
            if crypto.hourlyVolume < crypto.dailyVolume / 24:
                crypto.danger += 2
            
            if datetime.utcnow().time() >= timed(11,30):
                crypto.danger += 2
            
            if date.today().weekday() == 4:
                crypto.danger += 1
            
            elif date.today().weekday() >= 5:
                crypto.danger += 2
            
            if crypto.danger < max_danger:
                profitable_trades.append(crypto)

        profitable_trades.sort(key=lambda x: x.danger)

        return profitable_trades[:amount_to_return]
    
    def incrementTrade(self, crypto, min_recovered):
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
            "amount": self.truncate(crypto.owned, crypto.precision),
            "price": self.truncate(crypto.higher * min_recovered / crypto.owned, 2),
            "trigger_price": self.truncate(crypto.higher * min_recovered / crypto.owned, 2)
        }
        
        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()
        
        if client.getStatusCode() == 429:
            print("Too many requests at once")
            return False
        
        time.sleep(1)

        if client.getStatusCode() != 201:
            print("Error while trying to create stop order")
        
        if client.getStatusCode() == 201:
            crypto.stop_id = client.getData()["order_id"]
        
        self.database.putInActive(crypto)

        return True
    
    def stopTrade(self, crypto):
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
            "type": "MARKET",
            "amount": self.truncate(crypto.owned, crypto.precision)
        }

        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()

        if client.getStatusCode() == 429:
            print("Too many requests at once")
            return False
        
        time.sleep(1)

        if client.getStatusCode() != 201:
            print("Error while trying to stop trade")
            return False
        
        crypto.market_id = client.getData()['order_id']

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
            return False

        if client.getStatusCode() != 201:
            print("Error while trying to buy crypto")
            return False
        
        crypto.owned = amount
        crypto.placed = amount * current_price
        crypto.current = amount * current_price
        crypto.setHigher()

        return True
