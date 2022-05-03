import os
import time
import datetime

from datetime import timedelta
from lastversion import has_update

from server import exchange
from server import mail

def stop(exchange_client, crypto, account, taxe_rate):
    percentage = exchange_client.stopTrade(crypto, account)
    if percentage == 0:
        return "Unable to stop trade on " + crypto.cryptoName + ".\n\n"
    
    account.available += crypto.current * percentage

    message = "Removed all current action on " + crypto.cryptoName + " at " + str(round(crypto.current, 2)) + "€"

    if crypto.current * percentage > crypto.placed and taxe_rate != 0.0:
        profit = crypto.current * percentage - crypto.placed
        account.addProfit(profit)
        message += " (NET: " + str(round(profit * (1 - taxe_rate), 2)) + "€ / TAXES: " + \
            str(round(profit * taxe_rate, 2)) + "€)"
    elif crypto.current * percentage > crypto.placed:
        profit = crypto.current * percentage - crypto.placed
        account.addProfit(profit)
        message += " (WON: " + str(round(crypto.current * percentage - crypto.placed, 2)) + "€)"
    elif crypto.current * percentage < crypto.placed:
        loss = crypto.placed - crypto.current * percentage
        account.addLoss(loss)
        message += " (LOST: " + str(round(loss, 2)) + "€)"
    
    return message + ".\n\n"

def report(account, taxe_rate):
    message = "\nDAILY STATS:\n\tGAINED:\t" + \
        str(round(account.dailyProfit, 2)) + "€\n\tLOST:\t" + \
        str(round(account.dailyLoss, 2)) + "€\n"

    if taxe_rate != 0.0:
        message += "\tTAXES:\t" + str(round(account.dailyProfit * taxe_rate, 2)) + \
            "€\n"

    if account.dailyProfit * (1 - taxe_rate) > account.dailyLoss:
        message += "\tPROFIT:\t" + str(round(account.dailyProfit * (1 - taxe_rate) - account.dailyLoss, 2)) + \
            "€\n"
    
    account.dailyProfit = 0
    account.dailyLoss = 0
    
    today = datetime.datetime.now()
    if today.weekday() == 6:
        message += "\nWEEKLY STATS:\n\tGAINED:\t" + \
            str(round(account.weeklyProfit, 2)) + "€\n\tLOST:\t" + \
            str(round(account.weeklyLoss, 2)) + "€\n"

        if taxe_rate != 0.0:
            message += "\tTAXES:\t" + str(round(account.weeklyProfit * taxe_rate, 2)) + \
                "€\n"

        if account.weeklyProfit * (1 - taxe_rate) > account.weeklyLoss:
            message += "\tPROFIT:\t" + str(round(account.weeklyProfit * (1 - taxe_rate) - account.weeklyLoss, 2)) + \
                "€\n" 
    
        account.weeklyProfit = 0
        account.weeklyLoss = 0
    
    if today.month != (today + timedelta(days=1)).month:
        message += "\nMONTHLY STATS:\n\tGAINED:\t" + \
            str(round(account.monthlyProfit, 2)) + "€\n\tLOST:\t" + \
            str(round(account.monthlyLoss, 2)) + "€\n"

        if taxe_rate != 0.0:
            message += "\tTAXES:\t" + str(round(account.monthlyProfit * taxe_rate, 2)) + \
                "€\n"

        if account.monthlyProfit * (1 - taxe_rate) > account.monthlyLoss:
            message += "\tPROFIT:\t" + str(round(account.monthlyProfit * (1 - taxe_rate) - account.monthlyLoss, 2)) + \
                "€\n" 
    
        account.monthlyProfit = 0
        account.monthlyLoss = 0

    return message + "\n"

def checkUpdate():
    message = ""
    version = has_update(repo="hugotms/trader", at="github", current_version=os.getenv('TRADER_VERSION'))
    if version != False:
        message = "############# UPDATE #############\n" + \
            "\nA new version of Trader is available ! It is highly recommended to upgrade.\n" + \
            "Currently, you are on version " + os.getenv('TRADER_VERSION') + " and latest is " + \
            str(version) + ".\nNote that this new version may include security patches, bug fixes and new features.\n"
    
    return message
        
isOk = True

min_recovered = os.getenv('MIN_RECOVERED_RATE')
min_profit = os.getenv('MIN_PROFIT_RATE')
max_danger = os.getenv('MAX_DANGER')
refresh_time = os.getenv('MINUTES_REFRESH_TIME')
taxe_rate = os.getenv('TAXE_RATE')
smtp_sending = os.getenv('SEND_ALERT_MAIL')
latest_release = os.getenv('TRADER_VERSION')

if min_recovered is None:
    print("Default recovered rate is 0.95")
    min_recovered = 0.95
min_recovered = float(min_recovered)

if min_profit is None:
    print("Default profit rate is 1.05")
    min_profit = 1.05
min_profit = float(min_profit)

if max_danger is None:
    print("Default max danger is 10")
    max_danger = 10
max_danger = int(max_danger)

if refresh_time is None:
    print("Default refresh time is 10 minutes")
    refresh_time = 10
refresh_time = int(refresh_time) * 60

if taxe_rate is None:
    print("Defaut taxe rate is 0.0")
    taxe_rate = 0.0
taxe_rate = float(taxe_rate)

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

if smtp_sending == True:
    smtp = mail.SMTP().new()
    if smtp is None:
        isOk = False

if account is None:
    isOk = False

# 2 hours delay between full danger calculation
hours = 2
seconds_in_delay = hours * 3600
delay = seconds_in_delay

report_send = False

while isOk:
    subject = "New trading update - " + time.strftime("%d/%m/%Y - %H:%M:%S")
    message = ""
    trading_message = ""

    for crypto in client.getAllActiveTrades(account, max_danger):
        print("Found " + crypto.cryptoName 
            + " (HIGHER: " + str(round(crypto.higher, 2)) 
            + "€ / CURRENT: " + str(round(crypto.current, 2)) 
            + "€ / DANGER: " + str(crypto.danger) 
            + " / VARIATION: " + str(round((1 - crypto.current / crypto.placed) * -100, 2))
            + "%)")

        if crypto.current < 10:
            trading_message += "No action can be done on " + crypto.cryptoName + " (less than 10€).\n\n"
        
        elif crypto.current * account.takerFee < crypto.higher * min_recovered:
            trading_message += "Loosing money on " + crypto.cryptoName + ". "
            trading_message += stop(client, crypto, account, taxe_rate)

        elif crypto.danger > max_danger:
            trading_message += crypto.cryptoName + " is too dangerous. "
            trading_message += stop(client, crypto, account, taxe_rate)
        
        elif crypto.danger >= max_danger % 2 and crypto.current * account.takerFee >= crypto.placed * min_profit:
            trading_message += crypto.cryptoName + " has reached its profit level. "
            trading_message += stop(client, crypto, account, taxe_rate)
        
        if delay < 0:
            crypto.loaded = False
    
    if trading_message != "":
        message += "############# TRADES #############\n\n"
    
    message += trading_message
    
    report_message = ""
    if report_send == True and datetime.time(00,00) <= datetime.datetime.now().time() <= datetime.time(hours,00):
        report_message = report(account, taxe_rate)
        report_send = False
        message += "############# REPORT #############\n"
    
    message += report_message

    if latest_release is not None and message != "":
        message += checkUpdate()

    if smtp_sending == True and message != "":
        smtp.send(subject=subject, plain=message)
    
    if message != "":
        print("\n" + subject)
        print("\n" + message)

    client.actualizeAccount(account)

    if (delay > 0):
        delay -= refresh_time
    else:
        delay = seconds_in_delay
        report_send = True

    time.sleep(refresh_time)
