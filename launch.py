import time
import datetime

from jinja2 import Environment, FileSystemLoader

from data import params
from bot import logic

def start():
    account = None
    parameters = params.Params()
    isOk = parameters.new()

    if isOk == True:
        account = parameters.exchange_client.getAccount()

    if account is None:
        isOk = False

    seconds_in_delay = 3600
    delay = seconds_in_delay

    report_send = False

    environment = Environment(loader=FileSystemLoader("templates/"))

    while isOk == True:
        subject = "New trading update - " + time.strftime("%d/%m/%Y")
        message = ""
        body = ""
        
        alerts = logic.monitor(parameters)
        
        if alerts != "":
            message += "############# ALERTS #############\n\n"
            message += alerts + "\n"
            body += environment.get_template("alerts.html.j2").render(text=alerts)
        
        parameters.exchange_client.actualizeAccount(account)

        if parameters.make_trade == True:
            logic.trade(parameters, account)

        if report_send == True and datetime.time(00,00) <= datetime.datetime.now().time() <= datetime.time(00,59):
            report_message = logic.report(parameters)
            message += "############# REPORT #############\n"
            message += report_message
            body += environment.get_template("reports.html.j2").render(text=report_message)

        update_message = ""
        if parameters.latest_bot_release is not None and message != "":
            update_message = logic.checkUpdate(parameters.latest_bot_release)
        
        if update_message != "":
            message += "############# UPDATE #############\n\n"
            message += update_message
            body += environment.get_template("version.html.j2").render(text=update_message)

        if parameters.smtp is not None and message != "":
            html = environment.get_template("base.html.j2").render(body=body)
            parameters.smtp.send(subject=subject, plain=message, html=html)

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

if __name__ == '__main__':
    start()
