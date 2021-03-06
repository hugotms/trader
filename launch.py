import time
import datetime

from data import params
from bot import logic

account = None
parameters = params.Params()
isOk = parameters.new()

if isOk == True:
    account = parameters.exchange_client.getAccount()

if account is None:
    isOk = False

# 2 hours delay between full danger calculation
hours = 2
seconds_in_delay = hours * 3600
delay = seconds_in_delay

report_send = False

while isOk == True:
    subject = "New trading update - " + time.strftime("%d/%m/%Y")
    message = ""
    
    logic.monitor(
            parameters.exchange_client, 
            account, 
            parameters.min_recovered, 
            parameters.min_profit, 
            parameters.max_danger, 
            parameters.taxe_rate,
            delay,
            parameters.refresh_time
        )
    
    parameters.exchange_client.actualizeAccount(account)

    if parameters.make_trade == True:
        logic.trade(
            parameters.exchange_client, 
            account, 
            parameters.max_danger, 
            parameters.max_concurrent_trades,
            parameters.min_recovered,
            parameters.refresh_time
        )

    if report_send == True and datetime.time(00,00) <= datetime.datetime.now().time() <= datetime.time(hours - 1,59):
        message += "############# REPORT #############\n"
        message += logic.report(
            parameters.database, 
            parameters.watching_cryptos, 
            parameters.ignore_cryptos, 
            parameters.watching_currencies, 
            parameters.taxe_rate
        )

    if parameters.latest_bot_release is not None and message != "":
        message += logic.checkUpdate(parameters.latest_bot_release)

    if parameters.smtp is not None and message != "":
        parameters.smtp.send(subject=subject, plain=message)

    if message != "":
        print("\n" + subject)
        print("\n" + message)

    if (delay > 0):
        delay -= parameters.refresh_time * 60
        report_send = False
    else:
        delay = seconds_in_delay
        report_send = True

    time.sleep(parameters.refresh_time * 60)

    parameters.actualize()
