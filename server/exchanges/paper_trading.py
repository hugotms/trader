from server import web
from server import db

import time
import pandas

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
        if frame < parameters.macd_slow + 10:
            frame = parameters.macd_slow + 10

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
        
        dataframe = pandas.DataFrame(data=data)
        dataframe = dataframe.loc[:, ["time", "high", "low", "close", "volume"]]
        dataframe.rename(columns={"time": "Date", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
        dataframe.sort_values("Date", inplace=True, ascending=True)

        modified = True
        while modified:
            modified = False

            for index, row in dataframe.iterrows():
                current_time = datetime.strptime(row["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")

                if index == 0 and current_time > datetime.strptime(tz2, "%Y-%m-%dT%H:%M:%S.%fZ"):
                    modified = True
                    new_row = [datetime.strftime(current_time - delta, "%Y-%m-%dT%H:%M:%S.%fZ"), row["High"], row["Low"], row["Close"], 0.0]
                    dataframe.loc[-1] = new_row
                    break

                elif index == 0:
                    continue

                last_time = datetime.strptime(dataframe.iloc[index - 1]["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")
                
                if last_time + delta >= current_time:
                    continue

                modified = True
                last_time += delta
                new_row = [datetime.strftime(last_time, "%Y-%m-%dT%H:%M:%S.%fZ"), None, None, None, None]
                dataframe.loc[index - 0.5] = new_row
                break
            
            dataframe = dataframe.sort_index().reset_index(drop=True)

        dataframe[["High", "Low", "Close"]] = dataframe[["High", "Low", "Close"]].fillna(method='ffill')
        dataframe["Volume"].fillna(value=0.0, inplace=True)
        
        length = dataframe.shape[0]
        last_time = datetime.strptime(dataframe.iloc[-1]["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")
            
        while last_time + delta < today:
            row = dataframe.iloc[-1]
            last_time = datetime.strptime(row.Date, "%Y-%m-%dT%H:%M:%S.%fZ")
            dataframe.loc[length] = [datetime.strftime(last_time + delta, "%Y-%m-%dT%H:%M:%S.%fZ"), row.High, row.Low, row.Close, 0.0]
            length += 1
        
        dataframe[["High", "Low", "Close", "Volume"]] = dataframe[["High", "Low", "Close", "Volume"]].astype("float64")
        dataframe["FMA"] = dataframe.iloc[:]["Close"].ewm(span=parameters.macd_fast, adjust=False).mean()
        dataframe["SMA"] = dataframe.iloc[:]["Close"].ewm(span=parameters.macd_slow, adjust=False).mean()
        dataframe["MACD"] = dataframe["FMA"] - dataframe["SMA"]
        dataframe["Signal"] = dataframe.iloc[:]["MACD"].ewm(span=parameters.macd_smooth, adjust=False).mean()

        crypto.macd = float(dataframe.iloc[-1]["MACD"])
        crypto.signal = float(dataframe.iloc[-1]["Signal"])

        dataframe["Highest"] = dataframe["High"].rolling(parameters.period).max()
        dataframe["Lowest"] = dataframe["Low"].rolling(parameters.period).min()
        dataframe["%K"] = ((dataframe["Close"] - dataframe["Lowest"]) * 100) / (dataframe["Highest"] - dataframe["Lowest"])
        dataframe["%D"] = dataframe["%K"].rolling(3).mean()

        crypto.stochastic_k = float(dataframe.iloc[-1]["%K"])
        crypto.stochastic_d = float(dataframe.iloc[-1]["%D"])

        dataframe = dataframe.sort_values("Date", ascending=False)

        avg_gain = 0
        avg_loss = 0
        for i in range(parameters.period):
            current_price = float(dataframe.iloc[i]["Close"])
            last_price = float(dataframe.iloc[i + 1]["Close"])
            
            if current_price == last_price:
                continue
            
            elif current_price - last_price > 0:
                avg_gain += abs(current_price - last_price)
                continue

            avg_loss += abs(current_price - last_price)
        
        avg_gain = avg_gain / parameters.period
        avg_loss = avg_loss / parameters.period

        if avg_loss == 0:
            crypto.rsi = 100
        
        else:
            crypto.rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
        
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

            if parameters.account.available * 0.99 >= crypto.hourlyVolume:
                continue
            
            if parameters.account.available * 0.99 >= crypto.hourlyVolume * 0.25:
                crypto.danger += 1
            
            if parameters.account.available * 0.99 >= crypto.hourlyVolume * 0.5:
                crypto.danger += 2
            
            if parameters.account.available * 0.99 >= crypto.hourlyVolume * 0.75:
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
        amount = ((parameters.account.available / crypto.danger) * 0.99) / crypto.last_price

        crypto.placed = amount * crypto.last_price
        
        amount *= parameters.account.makerFee

        crypto.owned = amount
        crypto.current = amount * crypto.last_price
        crypto.setHigher()

        parameters.database.putInActive(crypto)

        return True
