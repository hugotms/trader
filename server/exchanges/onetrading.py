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

        status_code, data = web.Api(Exchange.baseUrl + '/account/balances', headers=self.headers).send()
        time.sleep(1)

        if status_code == 429:
            print("Too many requests at once")
            return None

        if status_code != 200:
            print("Error while trying to access balance data")
            return None

        for item in data['balances']:
            if item['currency_code'] == currency_code:
                amount += float(item['available'])

        return amount

    def getAccountFees(self):
        makerFee = 1
        takerFee = 1

        status_code, data = web.Api(Exchange.baseUrl + '/account/fees', headers=self.headers).send()
        time.sleep(1)

        if status_code == 429:
            print("Too many requests at once")
            return makerFee, takerFee

        if status_code != 200:
            print("Error while trying to access account fees data")
            return makerFee, takerFee

        running_trading_volume = data['running_trading_volume']

        for tier in data['fee_tiers']:
            if tier['volume'] >= running_trading_volume:
                makerFee = 1 - float(tier['maker_fee']) / 100
                takerFee = 1 - float(tier['taker_fee']) / 100

        return makerFee, takerFee

    def getAccount(self, parameters):
        response = self.getCurrencyBalance(parameters.base_fiat)
        if response is None:
            print("No account could be found")
            return None

        new = account.Account(available=response)
        new.makerFee, new.takerFee = self.getAccountFees()

        return new

    def actualizeAccount(self, parameters):
        response = self.getCurrencyBalance(parameters.base_fiat)
        if response is None:
            return False

        parameters.account.available = response
        parameters.account.makerFee, parameters.account.takerFee = self.getAccountFees()

        return True

    def getDataframe(self, instrument_code, timeframe, lines, candlesticks_period, today, tz, tz2, delta):
        header = {
            "Accept": "application/json"
        }

        status_code, data = web.Api(Exchange.baseUrl + "/candlesticks/" + instrument_code + "?unit=" + timeframe + "&period=" + str(candlesticks_period) + "&from=" + tz2 + "&to=" + tz, headers=header).send()
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
        header = {
            "Accept": "application/json"
        }

        crypto.last_price = self.getPrice(crypto.instrument_code)
        if crypto.last_price == 0:
            return None

        today = datetime.utcnow()
        tz = today.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        tz2 = (today - relativedelta(months=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = relativedelta(months=1)

        dataframe = self.getDataframe(crypto.instrument_code, "MONTHS", 24, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None

        last_time = datetime.strptime(dataframe.iloc[-1]["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if datetime.strftime(last_time, "%m") != datetime.strftime(today, "%m"):
            status_code, data = web.Api(Exchange.baseUrl + "/market-ticker/" + crypto.instrument_code, headers=header).send()

            if status_code != 200:
                print("Error while trying to get market tickers")
                return None

            length = dataframe.shape[0]
            dataframe.loc[length] = [datetime.strftime(today, "%Y-%m-%dT%H:%M:%S.%fZ"), float(data['high']), float(data['low']), float(data['last_price']), None]
            dataframe.reset_index(inplace=True, drop=True)

        if self.getRSI(dataframe) < 50:
            crypto.danger += 1

        tz2 = (today - relativedelta(weeks=24)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = relativedelta(weeks=1)

        dataframe = self.getDataframe(crypto.instrument_code, "WEEKS", 24, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None

        last_time = datetime.strptime(dataframe.iloc[-1]["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if datetime.strftime(last_time, "%W") != datetime.strftime(today, "%W"):
            status_code, data = web.Api(Exchange.baseUrl + "/market-ticker/" + crypto.instrument_code, headers=header).send()

            if status_code != 200:
                print("Error while trying to get market tickers")
                return None

            length = dataframe.shape[0]
            dataframe.loc[length] = [datetime.strftime(today, "%Y-%m-%dT%H:%M:%S.%fZ"), float(data['high']), float(data['low']), float(data['last_price']), None]
            dataframe.reset_index(inplace=True, drop=True)

        if self.getRSI(dataframe) < 50:
            crypto.danger += 1

        tz2 = (today - timedelta(days=36)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        delta = timedelta(days=1)

        dataframe = self.getDataframe(crypto.instrument_code, "DAYS", 26 + 10, 1, today, tz, tz2, delta)
        if dataframe is None:
            return None

        last_time = datetime.strptime(dataframe.iloc[-1]["Date"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if datetime.strftime(last_time, "%d") != datetime.strftime(today, "%d"):
            status_code, data = web.Api(Exchange.baseUrl + "/market-ticker/" + crypto.instrument_code, headers=header).send()

            if status_code != 200:
                print("Error while trying to get market tickers")
                return None

            length = dataframe.shape[0]
            dataframe.loc[length] = [datetime.strftime(today, "%Y-%m-%dT%H:%M:%S.%fZ"), float(data['high']), float(data['low']), float(data['last_price']), None]
            dataframe.reset_index(inplace=True, drop=True)

        dataframe["FMA"] = dataframe.iloc[:]["Close"].ewm(span=12, adjust=False).mean()
        dataframe["SMA"] = dataframe.iloc[:]["Close"].ewm(span=26, adjust=False).mean()
        dataframe["MACD"] = dataframe["FMA"] - dataframe["SMA"]
        dataframe["Signal"] = dataframe.iloc[:]["MACD"].ewm(span=9, adjust=False).mean()
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
        header = {
            "Accept": "application/json"
        }

        status_code, data = web.Api(Exchange.baseUrl + "/market-ticker/" + instrument_code, headers=header).send()

        if status_code != 200:
            print("Error while trying to get market tickers")
            return False

        return float(data['last_price'])

    def getAllActiveAssets(self, parameters):
        active_assets = []

        status_code, data = web.Api(Exchange.baseUrl + "/account/trades", headers=self.headers).send()
        time.sleep(1)

        if status_code == 429:
            print("Too many requests at once")
            return []

        if status_code != 200:
            print("Error while trying to access account active trades")
            return []

        trades = data['trade_history']

        asset_names = []
        ignored_assets = []
        for item in trades:
            if item['trade']['instrument_code'].split('_')[1] != parameters.base_fiat:
                continue

            if len(parameters.ignore_currencies) != 0 and item['trade']['instrument_code'] in parameters.ignore_currencies:
                continue

            elif len(parameters.watching_currencies) != 0 and item['trade']['instrument_code'] not in parameters.watching_currencies:
                continue

            elif item['trade']['instrument_code'] in ignored_assets:
                continue

            elif item['trade']['side'] == "SELL":
                ignored_assets.append(item['trade']['instrument_code'])
                continue

            if item['trade']['instrument_code'] not in asset_names:
                last_price = self.getPrice(item['trade']['instrument_code'])
                if not last_price:
                    ignored_assets.append(item['trade']['instrument_code'])
                    continue

                asset = assets.Crypto(
                    instrument_code=item['trade']['instrument_code'],
                    base=item['trade']['instrument_code'].split('_')[0],
                    currency=item['trade']['instrument_code'].split('_')[1],
                    owned=float(item['trade']['amount']) - float(item['fee']['fee_amount']),
                    placed=float(item['trade']['amount']) * float(item['trade']['price']),
                    current=(float(item['trade']['amount']) - float(item['fee']['fee_amount'])) * last_price,
                    placed_on=item['trade']['time']
                ).setHigher()

                asset.last_price = last_price

                active_assets.append(asset)

                asset_names.append(item['trade']['instrument_code'])

            else:
                active = active_assets[asset_names.index(item['trade']['instrument_code'])]
                active.owned += float(item['trade']['amount']) - float(item['fee']['fee_amount'])
                active.placed += float(item['trade']['amount']) * float(item['trade']['price'])
                active.current += (float(item['trade']['amount']) - float(item['fee']['fee_amount'])) * active.last_price
                active.setHigher()

        for crypto in parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies):
            isFound = False

            for asset in active_assets:
                if crypto["_id"] == asset.instrument_code:
                    isFound = True

                    asset.stop_id = crypto["stop_id"]
                    asset.market_id = crypto["market_id"]
                    asset.failed = bool(crypto["failed"])
                    asset.alerted = bool(crypto["alerted"])
                    asset.precision = int(crypto["precision"])

                    if float(crypto["higher"]) > asset.current:
                        asset.higher = float(crypto["higher"])

            if isFound == True or crypto["_id"] in ignored_assets:
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

            status_code, data = web.Api(Exchange.baseUrl + "/account/orders/" + order_id, headers=self.headers).send()
            time.sleep(1)

            if status_code != 200:
                parameters.database.putInHistory(asset)
                continue

            if data['order']['status'] not in ["FILLED_FULLY", "CLOSED"]:
                parameters.database.putInHistory(asset)
                continue

            current_price = asset.owned * float(data['order']['price'])
            if current_price == 0.0:
                parameters.database.putInHistory(asset)
                continue

            asset.current = current_price
            if asset.current > asset.higher:
                asset.higher = asset.current

            parameters.database.putInHistory(asset)

        for asset in active_assets:
            header = {
                "Accept": "application/json"
            }

            if asset.precision == 0:
                status_code, data = web.Api(Exchange.baseUrl + "/instruments", headers=header).send()
                time.sleep(1)

                if status_code != 200:
                    continue

                for item in data:
                    pair = item["base"]["code"] + "_" + item["quote"]["code"]

                    if pair != asset.instrument_code:
                        continue

                    asset.precision = int(item["amount_precision"])

                    break

            parameters.database.putInActive(asset)

        return active_assets

    def findProfitable(self, parameters):
        header = {
            "Accept": "application/json"
        }

        actives = parameters.database.findActives(parameters.watching_currencies, parameters.ignore_currencies)
        ignored_assets = []
        for asset in actives:
            ignored_assets.append(asset["_id"])

        status_code, data = web.Api(Exchange.baseUrl + "/instruments", headers=header).send()
        time.sleep(1)

        if status_code != 200:
            print("Error while trying to get available cryptos")
            return []

        available_cryptos = []
        for item in data:
            if item["quote"]["code"] != parameters.base_fiat:
                continue

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

            profitable_assets.append(crypto)

        profitable_assets.sort(key=lambda x: x.dailyVolume, reverse=True)
        profitable_assets.sort(key=lambda x: x.danger)

        return profitable_assets

    def stopLossOrder(self, crypto, parameters):
        if crypto.stop_id != "":
            status_code, data = web.Api(Exchange.baseUrl + "/account/orders/" + crypto.stop_id, headers=self.headers, method="DELETE").send()
            time.sleep(1)

            if status_code == 429:
                print("Too many requests at once")
                return False

            if status_code != 204:
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

        status_code, data = web.Api(Exchange.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()
        time.sleep(1)

        if status_code == 429:
            print("Too many requests at once")
            return False

        if status_code != 201:
            crypto.failed == True
            print("Error while trying to create stop order")
            return False

        crypto.stop_id = data["order_id"]

        parameters.database.putInActive(crypto)

        return True

    def sellingMarketOrder(self, crypto, parameters):
        if crypto.stop_id != "":
            status_code, data = web.Api(Exchange.baseUrl + "/account/orders/" + crypto.stop_id, headers=self.headers, method="DELETE").send()
            time.sleep(1)

            if status_code == 429:
                print("Too many requests at once")
                return False

            if status_code != 204:
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

        status_code, data = web.Api(Exchange.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()
        time.sleep(1)

        if status_code == 429:
            print("Too many requests at once")
            return False

        if status_code != 201:
            print("Error while trying to create selling market order")
            return False

        crypto.market_id = data['order_id']
        parameters.database.putInActive(crypto)

        return True

    def buyingMarketOrder(self, crypto, parameters):
        current_price = self.getPrice(crypto.instrument_code)
        if current_price == 0:
            return False

        amount = ((parameters.account.available / crypto.danger) * 0.99) / current_price
        body = {
            "instrument_code": crypto.instrument_code,
            "side": "BUY",
            "type": "MARKET",
            "amount": self.truncate(amount, crypto.precision)
        }

        status_code, data = web.Api(Exchange.baseUrl + "/account/orders", headers=self.headers, method="POST", data=body).send()

        if status_code == 429:
            print("Too many requests at once")
            return False

        if status_code != 201:
            print("Error while trying to buy crypto")
            return False

        crypto.owned = amount * parameters.account.makerFee
        crypto.placed = amount * current_price
        crypto.current = crypto.owned * current_price
        crypto.setHigher()

        return True
