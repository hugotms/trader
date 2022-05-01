import pymongo
import os

from datetime import datetime

class Mongo:

    def __init__(self):
        self.hostname = os.getenv('MONGO_DB_HOST')
        self.port = os.getenv('MONGO_DB_PORT')
        self.db_name = os.getenv('MONGO_DB_NAME')
        self.user = os.getenv('MONGO_DB_USER')
        self.password = os.getenv('MONGO_DB_PASSWORD')

        if self.user is None:
            print("Default DB user is trader")
            self.user = "trader"

        if self.db_name is None:
            print("Default DB name is trader")
            self.db_name = "trader" 

    def new(self):
        if self.hostname is None or self.password is None:
            print("Required DB variables not set")
            return None
        
        if self.port is None:
            print("Default DB port is 27017")
            self.port = 27017
        self.port = int(self.port)

        return self

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
    
    def putInActive(self, crypto):
        self.connect()
        if self.client is None:
            return None
        
        isFound = False
        for active in self.find("actives"):
            if active["_id"] == crypto.cryptoName:
                isFound = True
                break
        
        if isFound == True:
            data = {
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
                "_id": crypto.cryptoName
            }

            self.update("actives", data, query)
        
        else:
            data = {
                "_id": crypto.cryptoName,
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
                "date": datetime.now(),
                "cryptoName": crypto["_id"],
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
    
    def findActive(self):
        self.connect()
        if self.client is None:
            return []
        
        return self.find("actives")

    def getLastDanger(self, crypto):
        self.connect()
        if self.client is None:
            return 0
        
        query = {
            "cryptoName": crypto.cryptoName
        }

        res = self.find("history", query)
        if len(res) == 0:
            return 0
        
        return res[0]["danger"]
    