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

report_send = True

while isOk == True:
    subject = "New trading update - " + time.strftime("%d/%m/%Y - %H:%M:%S")
    message = logic.monitor(
            parameters.exchange_client, 
            account, 
            parameters.min_recovered, 
            parameters.min_profit, 
            parameters.max_danger, 
            parameters.taxe_rate,
            delay
        )

    if report_send == True and datetime.time(00,00) <= datetime.datetime.now().time() <= datetime.time(hours,00):
        message += "############# REPORT #############\n"
        message += logic.report(account, parameters.taxe_rate)
        report_send = False

    if parameters.latest_bot_release is not None and message != "":
        message += logic.checkUpdate(parameters.latest_bot_release)

    if parameters.smtp is not None and message != "":
        parameters.smtp.send(subject=subject, plain=message)

    if message != "":
        print("\n" + subject)
        print("\n" + message)

    if (delay > 0):
        delay -= parameters.refresh_time
    else:
        delay = seconds_in_delay
        report_send = True

    time.sleep(parameters.refresh_time)

    parameters.actualize()
