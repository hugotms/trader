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
        amount = ((parameters.account.available / crypto.danger) * 0.99) / crypto.last_price

        crypto.placed = amount * crypto.last_price
        
        amount *= parameters.account.makerFee

        crypto.owned = amount
        crypto.current = amount * crypto.last_price
        crypto.setHigher()

        parameters.database.putInActive(crypto)

        return True
