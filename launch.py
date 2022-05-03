import os
import time
import datetime

from server import exchange
from server import mail
from bot import logic

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

while isOk == True:
    subject = "New trading update - " + time.strftime("%d/%m/%Y - %H:%M:%S")
    message = logic.monitor(client, account, min_recovered, min_profit, max_danger, taxe_rate)

    if report_send == True and datetime.time(00,00) <= datetime.datetime.now().time() <= datetime.time(hours,00):
        message += "############# REPORT #############\n"
        message += logic.report(account, taxe_rate)
        report_send = False

    if latest_release is not None and message != "":
        message += logic.checkUpdate()

    if smtp is not None and message != "":
        smtp.send(subject=subject, plain=message)

    if message != "":
        print("\n" + subject)
        print("\n" + message)

    if (delay > 0):
        delay -= refresh_time
    else:
        delay = seconds_in_delay
        report_send = True

    time.sleep(refresh_time)
