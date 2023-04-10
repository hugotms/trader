import json

from data import assets

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
        
        elif crypto.rsi >= parameters.overbought_threshold and crypto.adl <= -1:
            trading_message += crypto.instrument_code + " is overbought. "
            trading_message += stop(parameters, crypto)
        
        elif crypto.rsi < parameters.oversold_threshold and crypto.adl <= -1:
            trading_message += crypto.instrument_code + " is oversold. "
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

        if crypto.rsi < 50:
            continue

        if crypto.rsi >= parameters.overbought_threshold:
            continue

        if crypto.adl < 1:
            continue

        if crypto.sma >= crypto.fma:
            continue

        if crypto.fma >= crypto.last_price:
            continue

        if (parameters.account.available / crypto.danger) * parameters.account.takerFee * parameters.account.makerFee * parameters.security_min_recovered < 10:
            continue
        
        trading_message += start(parameters, crypto)

    if trading_message != "":
        print(trading_message)
