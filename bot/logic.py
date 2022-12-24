import time
import datetime
import json

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from lastversion import has_update

def stop(parameters, crypto):
    if parameters.exchange_client.stopTrade(crypto, parameters) == False:
        crypto.failed = True
        return "Unable to sell " + crypto.instrument_code + ".\n"

    message = "Selling market order for " + crypto.instrument_code + " at " + str(round(crypto.current, 2)) + "€"

    if crypto.current >= crypto.placed:
        message += " (WON: " + str(round(crypto.current - crypto.placed, 2)) + "€)"
    else:
        message += " (LOST: " + str(round(crypto.placed - crypto.current, 2)) + "€)"
    
    return message + ".\n"

def start(parameters, crypto, account):
    if parameters.exchange_client.makeTrade(crypto, account) == False:
        return ""
    
    account.available -= crypto.placed

    return "Buying market order for " + crypto.instrument_code + \
        " (OWNED: " + str(round(crypto.owned, crypto.precision)) + \
        " / PRICE: " + str(round(crypto.last_price, 2)) + \
        " / FMA: " + str(round(crypto.fma, 2)) + \
        " / SMA: " + str(round(crypto.sma, 2)) + \
        " / RSI: " + str(round(crypto.rsi)) + \
        ").\n"

def report(parameters):
    response = parameters.database.getPastPerformance(datetime.datetime.utcnow() - timedelta(days=1), parameters.watching_currencies, parameters.ignore_currencies)
    if response is None:
        return ""
    response = json.loads(response)

    message = "\nDAILY STATS:\n\tORDERS:\t" + \
        str(response["trades"]) + "\n\tGAINED:\t" + \
        str(round(response["profit"], 2)) + "€\n\tLOST:\t" + \
        str(round(response["loss"], 2)) + "€\n\tVOLUME:\t" + \
        str(round(response["volume"], 2)) + "€\n"

    if parameters.taxe_rate != 0.0:
        message += "\tTAXES:\t" + str(round(response["profit"] * parameters.taxe_rate, 2)) + \
            "€\n"

    if response["profit"] * (1 - parameters.taxe_rate) > response["loss"]:
        message += "\tPROFIT:\t" + str(round(response["profit"] * (1 - parameters.taxe_rate) - response["loss"], 2)) + \
            "€\n"
    
    today = datetime.datetime.now()
    if today.weekday() == 0:
        response = parameters.database.getPastPerformance(datetime.datetime.utcnow() - timedelta(weeks=1), parameters.watching_currencies, parameters.ignore_currencies)
        if response is None:
            return message
        response = json.loads(response)

        message += "\nWEEKLY STATS:\n\tORDERS:\t" + \
            str(response["trades"]) + "\n\tGAINED:\t" + \
            str(round(response["profit"], 2)) + "€\n\tLOST:\t" + \
            str(round(response["loss"], 2)) + "€\n\tVOLUME:\t" + \
            str(round(response["volume"], 2)) + "€\n"

        if parameters.taxe_rate != 0.0:
            message += "\tTAXES:\t" + str(round(response["profit"] * parameters.taxe_rate, 2)) + \
                "€\n"

        if response["profit"] * (1 - parameters.taxe_rate) > response["loss"]:
            message += "\tPROFIT:\t" + str(round(response["profit"] * (1 - parameters.taxe_rate) - response["loss"], 2)) + \
                "€\n"
    
    if today.month != (today + timedelta(days=1)).month:
        response = parameters.database.getPastPerformance(datetime.datetime.utcnow() - relativedelta(months=1), parameters.watching_currencies, parameters.ignore_currencies)
        if response is None:
            return message
        response = json.loads(response)

        message += "\nMONTHLY STATS:\n\tORDERS:\t" + \
            str(response["trades"]) + "\n\tGAINED:\t" + \
            str(round(response["profit"], 2)) + "€\n\tLOST:\t" + \
            str(round(response["loss"], 2)) + "€\n\tVOLUME:\t" + \
            str(round(response["volume"], 2)) + "€\n"

        if parameters.taxe_rate != 0.0:
            message += "\tTAXES:\t" + str(round(response["profit"] * parameters.taxe_rate, 2)) + \
                "€\n"

        if response["profit"] * (1 - parameters.taxe_rate) > response["loss"]:
            message += "\tPROFIT:\t" + str(round(response["profit"] * (1 - parameters.taxe_rate) - response["loss"], 2)) + \
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

def monitor(parameters):
    trading_message = ""
    trading_alert = ""

    for crypto in parameters.exchange_client.getAllActiveTrades(parameters):
        print("Found " + crypto.instrument_code 
            + " (HIGHER: " + str(round(crypto.higher, 2)) 
            + "€ / CURRENT: " + str(round(crypto.current, 2)) 
            + "€ / VARIATION: " + str(round((1 - crypto.current / crypto.placed) * -100, 2))
            + "% / RSI: " + str(round(crypto.rsi, 1))
            + ")")

        if crypto.current < 10:
            trading_message += "No action can be done on " + crypto.instrument_code + " (less than 10€).\n"
        
        elif crypto.current < crypto.higher * parameters.min_recovered:
            trading_message += "Loosing money on " + crypto.instrument_code + ". "
            trading_message += stop(parameters, crypto)
        
        elif crypto.rsi > parameters.overbought_threshold and crypto.fma > crypto.last_price > 0:
            trading_message += crypto.instrument_code + " is overbought. "
            trading_message += stop(parameters, crypto)
        
        elif crypto.fma < crypto.sma:
            trading_message += "Trend of " + crypto.instrument_code + " is going down. "
            trading_message += stop(parameters, crypto)
        
        elif parameters.min_profit > 1.0 and crypto.current >= crypto.placed * parameters.min_profit:
            trading_message += crypto.instrument_code + " has reached its profit level. "
            trading_message += stop(parameters, crypto)
        
        elif crypto.higher * parameters.min_recovered > 10 and (crypto.higher == crypto.current or crypto.stop_id == ""):
            parameters.exchange_client.incrementTrade(crypto, parameters)
        
        if crypto.failed == True and crypto.alerted == False:
            trading_alert += "No action can be done on " + crypto.instrument_code + " due to an error.\n"
            crypto.alerted = True
        
        parameters.database.putInActive(crypto)

    if trading_message != "":
        print(trading_message)
    
    return trading_alert

def buy(parameters, account):
    trading_message = ""

    if account.available * account.takerFee * account.makerFee * parameters.min_recovered < 10:
        return None

    for crypto in parameters.exchange_client.findProfitable(parameters, account):

        if crypto.danger < 1:
            crypto.danger = 1

        if crypto.rsi > parameters.oversold_threshold:
            continue

        if (account.available / crypto.danger) * account.takerFee * account.makerFee * parameters.min_recovered * (1 - (crypto.rsi / 100)) < 10:
            continue

        if crypto.last_price > crypto.fma > crypto.sma:
            trading_message += start(parameters, crypto, account)

    if trading_message != "":
        print(trading_message)
