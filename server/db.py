import pymongo
import json

from datetime import datetime, timedelta

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
                "stop_id": crypto.stop_id,
                "market_id": crypto.market_id,
                "base": crypto.base,
                "currency": crypto.currency,
                "owned": crypto.owned,
                "placed": crypto.placed,
                "current": crypto.current,
                "higher": crypto.higher,
                "placed_on": crypto.placed_on,
                "danger": crypto.danger,
                "hourlyVolume": crypto.hourlyVolume,
                "dailyVolume": crypto.dailyVolume,
                "precision": crypto.precision,
                "failed": crypto.failed,
                "alerted": crypto.alerted
            }

            query = {
                "_id": crypto.instrument_code
            }

            self.update("actives", data, query)
        
        else:
            data = {
                "_id": crypto.instrument_code,
                "stop_id": crypto.stop_id,
                "market_id": crypto.market_id,
                "base": crypto.base,
                "currency": crypto.currency,
                "owned": crypto.owned,
                "placed": crypto.placed,
                "current": crypto.current,
                "higher": crypto.higher,
                "placed_on": crypto.placed_on,
                "danger": crypto.danger,
                "hourlyVolume": crypto.hourlyVolume,
                "dailyVolume": crypto.dailyVolume,
                "precision": crypto.precision,
                "failed": crypto.failed,
                "alerted": crypto.alerted
            }

            self.create("actives", data)
        
        return self
    
    def putInHistory(self, crypto):
        if self.client is None:
            return None
        
        isFound = False
        for active in self.find("actives"):
            if active["_id"] == crypto.instrument_code:
                isFound = True
                break
        
        if isFound == True:
            query = {
                "_id": crypto.instrument_code
            }

            self.delete("actives", query)

            data = {
                "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "instrument_code": crypto.instrument_code,
                "base": crypto.base,
                "currency": crypto.currency,
                "owned": str(crypto.owned),
                "placed": str(crypto.placed),
                "current": str(crypto.current),
                "higher": str(crypto.higher),
                "placed_on": crypto.placed_on
            }

            self.create("history", data)
        
        return self
    
    def findActives(self, watching_currencies, ignore_currencies):
        if self.client is None:
            return []

        query = {}
        if len(ignore_currencies) != 0:
            query["_id"] = {
                "$nin": ignore_currencies
            }
        
        elif len(watching_currencies) != 0:
            query["_id"] = {
                "$in": watching_currencies
            }
        
        return self.find("actives", query)
    
    def getPastPerformance(self, report, parameters, instrument_code=None):
        if self.client is None:
            return None

        query = {
            "date": {
                "$gt": report.past.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        }
        query2 = {
            "placed_on": {
                "$gt": report.past.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        }

        if len(parameters.ignore_currencies) != 0:
            query["instrument_code"] = {
                "$nin": parameters.ignore_currencies
            }
            query2["_id"] = {
                "$nin": parameters.ignore_currencies
            }
        
        elif len(parameters.watching_currencies) != 0:
            query["instrument_code"] = {
                "$in": parameters.watching_currencies
            }
            query2["_id"] = {
                "$in": parameters.watching_currencies
            }
        
        if instrument_code is not None:
            query["instrument_code"] = instrument_code
            query2["_id"] = instrument_code

        res = self.find("history", query)
        res2 = self.find("actives", query2)
        report.orders = len(res) + len(res2)
        for item in res:
            placed = float(item["placed"])
            current = float(item["current"])

            report.volume += current

            current *= parameters.account.takerFee

            if current > placed:
                report.gain += current - placed
                continue

            report.loss += placed - current
        
        for item in res2:
            report.volume += float(item["placed"])
        
        return res

    def getLastPlaced(self, crypto, wait_time):
        if self.client is None:
            return True
        
        query = {
            "instrument_code": crypto.instrument_code,
            "date": {
                "$gte": (datetime.utcnow() - timedelta(minutes=wait_time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        }

        res = self.find("history", query)
        if len(res) == 0:
            return True

        return False
