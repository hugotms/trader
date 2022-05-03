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

    def connect(self):    
        try:
            client = pymongo.MongoClient("mongodb://" + self.hostname + ":" + str(self.port) + "/", 
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
        self.connect()
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
        self.connect()
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
                "danger": crypto.danger,
                "loaded": crypto.loaded,
                "dailyDanger": crypto.dailyDanger,
                "weeklyDanger": crypto.weeklyDanger,
                "monthlyDanger": crypto.monthlyDanger
            }

            self.create("actives", data)
        
        return self
    
    def putInHistory(self, crypto):
        self.connect()
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
                "danger": crypto["danger"],
                "loaded": crypto["loaded"],
                "dailyDanger": crypto["dailyDanger"],
                "weeklyDanger": crypto["weeklyDanger"],
                "monthlyDanger": crypto["monthlyDanger"]
            }

            self.create("history", data)
        
        return self
    
    def findActives(self, watching_cryptos, watching_currencies):
        self.connect()
        if self.client is None:
            return []

        query = {}
        if len(watching_cryptos) != 0:
            query["_id"] = {
                "$in": watching_cryptos
            }
        
        if len(watching_currencies) != 0:
            query["currency"] = {
                "$in": watching_currencies
            }
        
        return self.find("actives", query)
    
    def getPastPerformance(self, past, watching_cryptos, watching_currencies, instrument_code=None):
        self.connect()
        if self.client is None:
            return None
        
        profit = 0
        loss = 0

        query = {
            "date": {
                "$gt": past
            }
        }

        if len(watching_cryptos) != 0:
            query["_id"] = {
                "$in": watching_cryptos
            }
        
        if len(watching_currencies) != 0:
            query["currency"] = {
                "$in": watching_currencies
            }

        if instrument_code is not None and len(watching_cryptos) != 0 and instrument_code not in watching_cryptos:
            return None
        
        elif instrument_code is not None and len(watching_currencies) != 0 and instrument_code.split('_')[1] not in watching_currencies:
            return None
        
        elif instrument_code is not None:
            query["instrument_code"] = instrument_code

        for item in self.find("history", query):
            placed = float(item["placed"])
            current = float(item["current"])

            if current > placed:
                profit += current - placed
            else:
                loss += placed - current
        
        return json.dumps({
            "profit": profit,
            "loss": loss
        })

    def getLastDanger(self, crypto):
        self.connect()
        if self.client is None:
            return 0
        
        query = {
            "instrument_code": crypto.instrument_code
        }

        res = self.find("history", query)
        if len(res) == 0:
            return 0
        
        return res[0]["danger"]
    