import os

from server import db
from server.exchanges import bitpanda_pro, history, paper_trading
from server import mail

class Params:

    def __init__(self):
        self.exchange_type = os.getenv('EXCHANGE_TYPE')
        self.exchange_api_key = os.getenv('EXCHANGE_API_KEY')
        self.exchange_input_filename = os.getenv('EXCHANGE_INPUT_FILENAME')
        self.init_capital = os.getenv('TEST_INIT_CAPITAL')

        self.db_hostname = os.getenv('MONGO_DB_HOST')
        self.db_port = os.getenv('MONGO_DB_PORT')
        self.db_name = os.getenv('MONGO_DB_NAME')
        self.db_user = os.getenv('MONGO_DB_USER')
        self.db_password = os.getenv('MONGO_DB_PASSWORD')

        self.min_recovered = os.getenv('MIN_RECOVERED_RATE')
        self.security_min_recovered = os.getenv('SECURITY_MIN_RECOVERED_RATE')
        self.min_profit = os.getenv('MIN_PROFIT_RATE')
        self.max_danger = os.getenv('MAX_DANGER')
        self.refresh_time = os.getenv('MINUTES_REFRESH_TIME')
        self.wait_time = os.getenv('MINUTES_WAIT_TIME')
        self.make_order = os.getenv('MAKE_ORDER')
        self.candlesticks_timeframe = os.getenv('CANDLESTICKS_TIMEFRAME')
        self.candlesticks_period = os.getenv('CANDLESTICKS_PERIOD')
        self.fma_unit = os.getenv('WINDOW_SIZE_FMA')
        self.sma_unit = os.getenv('WINDOW_SIZE_SMA')
        self.period = os.getenv('INDICATORS_PERIOD')
        self.oversold_threshold = os.getenv('OVERSOLD_THRESHOLD')
        self.overbought_threshold = os.getenv('OVERBOUGHT_THRESHOLD')

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
        self.account = None
    
    def actualize(self):
        self.watching_currencies = self.database.findVar("watching_currencies", self.watching_currencies, [])
        self.ignore_currencies = self.database.findVar("ignore_currencies", self.ignore_currencies, [])
        self.min_recovered = self.database.findVar("min_recovered", self.min_recovered, 0.95)
        self.security_min_recovered = self.database.findVar("security_min_recovered", self.security_min_recovered, 0.9)
        self.min_profit = self.database.findVar("min_profit", self.min_profit, 1.0)
        self.max_danger = self.database.findVar("max_danger", self.max_danger, 5)
        self.wait_time = self.database.findVar("wait_time", self.wait_time, 10)
        self.refresh_time = self.database.findVar("refresh_time", self.refresh_time, 10)
        self.make_order = self.database.findVar("make_order", self.make_order, False)
        self.candlesticks_timeframe = self.database.findVar("candlesticks_timeframe", self.candlesticks_timeframe, "DAYS")
        self.candlesticks_period = self.database.findVar("candlesticks_period", self.candlesticks_period, 1)
        self.fma_unit = self.database.findVar("fma_unit", self.fma_unit, 5)
        self.sma_unit = self.database.findVar("sma_unit", self.sma_unit, 50)
        self.period = self.database.findVar("period", self.period, 14)
        self.oversold_threshold = self.database.findVar("oversold_threshold", self.oversold_threshold, 30)
        self.overbought_threshold = self.database.findVar("overbought_threshold", self.overbought_threshold, 70)
        self.init_capital = self.database.findVar("test_init_capital", self.init_capital, 1000)

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
            self.refresh_time = int(self.refresh_time)
            self.wait_time = int(self.wait_time)
            self.min_recovered = float(self.min_recovered)
            self.security_min_recovered = float(self.security_min_recovered)
            self.min_profit = float(self.min_profit)
            self.max_danger = int(self.max_danger)
            self.make_order = bool(self.make_order)
            self.candlesticks_period = int(self.candlesticks_period)
            self.fma_unit = int(self.fma_unit)
            self.sma_unit = int(self.sma_unit)
            self.period = int(self.period)
            self.oversold_threshold = int(self.oversold_threshold)
            self.overbought_threshold = int(self.overbought_threshold)
        except Exception:
            print("Error while converting parameters from string")
            return False
        
        if self.security_min_recovered >= self.min_recovered:
            return False
        
        if self.refresh_time < 1:
            self.refresh_time = 1
        
        if self.exchange_type == "BITPANDA_PRO":
        
            if self.exchange_api_key is None:
                print("Required API key was not set")
                return False
            
            self.exchange_client = bitpanda_pro.Exchange(self.exchange_api_key)

            return True
        
        try:
            self.init_capital = float(self.init_capital)
        except Exception:
            print("Init capital must be a number")
            return False
        
        if self.exchange_type == "HISTORY":
            if self.exchange_input_filename is None:
                print("Required CSV file not set")
                return False
            
            frame = self.period + 1
            if frame < self.sma_unit + 10:
                frame = self.sma_unit + 10
            
            self.exchange_client = history.Exchange(self.init_capital, self.exchange_input_filename, frame, self.watching_currencies, self.ignore_currencies)

            return True
        
        if self.exchange_type == "PAPER_TRADING":
            self.exchange_client = paper_trading.Exchange(self.init_capital)

            return True

        print("No available exchanges selected")

        return False
    