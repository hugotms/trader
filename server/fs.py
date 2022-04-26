import os

class File:

    def __init__(self):
        self.csv_file = os.getenv('CSV_FILE_PATH')
        if self.csv_file is None:
            print("Using default CSV file /data/cryptos.csv")
            self.csv_file = "/data/cryptos.csv"

    def new(self):
        try:
            fs = open(self.csv_file, mode='w')
            fs.close()
            return self
        except IOError:
            return None
    
    def isInFile(self, crypto):
        fs = open(self.csv_file, mode='r')
        lines = fs.readlines()
        fs.close()

        for line in lines:
            if crypto.cryptoName == line.split(sep=',')[0]:
                return True
        
        return False

    def addToFile(self, crypto):
        fs = open(self.csv_file, mode='a')
        fs.write(crypto.to_csv())
        fs.close()
    
    def updateInFile(self, crypto):
        fs = open(self.csv_file, mode='r')
        lines = fs.readlines()
        fs.close()

        new = []
        for line in lines:
            if crypto.cryptoName == line.split(sep=',')[0]:
                new.append(crypto.to_csv())
            else:
                new.append(line)
        
        fs = open(self.csv_file, mode='w')
        fs.writelines(new)
        fs.close()
    
    def putInFile(self, crypto):
        if self.isInFile(crypto):
            self.updateInFile(crypto)
        else:
            self.addToFile(crypto)
    
    def getLastDanger(self, crypto):
        fs = open(self.csv_file, mode='r')
        lines = fs.readlines()
        fs.close()

        for line in lines:
            if crypto.cryptoName == line.split(sep=',')[0]:
                return line.split(sep=',')[4]
        
        return 0