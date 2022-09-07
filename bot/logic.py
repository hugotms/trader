import time
import datetime
import json

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from lastversion import has_update

def stop(exchange_client, crypto, taxe_rate):
    if exchange_client.stopTrade(crypto) == False:
        crypto.failed = True
        return "Unable to stop trade on " + crypto.instrument_code + ".\n"

    message = "Removed all current action on " + crypto.instrument_code + " at " + str(round(crypto.current, 2)) + "€"

    if crypto.current > crypto.placed and taxe_rate != 0.0:
        profit = crypto.current - crypto.placed
        message += " (NET: " + str(round(profit * (1 - taxe_rate), 2)) + "€ / TAXES: " + \
            str(round(profit * taxe_rate, 2)) + "€)"
    elif crypto.current > crypto.placed:
        message += " (WON: " + str(round(crypto.current - crypto.placed, 2)) + "€)"
    elif crypto.current < crypto.placed:
        message += " (LOST: " + str(round(crypto.placed - crypto.current, 2)) + "€)"
    
    return message + ".\n"

def start(exchange_client, crypto, account):
    if exchange_client.makeTrade(crypto, account) == False:
        return ""
    
    account.available -= crypto.placed

    return "Placed action on " + crypto.instrument_code + " (OWNED: " + str(round(crypto.owned, 4)) + ").\n"

def report(database, watching_currencies, ignore_currencies, taxe_rate):
    response = database.getPastPerformance(datetime.datetime.utcnow() - timedelta(days=1), watching_currencies, ignore_currencies)
    if response is None:
        return ""
    response = json.loads(response)

    message = "\nDAILY STATS:\n\tORDERS:\t" + \
        str(response["trades"]) + "\n\tGAINED:\t" + \
        str(round(response["profit"], 2)) + "€\n\tLOST:\t" + \
        str(round(response["loss"], 2)) + "€\n\tVOLUME:\t" + \
        str(round(response["volume"], 2)) + "€\n"

    if taxe_rate != 0.0:
        message += "\tTAXES:\t" + str(round(response["profit"] * taxe_rate, 2)) + \
            "€\n"

    if response["profit"] * (1 - taxe_rate) > response["loss"]:
        message += "\tPROFIT:\t" + str(round(response["profit"] * (1 - taxe_rate) - response["loss"], 2)) + \
            "€\n"
    
    today = datetime.datetime.now()
    if today.weekday() == 0:
        response = database.getPastPerformance(datetime.datetime.utcnow() - timedelta(weeks=1), watching_currencies, ignore_currencies)
        if response is None:
            return message
        response = json.loads(response)

        message += "\nWEEKLY STATS:\n\tORDERS:\t" + \
            str(response["trades"]) + "\n\tGAINED:\t" + \
            str(round(response["profit"], 2)) + "€\n\tLOST:\t" + \
            str(round(response["loss"], 2)) + "€\n\tVOLUME:\t" + \
            str(round(response["volume"], 2)) + "€\n"

        if taxe_rate != 0.0:
            message += "\tTAXES:\t" + str(round(response["profit"] * taxe_rate, 2)) + \
                "€\n"

        if response["profit"] * (1 - taxe_rate) > response["loss"]:
            message += "\tPROFIT:\t" + str(round(response["profit"] * (1 - taxe_rate) - response["loss"], 2)) + \
                "€\n"
    
    if today.month != (today + timedelta(days=1)).month:
        response = database.getPastPerformance(datetime.datetime.utcnow() - relativedelta(months=1), watching_currencies, ignore_currencies)
        if response is None:
            return message
        response = json.loads(response)

        message += "\nMONTHLY STATS:\n\tORDERS:\t" + \
            str(response["trades"]) + "\n\tGAINED:\t" + \
            str(round(response["profit"], 2)) + "€\n\tLOST:\t" + \
            str(round(response["loss"], 2)) + "€\n\tVOLUME:\t" + \
            str(round(response["volume"], 2)) + "€\n"

        if taxe_rate != 0.0:
            message += "\tTAXES:\t" + str(round(response["profit"] * taxe_rate, 2)) + \
                "€\n"

        if response["profit"] * (1 - taxe_rate) > response["loss"]:
            message += "\tPROFIT:\t" + str(round(response["profit"] * (1 - taxe_rate) - response["loss"], 2)) + \
                "€\n"

    return message + "\n"

def checkUpdate(current_version):
    message = ""
    version = has_update(repo="hugotms/trader", at="github", current_version=current_version)
    if version != False:
        message = "A new version of Trader is available ! It is highly recommended to upgrade.\n\n" + \
            "Currently, you are on version " + current_version + " and latest is " + \
            str(version) + ".\n\nNote that this new version may include security patches, bug fixes and new features."
    
    return message

def monitor(exchange_client, min_recovered, min_profit, fma_unit, sma_unit, overbought_threshold, taxe_rate):
    trading_message = ""
    trading_alert = ""

    for crypto in exchange_client.getAllActiveTrades(fma_unit, sma_unit):
        print("Found " + crypto.instrument_code 
            + " (HIGHER: " + str(round(crypto.higher, 2)) 
            + "€ / CURRENT: " + str(round(crypto.current, 2)) 
            + "€ / VARIATION: " + str(round((1 - crypto.current / crypto.placed) * -100, 2))
            + "%)")

        if crypto.current < 10:
            trading_message += "No action can be done on " + crypto.instrument_code + " (less than 10€).\n"
        
        elif crypto.current < crypto.higher * min_recovered:
            trading_message += "Loosing money on " + crypto.instrument_code + ". "
            trading_message += stop(exchange_client, crypto, taxe_rate)
        
        elif crypto.rsi > overbought_threshold:
            trading_message += crypto.instrument_code + " is overbought. "
            trading_message += stop(exchange_client, crypto, taxe_rate)

        elif crypto.fma < crypto.sma:
            trading_message += crypto.instrument_code + " trend is going down. "
            trading_message += stop(exchange_client, crypto, taxe_rate)
        
        elif min_profit > 1.0 and crypto.current >= crypto.placed * min_profit:
            trading_message += crypto.instrument_code + " has reached its profit level. "
            trading_message += stop(exchange_client, crypto, taxe_rate)
        
        elif crypto.higher * min_recovered > 10 and (crypto.higher == crypto.current or crypto.stop_id == ""):
            exchange_client.incrementTrade(crypto, min_recovered)
        
        if crypto.failed == True and crypto.alerted == False:
            trading_alert += "No action can be done on " + crypto.instrument_code + " due to an error.\n"
            crypto.alerted = True
        
        exchange_client.database.putInActive(crypto)

    if trading_message != "":
        print(trading_message)
    
    return trading_alert

def trade(exchange_client, account, max_danger, max_concurrent_currencies, fma_unit, sma_unit, oversold_threshold, min_recovered, wait_time):
    trading_message = ""

    if account.available * account.takerFee * account.makerFee * min_recovered < 10:
        return None

    for crypto in exchange_client.findProfitable(max_concurrent_currencies, fma_unit, sma_unit, max_danger, min_recovered, account, wait_time):

        if crypto.danger < 1:
            crypto.danger = 1

        if account.available * account.takerFee * account.makerFee * min_recovered / crypto.danger < 10:
            continue

        if crypto.rsi < oversold_threshold and crypto.fma > crypto.sma:
            trading_message += start(exchange_client, crypto, account)

    if trading_message != "":
        print(trading_message)
