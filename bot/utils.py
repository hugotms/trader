import datetime

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from lastversion import has_update

from data import assets
from data import reports

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

        response = response = parameters.database.getPastPerformance(report, parameters)
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

def report(parameters):
    report_data = getHistory(parameters)
    
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
