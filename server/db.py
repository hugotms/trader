import pymongo
import json

from datetime import datetime

class Mongo:

    def __init__(self, hostname, port, db_name, user, password):
        self.hostname = hostname
        self.port = port
        self.db_name = db_name
        self.user = user
        self.password = password

        try:
            client = pymongo.MongoClient(
                host=self.hostname,
                port=self.port, 
                username=self.user, 
                password=self.password
            )
            client.server_info()
            self.client = client[self.db_name]

        except Exception:
            print("Unable to connect to database")
            self.client = None   
        
    def find(self, table, query={}):
        return list(self.client[table].find(query))
    
    def create(self, table, data):
        if self.client[table].insert_one(data).inserted_id is None:
            print("Unable to insert data on " + table)
    
    def update(self, table, data, query):
        if self.client[table].update_one(query, {"$set": data}) is None:
            print("Unable to update data on " + table)
    
    def delete(self, table, query):
        if self.client[table].delete_one(query) is None:
            print("Unable to delete data on " + table)
    
    def findVar(self, var_name, current_value, default=None):
        if self.client is None and current_value is None:
            return default
        
        elif self.client is None:
            return current_value

        query = {
            "_id": var_name
        }

        res = self.find("parameters", query)

        if len(res) == 0 and current_value is None:
            return default
        
        elif len(res) == 0:
            return current_value

        return res[0]["value"]
    
    def putInActive(self, crypto):
        if self.client is None:
            return None
        
        isFound = False
        for active in self.find("actives"):
            if active["_id"] == crypto.instrument_code:
                isFound = True
                break
        
        if isFound == True:
            data = {
                "base": crypto.base,
                "currency": crypto.currency,
                "owned": crypto.owned,
                "placed": crypto.placed,
                "current": crypto.current,
                "higher": crypto.higher,
                "placed_on": crypto.placed_on,
                "danger": crypto.danger,
                "loaded": crypto.loaded,
                "dailyDanger": crypto.dailyDanger,
                "weeklyDanger": crypto.weeklyDanger,
                "monthlyDanger": crypto.monthlyDanger
            }

            query = {
                "_id": crypto.instrument_code
            }

            self.update("actives", data, query)
        
        else:
            data = {
                "_id": crypto.instrument_code,
                "base": crypto.base,
                "currency": crypto.currency,
                "owned": crypto.owned,
                "placed": crypto.placed,
                "current": crypto.current,
                "higher": crypto.higher,
                "placed_on": crypto.placed_on,
                "danger": crypto.danger,
                "loaded": crypto.loaded,
                "dailyDanger": crypto.dailyDanger,
                "weeklyDanger": crypto.weeklyDanger,
                "monthlyDanger": crypto.monthlyDanger
            }

            self.create("actives", data)
        
        return self
    
    def putInHistory(self, crypto):
        if self.client is None:
            return None
        
        isFound = False
        for active in self.find("actives"):
            if active["_id"] == crypto["_id"]:
                isFound = True
                break
        
        if isFound == True:
            query = {
                "_id": crypto["_id"]
            }

            self.delete("actives", query)

            data = {
                "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "instrument_code": crypto["_id"],
                "base": crypto["base"],
                "currency": crypto["currency"],
                "owned": crypto["owned"],
                "placed": crypto["placed"],
                "current": crypto["current"],
                "higher": crypto["higher"],
                "placed_on": crypto["placed_on"],
                "danger": crypto["danger"],
                "loaded": crypto["loaded"],
                "dailyDanger": crypto["dailyDanger"],
                "weeklyDanger": crypto["weeklyDanger"],
                "monthlyDanger": crypto["monthlyDanger"]
            }

            self.create("history", data)
        
        return self
    
    def findActives(self, watching_cryptos, ignore_cryptos, watching_currencies):
        if self.client is None:
            return []

        query = {}
        if len(ignore_cryptos) != 0:
            query["_id"] = {
                "$nin": ignore_cryptos
            }
        
        elif len(watching_cryptos) != 0:
            query["_id"] = {
                "$in": watching_cryptos
            }
        
        if len(watching_currencies) != 0:
            query["currency"] = {
                "$in": watching_currencies
            }
        
        return self.find("actives", query)
    
    def getPastPerformance(self, past, watching_cryptos, ignore_cryptos, watching_currencies, instrument_code=None):
        if self.client is None:
            return None
        
        profit = 0
        loss = 0
        volume = 0

        query = {
            "date": {
                "$gt": past.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        }

        if len(ignore_cryptos) != 0:
            query["instrument_code"] = {
                "$nin": ignore_cryptos
            }
        
        elif len(watching_cryptos) != 0:
            query["instrument_code"] = {
                "$in": watching_cryptos
            }
        
        if len(watching_currencies) != 0:
            query["currency"] = {
                "$in": watching_currencies
            }
        
        if instrument_code is not None:
            query["instrument_code"] = instrument_code

        res = self.find("history", query)
        trades = len(res)
        for item in res:
            placed = float(item["placed"])
            current = float(item["current"])

            placed_on = None
            if "placed_on" in item:
                placed_on = datetime.strptime(item["placed_on"], "%Y-%m-%dT%H:%M:%S.%fZ")

            if current > placed:
                profit += current - placed
            else:
                loss += placed - current

            volume += current
            if placed_on is not None and past <= placed_on:
                trades += 1
                volume += placed
        
        return json.dumps({
            "profit": profit,
            "loss": loss,
            "trades": trades,
            "volume": volume
        })

    def getLastDanger(self, crypto):
        if self.client is None:
            return 0
        
        query = {
            "instrument_code": crypto.instrument_code
        }

        res = self.find("history", query)
        if len(res) == 0:
            return 0
        
        return res[0]["danger"]
    