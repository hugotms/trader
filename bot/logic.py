import time
import datetime
import json

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from lastversion import has_update

from data import assets
from data import reports

def stop(parameters, crypto):
    if parameters.exchange_client.sellingMarketOrder(crypto, parameters) == False:
        crypto.failed = True
        parameters.database.putInActive(crypto)
        return "Unable to sell " + crypto.instrument_code + ".\n"

    message = "Selling market order for " + crypto.instrument_code + " at " + str(round(crypto.current * parameters.account.takerFee, 2)) + "€"

    if crypto.current * parameters.account.takerFee >= crypto.placed:
        message += " (WON: " + str(round((crypto.current * parameters.account.takerFee) - crypto.placed, 2)) + "€)"
    else:
        message += " (LOST: " + str(round(crypto.placed - (crypto.current * parameters.account.takerFee), 2)) + "€)"
    
    return message + ".\n"

def start(parameters, crypto):
    if parameters.exchange_client.buyingMarketOrder(crypto, parameters) == False:
        return ""
    
    parameters.account.available -= crypto.placed

    return "Buying market order for " + crypto.instrument_code + \
        " (OWNED: " + str(round(crypto.owned, crypto.precision)) + \
        " / PRICE: " + str(round(crypto.last_price, crypto.precision)) + \
        " / FMA: " + str(round(crypto.fma, crypto.precision)) + \
        " / SMA: " + str(round(crypto.sma, crypto.precision)) + \
        " / RSI: " + str(round(crypto.rsi)) + \
        " / ADL: " + str(round(crypto.adl)) + \
        ").\n"

def getHistory(parameters):
    report_data = [None, None, None]
    report_data[0] = reports.Report(datetime.datetime.utcnow() - timedelta(days=1))

    today = datetime.datetime.now()
    if today.weekday() == 0:
        report_data[1] = reports.Report(datetime.datetime.utcnow() - timedelta(weeks=1))
    
    if today.month != (today + timedelta(days=1)).month:
        report_data[2] = reports.Report(datetime.datetime.utcnow() - relativedelta(months=1))

    for report in report_data:
        if report is None:
            continue

        response = response = parameters.database.getPastPerformance(report, parameters.watching_currencies, parameters.ignore_currencies)
        if response is None:
            continue

        for item in response:
            report.list.append(assets.Crypto(
                item["instrument_code"],
                item["base"],
                item["currency"],
                float(item["owned"]),
                float(item["placed"]),
                float(item["current"]),
                item["placed_on"]
                )
            )

    return report_data

def report(parameters, report_data):
    message = "\nDAILY STATS:\n\tORDERS:\t" + \
        str(report_data[0].orders) + "\n\tGAINED:\t" + \
        str(round(report_data[0].gain, 2)) + "€\n\tLOST:\t" + \
        str(round(report_data[0].loss, 2)) + "€\n\tVOLUME:\t" + \
        str(round(report_data[0].volume, 2)) + "€\n"

    if report_data[0].gain > report_data[0].loss:
        message += "\tPROFIT:\t" + str(round(report_data[0].gain - report_data[0].loss, 2)) + \
            "€\n"
    
    if report_data[1] != None:

        message += "\nWEEKLY STATS:\n\tORDERS:\t" + \
            str(report_data[1].orders) + "\n\tGAINED:\t" + \
            str(round(report_data[1].gain, 2)) + "€\n\tLOST:\t" + \
            str(round(report_data[1].loss, 2)) + "€\n\tVOLUME:\t" + \
            str(round(report_data[1].volume, 2)) + "€\n"

        if report_data[1].gain > report_data[1].loss:
            message += "\tPROFIT:\t" + str(round(report_data[1].gain - report_data[1].loss, 2)) + \
                "€\n"
    
    if report_data[2] != None:
        message += "\nMONTHLY STATS:\n\tORDERS:\t" + \
            str(report_data[2].orders) + "\n\tGAINED:\t" + \
            str(round(report_data[2].gain, 2)) + "€\n\tLOST:\t" + \
            str(round(report_data[2].loss, 2)) + "€\n\tVOLUME:\t" + \
            str(round(report_data[2].volume, 2)) + "€\n"

        if report_data[2].gain > report_data[2].loss:
            message += "\tPROFIT:\t" + str(round(report_data[2].gain - report_data[2].loss, 2)) + \
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

def monitor(parameters, actives):
    trading_message = ""
    trading_alert = ""

    for crypto in actives:
        print("Found " + crypto.instrument_code 
            + " (HIGHER: " + str(round(crypto.higher, 2)) 
            + "€ / CURRENT: " + str(round(crypto.current, 2)) 
            + "€ / VARIATION: " + str(round((1 - crypto.current / crypto.placed) * -100, 2))
            + "%).")

        if crypto.current < 10:
            trading_message += "No action can be done on " + crypto.instrument_code + " (less than 10€).\n"
        
        elif crypto.current * parameters.account.takerFee < crypto.higher * parameters.min_recovered:
            trading_message += "Loosing money on " + crypto.instrument_code + ". "
            trading_message += stop(parameters, crypto)
        
        elif crypto.rsi > parameters.overbought_threshold and crypto.adl <= -1:
            trading_message += crypto.instrument_code + " is overbought. "
            trading_message += stop(parameters, crypto)
        
        elif crypto.sma > crypto.last_price and crypto.adl <= -1:
            trading_message += "Trend of " + crypto.instrument_code + " is going down. "
            trading_message += stop(parameters, crypto)
        
        elif parameters.min_profit > 1.0 and crypto.current * parameters.account.takerFee >= crypto.placed * parameters.min_profit:
            trading_message += crypto.instrument_code + " has reached its profit level. "
            trading_message += stop(parameters, crypto)
        
        elif crypto.higher * parameters.min_recovered > 10 and (crypto.higher == crypto.current or crypto.stop_id == ""):
            parameters.exchange_client.stopLossOrder(crypto, parameters)
        
        if crypto.failed == True and crypto.alerted == False:
            trading_alert += "No action can be done on " + crypto.instrument_code + " due to an error.\n"
            crypto.alerted = True
            parameters.database.putInActive(crypto)

    if trading_message != "":
        print(trading_message)
    
    return trading_alert

def buy(parameters, profitables):
    trading_message = ""

    for crypto in profitables:

        if crypto.rsi > parameters.oversold_threshold:
            continue

        if crypto.adl < 1:
            continue

        if crypto.sma >= crypto.last_price:
            continue

        if (parameters.account.available / crypto.danger) * parameters.account.takerFee * parameters.account.makerFee * parameters.security_min_recovered * (1 - (crypto.rsi / 100)) < 10:
            continue
        
        trading_message += start(parameters, crypto)

    if trading_message != "":
        print(trading_message)
