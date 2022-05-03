import time
import datetime

from datetime import timedelta
from lastversion import has_update

def stop(exchange_client, crypto, account, taxe_rate):
    percentage = exchange_client.stopTrade(crypto, account)
    if percentage == 0:
        return "Unable to stop trade on " + crypto.instrument_code + ".\n\n"
    
    account.available += crypto.current * percentage

    message = "Removed all current action on " + crypto.instrument_code + " at " + str(round(crypto.current, 2)) + "€"

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
    message = "\nDAILY STATS:\n\tTRADES:\t" + \
        str(account.dailyTrade) + "\n\tGAINED:\t" + \
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
    account.dailyTrade = 0
    
    today = datetime.datetime.now()
    if today.weekday() == 6:
        message += "\nWEEKLY STATS:\n\tTRADES:\t" + \
            str(account.weeklyTrade) + "\n\tGAINED:\t" + \
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
        account.weeklyTrade = 0
    
    if today.month != (today + timedelta(days=1)).month:
        message += "\nMONTHLY STATS:\n\tTRADES:\t" + \
            str(account.monthlyTrade) + "\n\tGAINED:\t" + \
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
        account.monthlyTrade = 0

    return message + "\n"

def checkUpdate(current_version):
    message = ""
    version = has_update(repo="hugotms/trader", at="github", current_version=current_version)
    if version != False:
        message = "############# UPDATE #############\n" + \
            "\nA new version of Trader is available ! It is highly recommended to upgrade.\n" + \
            "Currently, you are on version " + os.getenv('TRADER_VERSION') + " and latest is " + \
            str(version) + ".\nNote that this new version may include security patches, bug fixes and new features.\n"
    
    return message

def monitor(exchange_client, account, min_recovered, min_profit, max_danger, taxe_rate, delay):
    trading_message = ""

    for crypto in exchange_client.getAllActiveTrades(account, max_danger):
        print("Found " + crypto.instrument_code 
            + " (HIGHER: " + str(round(crypto.higher, 2)) 
            + "€ / CURRENT: " + str(round(crypto.current, 2)) 
            + "€ / DANGER: " + str(crypto.danger) 
            + " / VARIATION: " + str(round((1 - crypto.current / crypto.placed) * -100, 2))
            + "%)")

        if crypto.current < 10:
            trading_message += "No action can be done on " + crypto.instrument_code + " (less than 10€).\n\n"
        
        elif crypto.current * account.takerFee < crypto.higher * min_recovered:
            trading_message += "Loosing money on " + crypto.instrument_code + ". "
            trading_message += stop(exchange_client, crypto, account, taxe_rate)

        elif crypto.danger > max_danger:
            trading_message += crypto.instrument_code + " is too dangerous. "
            trading_message += stop(exchange_client, crypto, account, taxe_rate)
        
        elif crypto.danger >= max_danger % 2 and crypto.current * account.takerFee >= crypto.placed * min_profit:
            trading_message += crypto.instrument_code + " has reached its profit level. "
            trading_message += stop(exchange_client, crypto, account, taxe_rate)
        
        if delay < 0:
            crypto.loaded = False
            exchange_client.database.putInActive(crypto)
        
    exchange_client.actualizeAccount(account)

    if trading_message != "":
        return "############# TRADES #############\n\n" + trading_message
    
    return ""
