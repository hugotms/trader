import requests
import json

class Api:

    def __init__(self, url, data={}, headers=None, method='GET'):
        self.url = url
        self.data = data
        self.headers = headers
        self.method = method
        self.statusCode = 500
        self.res = None

    def send(self):
        if self.method == 'GET':
            self.res = requests.get(self.url, headers=self.headers)
        elif self.method == 'POST':
            self.res = requests.post(self.url, headers=self.headers, json=self.data)
        elif self.method == 'PUT':
            self.res = requests.put(self.url, headers=self.headers, json=self.data)
        elif self.method == 'DELETE':
            self.res = requests.delete(self.url, headers=self.headers, json=self.data)
        else:
            print('Unsupported method')
        
        return self
    
    def getStatusCode(self):
        if self.res is not None:
            return self.res.status_code
        
        return 500
    
    def getData(self):
        if self.res is not None:
            return self.res.json()
        
        return None