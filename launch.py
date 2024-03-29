import time
import datetime

from jinja2 import Environment, FileSystemLoader

from data import params
from bot import logic
from server import fs

def start():
    parameters = params.Params()
    isOk = parameters.new()

    if isOk == True:
        parameters.account = parameters.exchange_client.getAccount()

    if parameters.account is None:
        isOk = False

    seconds_in_delay = 3600
    delay = seconds_in_delay

    report_send = False

    environment = Environment(loader=FileSystemLoader("templates/"))

    while isOk == True:
        subject = "New asset update - " + time.strftime("%d/%m/%Y")
        message = ""
        body = ""

        parameters.account.total = parameters.account.available

        reports = []
        if parameters.exchange_type != "HISTORY":
            reports = logic.getHistory(parameters)

        actives = parameters.exchange_client.getAllActiveAssets(parameters)

        alerts = logic.monitor(parameters, actives)
        
        if alerts != "":
            message += "############# ALERTS #############\n\n"
            message += alerts + "\n"
            body += environment.get_template("alerts.html.j2").render(text=alerts)
        
        parameters.exchange_client.actualizeAccount(parameters.account)

        profitables = parameters.exchange_client.findProfitable(parameters)

        sleep = 0
        if parameters.exchange_type != "HISTORY":

            actives_html = environment.get_template("actives.html.j2").render(list=actives)
            html_file = fs.File('output', 'index.html')
            
            if html_file.create() is None:
                print("Unable to create 'output/index.html' file. Please check permissions on filesystem")
                isOk = False

            html_file.putInFile(actives_html)

            profitables_html = environment.get_template("profitables.html.j2").render(list=profitables)
            html_file = fs.File('output', 'profitables.html')
            
            if html_file.create() is None:
                print("Unable to create 'output/profitables.html' file. Please check permissions on filesystem")
                isOk = False

            html_file.putInFile(profitables_html)

            for asset in actives:
                parameters.account.total += asset.current

            account_html = environment.get_template("account.html.j2").render(
                account=parameters.account,
                history=reports[0].list,
            )
            html_file = fs.File('output', 'account.html')
            
            if html_file.create() is None:
                print("Unable to create 'output/account.html' file. Please check permissions on filesystem")
                isOk = False

            html_file.putInFile(account_html)

            sleep = parameters.refresh_time * 60
        
        else:
            isOk = parameters.exchange_client.isOk

        if report_send == True and (datetime.time(00,00) <= datetime.datetime.now().time() <= datetime.time(00,59) or isOk == False):
            reports = logic.getHistory(parameters)
            report_message = logic.report(parameters, reports)
            message += "############# REPORT #############\n"
            message += report_message
            body += environment.get_template("reports.html.j2").render(text=report_message)
            delay = seconds_in_delay

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
            report_send = True
        
        if parameters.make_order == True and isOk:
            logic.buy(parameters, profitables)

        time.sleep(sleep)

        parameters.actualize()

        if parameters.exchange_type == "HISTORY" and not isOk:
            parameters.database.client.drop_collection("actives")
            parameters.database.client.drop_collection("history")

if __name__ == '__main__':
    start()
