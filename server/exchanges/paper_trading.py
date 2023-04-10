from server import web
from server import db

import time

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from data import account
from data import assets

class Exchange:
    baseUrl = "https://api.exchange.bitpanda.com/public/v1"

    def __init__(self, init_capital):
        self.init_capital = init_capital
        self.header = {
            "Accept": "application/json"
        }
    
    def getAccount(self):
        new = account.Account(available=self.init_capital)
        new.makerFee = 0.9985
        new.takerFee = 0.9975

        return new
    
    def actualizeAccount(self, account):
        return True
    
    def getStats(self, crypto, parameters, full=False):
        frame = parameters.period + 1
        if frame < parameters.sma_unit + 10:
            frame = parameters.sma_unit + 10

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

        status_code, data = web.Api(Exchange.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=" + parameters.candlesticks_timeframe + "&period=" + str(parameters.candlesticks_period) + "&from=" + tz2 + "&to=" + tz, headers=self.header).send()
        time.sleep(1)

        if status_code != 200:
            print("Error while trying to get price tickers")
            return None
        
        length = len(data)
        if length < 3:
            return None
        
        values = []

        last_time = datetime.strptime(data[length - 1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        i = 0
        while last_time < today.replace(second=59):
            values.append(data[length - 1])
            values[i]['volume'] = 0.0

            last_time = last_time + delta
            i += 1

            if i >= frame:
                return None

        for i in range(1, length + 1):
            if length - i - 1 < 0:
                break
            
            previous_time = datetime.strptime(data[length - i - 1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            current_time = datetime.strptime(data[length - i]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")

            added = False
            
            while previous_time < current_time:
                values.append(data[length - i])
                current_time = current_time - delta

                if added:
                    values[len(values) - 1]['volume'] = 0.0
                
                added = True
        
        missing = frame - len(values)

        if missing > 0:
            last_item = values[len(values) - 1]
            last_item['volume'] = 0.0
            
            for i in range(missing):
                values.append(last_item)
        
        fma_mean = 0
        for i in range(parameters.fma_unit, parameters.fma_unit + 10):
            fma_mean += float(values[i]['close'])
        
        fma_mean = fma_mean / 10

        for i in range(1, parameters.fma_unit + 1):
            fma_mean = ((2 / (parameters.fma_unit + 1)) * float(values[parameters.fma_unit - i]['close'])) + ((1 - (2 / (parameters.fma_unit + 1))) * fma_mean)

        sma_mean = 0
        for i in range(parameters.sma_unit, parameters.sma_unit + 10):
            sma_mean += float(values[i]['close'])
        
        sma_mean = sma_mean / 10

        for i in range(1, parameters.sma_unit + 1):
            sma_mean = ((2 / (parameters.sma_unit + 1)) * float(values[parameters.sma_unit - i]['close'])) + ((1 - (2 / (parameters.sma_unit + 1))) * sma_mean)

        avg_gain = 0
        avg_loss = 0
        for i in range(parameters.period):
            current_price = float(values[i]['close'])
            last_price = float(values[i + 1]['close'])
            
            if current_price == last_price:
                continue
            
            elif current_price - last_price > 0:
                avg_gain += abs(current_price - last_price)
                continue

            avg_loss += abs(current_price - last_price)
        
        avg_gain = avg_gain / parameters.period
        avg_loss = avg_loss / parameters.period

        crypto.fma = round(fma_mean, crypto.precision)
        crypto.sma = round(sma_mean, crypto.precision)

        if avg_loss == 0:
            crypto.rsi = 100
        
        else:
            crypto.rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
        
        adl = 0.0
        for i in range(1, parameters.period + 1):
            close = float(values[parameters.period - i]['close'])
            high = float(values[parameters.period - i]['high'])
            low = float(values[parameters.period - i]['low'])
            volume = float(values[parameters.period - i]['volume'])

            if high == low:
                continue

            adl += ((((close - low) - (high - close)) / (high - low)) * volume) * i
        
        crypto.adl = adl / parameters.period
        
        if full == False:
            return True
        
        tz2 = (today - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        status_code, data = web.Api(Exchange.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=HOURS&period=1&from=" + tz2 + "&to=" + tz, headers=self.header).send()
        time.sleep(1)

        if status_code != 200:
            print("Error while trying to get price tickers")
            return None

        length = len(data)

        if length == 0:
            return None
        
        crypto.hourlyVolume = float(data[length - 1]['volume'])

        for item in data:
            crypto.dailyVolume += float(item['volume'])

        return True
    
    def getPrice(self, instrument_code):
        status_code, data = web.Api(Exchange.baseUrl + "/market-ticker/" + instrument_code, headers=self.header).send()

        if status_code != 200:
            print("Error while trying to get market tickers")
            return 0

        return float(data['last_price'])
    
    def getAllActiveAssets(self, parameters):
        active_assets = []

        for asset in parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies):
            crypto = assets.Crypto(
                asset["_id"],
                "",
                "",
                float(asset["owned"]),
                float(asset["placed"]),
                float(asset["current"]),
                "").setHigher()

            crypto.precision = int(asset["precision"])
            crypto.higher = float(asset["higher"])

            self.getStats(crypto, parameters)

            crypto.last_price = self.getPrice(crypto.instrument_code)

            crypto.current = crypto.owned * crypto.last_price

            if crypto.current > crypto.higher:
                crypto.higher = crypto.current

            parameters.database.putInActive(crypto)

            active_assets.append(crypto)
        
        return active_assets
    
    def findProfitable(self, parameters):
        actives = parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies)
        ignored_assets = []
        for asset in actives:
            ignored_assets.append(asset["_id"])
        
        status_code, data = web.Api(Exchange.baseUrl + "/instruments", headers=self.header).send()
        time.sleep(1)

        if status_code != 200:
            print("Error while trying to get available cryptos")
            return []

        available_cryptos = []
        for item in data:
            if item["state"] != "ACTIVE":
                continue

            pair = item["base"]["code"] + "_" + item["quote"]["code"]

            if pair in ignored_assets:
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
        
        profitable_assets = []
        for crypto in available_cryptos:
            if crypto.precision == 0:
                continue

            if parameters.database.getLastPlaced(crypto, parameters.wait_time):
                continue

            res = self.getStats(crypto, parameters, full=True)
            if res is None:
                continue

            if parameters.account.available * 0.99 * (1 - (crypto.rsi / 100)) >= crypto.hourlyVolume:
                continue
            
            if parameters.account.available * 0.99 * (1 - (crypto.rsi / 100)) >= crypto.hourlyVolume * 0.25:
                crypto.danger += 1
            
            if parameters.account.available * 0.99 * (1 - (crypto.rsi / 100)) >= crypto.hourlyVolume * 0.5:
                crypto.danger += 2
            
            if parameters.account.available * 0.99 * (1 - (crypto.rsi / 100)) >= crypto.hourlyVolume * 0.75:
                crypto.danger += 3
            
            if crypto.hourlyVolume < crypto.dailyVolume / 24:
                crypto.danger += 2
            
            if crypto.danger > parameters.max_danger:
                continue

            crypto.last_price = round(self.getPrice(crypto.instrument_code), crypto.precision)
            if crypto.last_price == 0:
                continue
            
            if crypto.danger > parameters.max_danger:
                continue
            
            profitable_assets.append(crypto)

        profitable_assets.sort(key=lambda x: x.dailyVolume, reverse=True)
        profitable_assets.sort(key=lambda x: x.danger)

        return profitable_assets
    
    def stopLossOrder(self, crypto, parameters):
        return True
    
    def sellingMarketOrder(self, crypto, parameters):
        parameters.database.putInHistory(crypto)
        parameters.account.available += crypto.current * parameters.account.takerFee

        return True
    
    def buyingMarketOrder(self, crypto, parameters):
        amount = ((parameters.account.available / crypto.danger) * 0.99 * (crypto.rsi / 100)) / crypto.last_price

        crypto.placed = amount * crypto.last_price
        
        amount *= parameters.account.makerFee

        crypto.owned = amount
        crypto.current = amount * crypto.last_price
        crypto.setHigher()

        parameters.database.putInActive(crypto)

        return True
