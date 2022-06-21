import os

from server import db
from server import exchange
from server import mail

class Params:

    def __init__(self):
        self.exchange_api_key = os.getenv('EXCHANGE_API_KEY')

        self.db_hostname = os.getenv('MONGO_DB_HOST')
        self.db_port = os.getenv('MONGO_DB_PORT')
        self.db_name = os.getenv('MONGO_DB_NAME')
        self.db_user = os.getenv('MONGO_DB_USER')
        self.db_password = os.getenv('MONGO_DB_PASSWORD')

        self.min_recovered = os.getenv('MIN_RECOVERED_RATE')
        self.min_profit = os.getenv('MIN_PROFIT_RATE')
        self.max_danger = os.getenv('MAX_DANGER')
        self.refresh_time = os.getenv('MINUTES_REFRESH_TIME')
        self.taxe_rate = os.getenv('TAXE_RATE')
        self.following = os.getenv('FOLLOWING')
        self.make_trade = os.getenv('MAKE_TRADE')
        self.max_concurrent_trades = os.getenv('MAX_CONCURRENT_TRADES')

        self.latest_bot_release = os.getenv('TRADER_VERSION')

        self.watching_currencies = os.getenv('WATCHING_CURRENCIES')
        self.ignore_currencies = os.getenv('IGNORE_CURRENCIES')

        self.smtp_sending = os.getenv('SEND_ALERT_MAIL')
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = os.getenv('SMTP_PORT')
        self.smtp_from = os.getenv('SMTP_FROM')
        self.smtp_as = os.getenv('SMTP_AS')
        self.smtp_key = os.getenv('SMTP_KEY')
        self.smtp_to = os.getenv('SMTP_TO')
        self.smtp = None
    
    def actualize(self):
        self.watching_currencies = self.database.findVar("watching_currencies", self.watching_currencies, [])
        self.ignore_currencies = self.database.findVar("ignore_currencies", self.ignore_currencies, [])
        self.min_recovered = self.database.findVar("min_recovered", self.min_recovered, 0.95)
        self.min_profit = self.database.findVar("min_profit", self.min_profit, 1.05)
        self.max_danger = self.database.findVar("max_danger", self.max_danger, 10)
        self.refresh_time = self.database.findVar("refresh_time", self.refresh_time, 10)
        if self.refresh_time < 1:
            self.refresh_time = 1
        
        self.taxe_rate = self.database.findVar("taxe_rate", self.taxe_rate, 0.0)
        self.following = self.database.findVar("following", self.following, True)
        self.make_trade = self.database.findVar("make_trade", self.make_trade, False)
        self.max_concurrent_trades = self.database.findVar("max_concurrent_trades", self.max_concurrent_trades, 0)

        if self.smtp_sending == True:
            self.smtp_host = self.database.findVar("smtp_host", self.smtp_host)
            self.smtp_port = self.database.findVar("smtp_port", self.smtp_port)
            self.smtp_from = self.database.findVar("smtp_from", self.smtp_from)
            self.smtp_key = self.database.findVar("smtp_key", self.smtp_key)
            self.smtp_as = self.database.findVar("smtp_as", self.smtp_as)
        
        if (self.smtp_sending == True and 
            (self.smtp_host is None or self.smtp_port is None or
            self.smtp_from is None or self.smtp_key is None)
            ):
            print("Required SMTP values not set. No email alert will be send")
            self.smtp_sending = False
            self.smtp = None
        
        self.exchange_client = exchange.BitpandaPro(self.exchange_api_key, self.database, self.watching_currencies, self.ignore_currencies)

        if self.smtp_sending == True: 
            self.smtp = mail.SMTP(
                self.smtp_host, 
                self.smtp_port, 
                self.smtp_key, 
                self.smtp_from, 
                self.smtp_as, 
                self.smtp_to
            )

    def new(self):
        if self.exchange_api_key is None:
            print("Required API key was not set")
            return False
        
        if self.db_hostname is None:
            print("Required DB hostname was not set")
            return False
        
        if self.db_password is None:
            print("Required DB password was not set")
            return False
        
        if self.db_user is None:
            print("Default DB user is trader")
            self.db_user = "trader"

        if self.db_name is None:
            print("Default DB name is trader")
            self.db_name = "trader" 
        
        if self.db_port is None:
            print("Default DB port is 27017")
            self.db_port = 27017
        
        if self.smtp_sending is None or self.smtp_sending.lower() != "true":
            print("By default, you will not be alerted of any variation")
            self.smtp_sending = False
        else:
            self.smtp_sending = True
        
        try:
            self.db_port = int(self.db_port)
        except Exception:
            print("DB port must be a number")
            return False
        
        try:
            self.refresh_time = int(self.refresh_time)
        except Exception:
            print("Refresh time must be a number")
            return False
        
        if self.following is None or self.following.lower() != "false":
            self.following = True
        else:
            self.following = False
        
        if self.make_trade is None or self.make_trade.lower() != "true":
            print("By default, no new trade will be done on your behalf")
            self.make_trade = False
        else:
            self.make_trade = True
        
        self.database = db.Mongo(self.db_hostname, self.db_port, self.db_name, self.db_user, self.db_password)
        
        if self.watching_currencies is not None:
            self.watching_currencies = self.watching_currencies.split(',')
        
        if self.ignore_currencies is not None:
            self.ignore_currencies = self.ignore_currencies.split(',')
        
        if self.smtp_sending == True:
            try:
                self.smtp_port = int(self.smtp_port)
            except Exception:
                print("SMTP port must be a number")
                return False
        
        self.actualize()
        
        try:
            self.min_recovered = float(self.min_recovered)
            self.min_profit = float(self.min_profit)
            self.max_danger = int(self.max_danger)
            self.taxe_rate = float(self.taxe_rate)
            self.max_concurrent_trades = int(self.max_concurrent_trades)
        except Exception:
            print("Error while converting parameters from string")
            return False

        return True
    