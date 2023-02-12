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
        response = None
        
        try:
            if self.method == 'GET':
                response = requests.get(self.url, headers=self.headers)
            elif self.method == 'POST':
                response = requests.post(self.url, headers=self.headers, json=self.data)
            elif self.method == 'PUT':
                response = requests.put(self.url, headers=self.headers, json=self.data)
            elif self.method == 'DELETE':
                response = requests.delete(self.url, headers=self.headers, json=self.data)
            else:
                print('Unsupported method')
        except:
            response = None
            print('Unable to access URL')
        
        if response is not None:
            self.statusCode = response.status_code
            self.res = response.json()
        
        return self.statusCode, self.res
