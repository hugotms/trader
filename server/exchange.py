from server import web
from server import db

import json
import time
import os

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from data import account
from data import assets

class BitpandaPro:
    baseUrl = "https://api.exchange.bitpanda.com/public/v1"

    def __init__(self, api_key):
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
            }
    
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
    
    def getStats(self, crypto, parameters, full=False):
        frame = parameters.rsi_period + 1
        if frame < parameters.sma_unit + 10:
            frame = parameters.sma_unit + 10

        header = {
            "Accept": "application/json"
        }

        today = datetime.utcnow()
        tz = today.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        tz2 = None
        delta = None

        if parameters.candlesticks_timeframe == 'MONTHS':
            tz2 = (today - relativedelta(months=frame * parameters.candlesticks_period)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            delta = relativedelta(months=parameters.candlesticks_period)
        
        elif parameters.candlesticks_timeframe == 'WEEKS':
            tz2 = (today - relativedelta(weeks=frame * parameters.candlesticks_period)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            delta = relativedelta(weeks=parameters.candlesticks_period)
        
        elif parameters.candlesticks_timeframe == 'DAYS':
            tz2 = (today - timedelta(days=frame * parameters.candlesticks_period)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            delta = timedelta(days=parameters.candlesticks_period)
        
        elif parameters.candlesticks_timeframe == 'HOURS':
            tz2 = (today - timedelta(hours=frame * parameters.candlesticks_period)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            delta = timedelta(hours=parameters.candlesticks_period)
        
        elif parameters.candlesticks_timeframe == 'MINUTES':
            tz2 = (today - timedelta(minutes=frame * parameters.candlesticks_period)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            delta = timedelta(minutes=parameters.candlesticks_period)

        client = web.Api(BitpandaPro.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=" + parameters.candlesticks_timeframe + "&period=" + str(parameters.candlesticks_period) + "&from=" + tz2 + "&to=" + tz, headers=header).send()

        if client.getStatusCode() != 200:
            print("Error while trying to get price tickers")
            return None
        
        time.sleep(1)
        
        length = len(client.getData())
        if length < 3:
            return None
        
        values = []

        last_time = datetime.strptime(client.getData()[length - 1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        i = 0
        while last_time < today.replace(second=59):
            values.append(float(client.getData()[length - 1]['close']))

            last_time = last_time + delta
            i += 1

            if i >= frame:
                return None

        for i in range(1, length + 1):
            if length - i - 1 < 0:
                break
            
            previous_time = datetime.strptime(client.getData()[length - i - 1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            current_time = datetime.strptime(client.getData()[length - i]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            
            while previous_time < current_time:
                values.append(float(client.getData()[length - i]['close']))
                current_time = current_time - delta
        
        missing = frame - len(values)
        if missing >= frame / 2:
            return None

        if missing > 0:
            last_item = values[len(values) - 1]
            
            for i in range(missing):
                values.append(last_item)
        
        length = len(values)
        if length < frame:
            return None
        
        fma_mean = sum(values[parameters.fma_unit:(parameters.fma_unit + 10)]) / 10
        for i in range(1, parameters.fma_unit + 1):
            fma_mean = ((2 / (parameters.fma_unit + 1)) * values[parameters.fma_unit - i]) + ((1 - (2 / (parameters.fma_unit + 1))) * fma_mean)
        
        mma_mean = sum(values[parameters.mma_unit:(parameters.mma_unit + 10)]) / 10
        for i in range(1, parameters.mma_unit + 1):
            mma_mean = ((2 / (parameters.mma_unit + 1)) * values[parameters.mma_unit - i]) + ((1 - (2 / (parameters.mma_unit + 1))) * mma_mean)

        sma_mean = sum(values[parameters.sma_unit:(parameters.sma_unit + 10)]) / 10
        for i in range(1, parameters.sma_unit + 1):
            sma_mean = ((2 / (parameters.sma_unit + 1)) * values[parameters.sma_unit - i]) + ((1 - (2 / (parameters.sma_unit + 1))) * sma_mean)

        avg_gain = 0
        avg_loss = 0
        same_values = 0
        for i in range(parameters.rsi_period):
            current_price = values[i]
            last_price = values[i + 1]

            if same_values >= parameters.rsi_period / 2:
                return None
            
            if current_price == last_price:
                same_values += 1
                continue
            
            if current_price - last_price > 0:
                avg_gain += abs(current_price - last_price)
                continue

            avg_loss += abs(current_price - last_price)
        
        avg_gain = avg_gain / parameters.rsi_period
        avg_loss = avg_loss / parameters.rsi_period

        crypto.fma = round(fma_mean, crypto.precision)
        crypto.mma = round(mma_mean, crypto.precision)
        crypto.sma = round(sma_mean, crypto.precision)

        if avg_loss == 0:
            crypto.rsi = 100
        
        else:
            crypto.rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
        
        if full == False:
            return True
        
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
            return 0

        return float(client.getData()['last_price'])
    
    def getAllActiveTrades(self, parameters):
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
            if len(parameters.ignore_currencies) != 0 and item['trade']['instrument_code'] in parameters.ignore_currencies:
                continue

            elif len(parameters.watching_currencies) != 0 and item['trade']['instrument_code'] not in parameters.watching_currencies:
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
        
        for crypto in parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies):
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
            
            if crypto['market_id'] != "":
                order_id = crypto['market_id']
            
            asset = assets.Crypto(
                crypto["_id"],
                crypto["base"],
                crypto["currency"],
                float(crypto["owned"]),
                float(crypto["placed"]),
                float(crypto['current']),
                crypto["placed_on"]
            )

            asset.higher = float(crypto["higher"])
            
            if order_id == "":
                parameters.database.putInHistory(asset)
                continue
            
            client = web.Api(BitpandaPro.baseUrl + "/account/orders/" + order_id, headers=self.headers).send()

            time.sleep(1)

            if client.getStatusCode() != 200:
                parameters.database.putInHistory(asset)
                continue

            if client.getData()['order']['status'] not in ["FILLED_FULLY", "CLOSED"]:
                parameters.database.putInHistory(asset)
                continue
            
            current_price = asset.owned * float(client.getData()['order']['price'])
            if current_price == 0.0:
                parameters.database.putInHistory(asset)
                continue
            
            asset.current = current_price
            if asset.current > asset.higher:
                asset.higher = asset.current

            parameters.database.putInHistory(asset)

        for trade in active_trades:
            self.getStats(trade, parameters)

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
            
            parameters.database.putInActive(trade)

        return active_trades
    
    def findProfitable(self, parameters, account):
        header = {
            "Accept": "application/json"
        }

        actives = parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies)
        if len(actives) >= parameters.max_concurrent_currencies:
            return []
        
        amount_to_return = parameters.max_concurrent_currencies - len(actives)

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

            elif len(parameters.ignore_currencies) != 0 and pair in parameters.ignore_currencies:
                continue

            elif len(parameters.watching_currencies) != 0 and pair not in parameters.watching_currencies:
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

            parameters.database.getLastDanger(crypto, parameters.min_recovered, parameters.max_danger, parameters.wait_time)
            if crypto.danger >= parameters.max_danger:
                continue

            res = self.getStats(crypto, parameters, full=True)
            if res is None:
                continue

            crypto.last_price = round(self.getPrice(crypto.instrument_code), crypto.precision)
            if crypto.last_price == 0:
                continue

            if account.available >= crypto.hourlyVolume:
                crypto.danger += parameters.max_danger
            
            if account.available * 10 >= crypto.hourlyVolume / 2:
                crypto.danger += 2

            if account.available * 10 >= crypto.hourlyVolume:
                crypto.danger += parameters.max_danger
            
            if crypto.hourlyVolume < crypto.dailyVolume / 24:
                crypto.danger += 2
            
            if crypto.danger <= parameters.max_danger:
                profitable_trades.append(crypto)

        profitable_trades.sort(key=lambda x: x.dailyVolume, reverse=True)
        profitable_trades.sort(key=lambda x: x.danger)

        return profitable_trades[:amount_to_return]
    
    def incrementTrade(self, crypto, parameters):
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
            parameters.database.putInActive(crypto)

        body = {
            "instrument_code": crypto.instrument_code,
            "side": "SELL",
            "type": "STOP",
            "amount": self.truncate(crypto.owned, crypto.precision),
            "price": self.truncate(crypto.higher * parameters.security_min_recovered / crypto.owned, 2),
            "trigger_price": self.truncate(crypto.higher * parameters.security_min_recovered / crypto.owned, 2)
        }
        
        client = web.Api(BitpandaPro.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()
        
        if client.getStatusCode() == 429:
            print("Too many requests at once")
            return False
        
        time.sleep(1)

        if client.getStatusCode() != 201:
            crypto.failed == True
            print("Error while trying to create stop order")
            return False
        
        crypto.stop_id = client.getData()["order_id"]
        
        parameters.database.putInActive(crypto)

        return True
    
    def stopTrade(self, crypto, parameters):
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
            parameters.database.putInActive(crypto)
        
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
        if current_price == 0:
            return False
        
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
