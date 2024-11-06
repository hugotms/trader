from server import web

import time
import pandas
import math

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from data import account
from data import assets

class Exchange:
    baseUrl = "https://api.onetrading.com/fast/v1"

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

    def actualizeAccount(self, parameters):
        return True

    def getDataframe(self, instrument_code, timeframe, lines, candlesticks_period, today, tz, tz2, delta):
        status_code, data = web.Api(Exchange.baseUrl + "/candlesticks/" + instrument_code + "?unit=" + timeframe + "&period=" + str(candlesticks_period) + "&from=" + tz2 + "&to=" + tz, headers=self.header).send()
        time.sleep(1)

        if status_code != 200:
            print("Error while trying to get price tickers")
            return None

        data = data["candlesticks"]

        length = len(data)
        if length < 3:
            return None

        dataframe = pandas.DataFrame(data=data)
        dataframe = dataframe.loc[:, ["time", "high", "low", "close", "volume"]]
        dataframe.rename(columns={"time": "Date", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
        dataframe.sort_values("Date", inplace=True, ascending=True)
        dataframe.reset_index(inplace=True, drop=True)

        length = dataframe.shape[0]
        last_time = datetime.strptime(dataframe.iloc[-1]["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")

        i = 0
        while last_time + delta < today.replace(second=59):
            last_time += delta
            dataframe.loc[length] = [datetime.strftime(last_time, "%Y-%m-%dT%H:%M:%S.%fZ"), None, None, None, None]
            length += 1
            i += 1

            if i >= lines:
                return None
        
        dataframe.reset_index(inplace=True, drop=True)

        modified = True
        while modified:
            modified = False

            last_row = None
            length = dataframe.shape[0]

            for index, row in dataframe.iterrows():
                if index >= lines:
                    break

                if index + 1 > length:
                    break

                if index == 0:
                    last_row = row
                    continue

                current_time = datetime.strptime(row["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")

                if datetime.strptime(last_row["Date"], "%Y-%m-%dT%H:%M:%S.%fZ") + delta < current_time:
                    modified = True
                    new_time = datetime.strptime(last_row["Date"], "%Y-%m-%dT%H:%M:%S.%fZ") + delta
                    new_row = [datetime.strftime(new_time, "%Y-%m-%dT%H:%M:%S.%fZ"), None, None, None, None]
                    dataframe.loc[index - 0.5] = new_row
                    break

                last_row = row

            dataframe = dataframe.sort_index().reset_index(drop=True)

        length = dataframe.shape[0]
        last_row = dataframe.iloc[0]
        last_time = datetime.strptime(last_row["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")

        while length < lines:
            last_time -= delta
            dataframe.loc[-1] = [datetime.strftime(last_time, "%Y-%m-%dT%H:%M:%S.%fZ"), last_row["High"], last_row["Low"], last_row["Close"], 0.0]
            dataframe = dataframe.sort_index().reset_index(drop=True)
            length += 1

        dataframe[["High", "Low", "Close"]] = dataframe[["High", "Low", "Close"]].fillna(method='ffill')
        dataframe["Volume"].fillna(value=0.0, inplace=True)
        dataframe[["High", "Low", "Close", "Volume"]] = dataframe[["High", "Low", "Close", "Volume"]].astype("float64")

        return dataframe

    def getRSI(self, dataframe):
        dataframe = dataframe.sort_values("Date", ascending=False)

        avg_gain = 0
        avg_loss = 0
        for i in range(14):
            current_price = float(dataframe.iloc[i]["Close"])
            last_price = float(dataframe.iloc[i + 1]["Close"])

            if current_price == last_price:
                continue

            elif current_price - last_price > 0:
                avg_gain += abs(current_price - last_price)
                continue

            avg_loss += abs(current_price - last_price)

        avg_gain = avg_gain / 14
        avg_loss = avg_loss / 14

        if avg_loss == 0:
            return 100

        return 100 - (100 / (1 + (avg_gain / avg_loss)))

    def getStats(self, crypto, parameters):
        today = datetime.utcnow()
        tz = today.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        tz2 = (today - relativedelta(months=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = relativedelta(months=1)

        dataframe = self.getDataframe(crypto.instrument_code, "MONTHS", 24, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None

        if self.getRSI(dataframe) < 50:
            crypto.danger += 1

        tz2 = (today - relativedelta(weeks=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = relativedelta(weeks=1)

        dataframe = self.getDataframe(crypto.instrument_code, "WEEKS", 24, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None

        if self.getRSI(dataframe) < 50:
            crypto.danger += 1

        tz2 = (today - timedelta(days=(parameters.macd_slow + 10))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = timedelta(days=1)

        dataframe = self.getDataframe(crypto.instrument_code, "DAYS", parameters.macd_slow + 10, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None
        
        dataframe["FMA"] = dataframe.iloc[:]["Close"].ewm(span=parameters.macd_fast, adjust=False).mean()
        dataframe["SMA"] = dataframe.iloc[:]["Close"].ewm(span=parameters.macd_slow, adjust=False).mean()
        dataframe["MACD"] = dataframe["FMA"] - dataframe["SMA"]
        dataframe["Signal"] = dataframe.iloc[:]["MACD"].ewm(span=parameters.macd_smooth, adjust=False).mean()
        dataframe["Highest"] = dataframe["High"].rolling(14).max()
        dataframe["Lowest"] = dataframe["Low"].rolling(14).min()
        dataframe["%K"] = ((dataframe["Close"] - dataframe["Lowest"]) * 100) / (dataframe["Highest"] - dataframe["Lowest"])
        dataframe["%D"] = dataframe["%K"].rolling(3).mean()

        crypto.macd = float(dataframe.iloc[-1]["MACD"])
        crypto.signal = float(dataframe.iloc[-1]["Signal"])
        crypto.stochastic_k = float(dataframe.iloc[-1]["%K"])
        crypto.stochastic_d = float(dataframe.iloc[-1]["%D"])

        if math.isnan(crypto.macd) or math.isnan(crypto.signal) or math.isnan(crypto.stochastic_k) or math.isnan(crypto.stochastic_d):
            return None

        crypto.rsi = self.getRSI(dataframe)

        tz2 = (today - timedelta(hours=34)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = timedelta(hours=1)

        dataframe = self.getDataframe(crypto.instrument_code, "HOURS", 34, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None

        if self.getRSI(dataframe) < 50:
            crypto.danger += 2

        crypto.hourlyVolume = float(dataframe.iloc[-1]["Volume"])

        dataframe = dataframe.sort_values("Date", ascending=False)
        dataframe.reset_index(drop=True, inplace=True)

        for index, row in dataframe.iterrows():
            if index >= 24:
                break

            crypto.dailyVolume += float(row["Volume"])

        tz2 = (today - timedelta(minutes=(24 * 5))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = timedelta(minutes=5)

        dataframe = self.getDataframe(crypto.instrument_code, "MINUTES", 24, 5, today, tz, tz2, delta)
        if dataframe is None:
            return None

        if self.getRSI(dataframe) < 50:
            crypto.danger += 2

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

            res = self.getStats(crypto, parameters)
            if res is None:
                continue

            if parameters.account.available * 0.99 >= crypto.hourlyVolume:
                crypto.danger += 4

            if parameters.account.available * 0.99 >= crypto.hourlyVolume * 0.25:
                crypto.danger += 1

            if parameters.account.available * 0.99 >= crypto.hourlyVolume * 0.5:
                crypto.danger += 2

            if parameters.account.available * 0.99 >= crypto.hourlyVolume * 0.75:
                crypto.danger += 3

            if crypto.hourlyVolume < crypto.dailyVolume / 24:
                crypto.danger += 2

            crypto.last_price = self.getPrice(crypto.instrument_code)
            if crypto.last_price == 0:
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
