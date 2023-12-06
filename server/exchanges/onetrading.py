from server import web
from server import db

import time
import pandas

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from data import account
from data import assets

class Exchange:
    baseUrl = "https://api.onetrading.com/public/v1"

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
    
    def getAccount(self):
        response = self.getCurrencyBalance('EUR')
        if response is None:
            print("No account could be found")
            return None

        new = account.Account(available=response)
        new.makerFee, new.takerFee = self.getAccountFees()

        return new
    
    def actualizeAccount(self, account):
        fees = None
        
        response = self.getCurrencyBalance('EUR')
        if response is None:
            return False

        account.available = response
        account.makerFee, account.takerFee = self.getAccountFees()

        return True
    
    def getStats(self, crypto, parameters, full=False):
        frame = parameters.period + 1
        if frame < parameters.macd_slow + 10:
            frame = parameters.macd_slow + 10

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

        status_code, data = web.Api(Exchange.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=" + parameters.candlesticks_timeframe + "&period=" + str(parameters.candlesticks_period) + "&from=" + tz2 + "&to=" + tz, headers=header).send()
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
        status_code, data = web.Api(Exchange.baseUrl + "/candlesticks/" + crypto.instrument_code + "?unit=HOURS&period=1&from=" + tz2 + "&to=" + tz, headers=header).send()
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
        header = {
            "Accept": "application/json"
        }

        status_code, data = web.Api(Exchange.baseUrl + "/market-ticker/" + instrument_code, headers=header).send()

        if status_code != 200:
            print("Error while trying to get market tickers")
            return 0

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
            if len(parameters.ignore_currencies) != 0 and item['trade']['instrument_code'] in parameters.ignore_currencies:
                continue

            elif len(parameters.watching_currencies) != 0 and item['trade']['instrument_code'] not in parameters.watching_currencies:
                continue
            
            elif item['trade']['instrument_code'] in ignored_assets:
                continue

            elif item['trade']['side'] == "SELL":
                ignored_assets.append(item['trade']['instrument_code'])
                continue

            amount = (float(item['trade']['amount']) - float(item['fee']['fee_amount'])) * self.getPrice(item['trade']['instrument_code'])

            if item['trade']['instrument_code'] not in asset_names:
                active_assets.append(assets.Crypto(
                    instrument_code=item['trade']['instrument_code'],
                    base=item['trade']['instrument_code'].split('_')[0],
                    currency=item['trade']['instrument_code'].split('_')[1],
                    owned=float(item['trade']['amount']) - float(item['fee']['fee_amount']),
                    placed=float(item['trade']['amount']) * float(item['trade']['price']),
                    current=amount,
                    placed_on=item['trade']['time']
                    ).setHigher())
                
                asset_names.append(item['trade']['instrument_code'])
                
            else:
                active = active_assets[asset_names.index(item['trade']['instrument_code'])]
                active.owned += float(item['trade']['amount']) - float(item['fee']['fee_amount'])
                active.placed += float(item['trade']['amount']) * float(item['trade']['price'])
                active.current += amount
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
            self.getStats(asset, parameters)

            asset.last_price = self.getPrice(asset.instrument_code)

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
