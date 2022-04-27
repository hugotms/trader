import os
import time

from server import exchange
from server import mail

def stop(exchange_client, crypto, account):
    percentage = exchange_client.stopTrade(crypto, account)
    if percentage == 0:
        print("Unable to stop trade on " + crypto.cryptoName)
        return "Unable to stop trade on " + crypto.cryptoName + "\n"
    
    account.amount += crypto.current * percentage

    message = "Removed all current action on " + crypto.cryptoName + " at " + str(round(crypto.current, 2)) + "€"

    if crypto.current * percentage > crypto.placed:
        message = message + " (NET: " + str(round(crypto.current * percentage * 0.7, 2)) + "€ / TAXES: " + \
            str(round(crypto.current * percentage * 0.3, 2)) + "€)"
    
    return message + "\n"
        
isOk = True

min_recovered = os.getenv('MIN_RECOVERED_RATE')
min_profit = os.getenv('MIN_PROFIT_RATE')
max_danger = os.getenv('MAX_DANGER')
refresh_time = os.getenv('MINUTES_REFRESH_TIME')
smtp_sending = os.getenv('SEND_ALERT_MAIL')

if min_recovered is None:
    print("Default recovered rate is 0.9")
    min_recovered = 0.9
min_recovered = float(min_recovered)

if min_profit is None:
    print("Default profit rate is 1.01")
    min_profit = 1.01
min_profit = float(min_profit)

if max_danger is None:
    print("Default max danger is 10")
    max_danger = 10
max_danger = int(max_danger)

if refresh_time is None:
    print("Default refresh time is 10 minutes")
    refresh_time = 10
refresh_time = int(refresh_time) * 60

if smtp_sending is None or smtp_sending.lower() != "true":
    print("By default, you will not be alerted of any variation")
    smtp_sending = False
else:
    smtp_sending = True

client = exchange.BitpandaPro().new()

smtp = None
account = None

if client is not None:
    account = client.getAccount()

if smtp_sending:
    smtp = mail.SMTP().new()
    if smtp is None:
        isOk = False

if account is None:
    isOk = False

# 2 hours delay between full danger calculation
# First run to be executed will be longer than others
seconds_in_delay = 2 * 3600
delay = seconds_in_delay

listCrypto = []

while isOk:
    subject = "New trades done on " + time.strftime("%d/%m/%Y - %H:%M:%S")
    message = ""

    listCrypto = client.getAllActiveTrades(listCrypto, account, max_danger)
    for crypto in listCrypto:
        print("Found " + crypto.cryptoName)

        if crypto.current < 10:
            print("No action can be done on " + crypto.cryptoName)
        
        elif crypto.current * account.takerFee < crypto.higher * min_recovered:
            print("Loosing money on " + crypto.cryptoName)
            message += stop(client, crypto, account)

        elif crypto.danger > max_danger:
            print(crypto.cryptoName + " is too dangerous")
            message += stop(client, crypto, account)
        
        elif crypto.danger >= max_danger % 2 and crypto.current * account.takerFee >= crypto.placed * min_profit:
            print(crypto.cryptoName + " has reached its profit level")
            message += stop(client, crypto, account)
        
        if delay < 0:
            crypto.loaded = False
    
    if smtp_sending == True and message != "":
        if not smtp.send(subject=subject, message=message):
            print("Unable to send mail to destinary address")

    account.actualize(client)

    if (delay > 0):
        delay -= refresh_time
    else:
        delay = seconds_in_delay

    time.sleep(refresh_time)
