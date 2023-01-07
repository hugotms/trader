from server import db

import pandas

from data import account
from data import assets

class Exchange:

    def __init__(self, init_capital, filename, frame, watching_currencies, ignore_currencies):
        self.init_capital = init_capital
        self.data = pandas.read_csv("input/" + filename)
        
        for item in ignore_currencies:
            self.data = self.data[self.data["Instrument_code"] != item]
        
        for item in self.data["Instrument_code"].drop_duplicates():
            if item not in watching_currencies:
                self.data = self.data[self.data["Instrument_code"] != item]

        self.data["Date"] = pandas.to_datetime(self.data["Date"])
        self.data.sort_values("Date", inplace=True, ascending=True)
        self.isOk = True
        self.frame = frame
    
    def getAccount(self):
        new = account.Account(available=self.init_capital)
        new.makerFee = 0.9985
        new.takerFee = 0.9975

        return new
    
    def actualizeAccount(self, account):
        return True
    
    def getStats(self, crypto, parameters, full=False):
        dataframe = self.data[self.data["Instrument_code"] == crypto.instrument_code]

        if dataframe.shape[0] == 0 or dataframe.shape[0] < self.frame:
            self.data = self.data[self.data["Instrument_code"] != crypto.instrument_code]
            return None

        dataframe = dataframe.head(self.frame)
        dataframe = dataframe.sort_values("Date", ascending=False)
        
        fma_mean = 0
        for i in range(parameters.fma_unit, parameters.fma_unit + 10):
            fma_mean += float(dataframe.iloc[i]["Close"])
        
        fma_mean = fma_mean / 10

        for i in range(1, parameters.fma_unit + 1):
            fma_mean = ((2 / (parameters.fma_unit + 1)) * float(dataframe.iloc[parameters.fma_unit - i]["Close"])) + ((1 - (2 / (parameters.fma_unit + 1))) * fma_mean)

        sma_mean = 0
        for i in range(parameters.sma_unit, parameters.sma_unit + 10):
            sma_mean += float(dataframe.iloc[i]["Close"])
        
        sma_mean = sma_mean / 10

        for i in range(1, parameters.sma_unit + 1):
            sma_mean = ((2 / (parameters.sma_unit + 1)) * float(dataframe.iloc[parameters.sma_unit - i]["Close"])) + ((1 - (2 / (parameters.sma_unit + 1))) * sma_mean)

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

        crypto.fma = round(fma_mean, crypto.precision)
        crypto.sma = round(sma_mean, crypto.precision)

        if avg_loss == 0:
            crypto.rsi = 100
        
        else:
            crypto.rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
        
        adl = 0.0
        for i in range(1, parameters.period + 1):
            close = float(dataframe.iloc[parameters.period - i]["Close"])
            high = float(dataframe.iloc[parameters.period - i]["High"])
            low = float(dataframe.iloc[parameters.period - i]["Low"])
            volume = float(dataframe.iloc[parameters.period - i]["Volume"])

            if high == low:
                continue

            adl += ((((close - low) - (high - close)) / (high - low)) * volume) * i
        
        crypto.adl = adl / parameters.period

        crypto.last_price = float(dataframe.iloc[0]["Close"])
        
        if full == False:
            return True
        
        difference = (dataframe.iloc[0]["Date"] - dataframe.iloc[1]["Date"]).total_seconds()

        if 3600 >= difference:
            occurence = int((3600 / difference) * 24)
            if occurence > dataframe.shape[0]:
                return None
            
            hourlyDataframe = dataframe.head(int(3600 / difference))
            for index, row in hourlyDataframe.iterrows():
                crypto.hourlyVolume += float(row["Volume"])
            
            dataframe = dataframe.head(occurence)
        
        elif 86400 > difference > 3600:
            occurence = int(86400 / difference)
            if occurence > dataframe.shape[0]:
                return None

            crypto.hourlyVolume = float(dataframe.iloc[0]["Volume"]) / (difference / 3600)
            dataframe = dataframe.head(occurence)
        
        elif difference >= 86400:
            crypto.dailyVolume = float(dataframe.iloc[0]["Volume"]) / (difference / 86400)
            crypto.hourlyVolume = crypto.dailyVolume / 24
            return True

        for index, row in dataframe.iterrows():
            crypto.dailyVolume += float(row["Volume"])

        return True
    
    def getAllActiveAssets(self, parameters):
        if self.data.shape[0] == 0:
            return []
        
        last_datetime = self.data.iloc[0]["Date"]
        dataframe = self.data[self.data["Date"] == last_datetime]
        dataframe = dataframe.drop_duplicates(subset=["Date", "Instrument_code"])

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

            crypto.precision = 4
            crypto.higher = float(asset["higher"])

            values = dataframe[dataframe["Instrument_code"] == crypto.instrument_code]
            if values.shape[0] == 0:
                continue

            self.getStats(crypto, parameters)

            crypto.current = crypto.owned * crypto.last_price

            if crypto.current > crypto.higher:
                crypto.higher = crypto.current

            parameters.database.putInActive(crypto)

            active_assets.append(crypto)
        
        return active_assets
    
    def findProfitable(self, parameters):
        if self.data.shape[0] < self.frame:
            self.isOk = False
            return []
        
        last_datetime = self.data.iloc[0]["Date"]

        actives = parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies)
        ignored_assets = []
        for asset in actives:
            ignored_assets.append(asset["_id"])
        
        dataframe = self.data[self.data["Date"] == last_datetime]
        dataframe = dataframe.drop_duplicates(subset=["Date", "Instrument_code"])

        available_cryptos = []
        for index, row in dataframe.iterrows():
            pair = row["Instrument_code"]

            if pair in ignored_assets:
                continue
            
            new = assets.Crypto(
                pair, 
                "", 
                "", 
                0, 
                0, 
                0, 
                ""
            )
            new.precision = 4

            available_cryptos.append(new)
        
        profitable_assets = []
        for crypto in available_cryptos:
            res = self.getStats(crypto, parameters, full=True)
            if res is None:
                continue

            if crypto.sma >= crypto.fma:
                crypto.danger += 1

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

            if crypto.fma >= crypto.last_price:
                crypto.danger += 1
            
            if crypto.danger > parameters.max_danger:
                continue
            
            profitable_assets.append(crypto)

        profitable_assets.sort(key=lambda x: x.dailyVolume, reverse=True)
        profitable_assets.sort(key=lambda x: x.danger)

        self.data = self.data[(self.data["Date"] != last_datetime)]

        return profitable_assets
    
    def stopLossOrder(self, crypto, parameters):
        return True
    
    def sellingMarketOrder(self, crypto, parameters):
        parameters.database.putInHistory(crypto)
        parameters.account.available += crypto.current * parameters.account.takerFee

        return True
    
    def buyingMarketOrder(self, crypto, parameters):
        amount = ((parameters.account.available / crypto.danger) * 0.99 * (1 - (crypto.rsi / 100))) / crypto.last_price

        crypto.placed = amount * crypto.last_price
        
        amount -= (1 - parameters.account.makerFee) * amount

        crypto.owned = amount
        crypto.current = amount * crypto.last_price
        crypto.setHigher()

        parameters.database.putInActive(crypto)

        return True
