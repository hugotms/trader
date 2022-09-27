import smtplib

from email.mime import multipart, text

class SMTP:

    def __init__(self, host, port, password, from_addr, alias, to_addrs):
        self.host = host
        self.port = port
        self.password = password
        self.from_addr = from_addr
        self.alias = alias
        self.to_addrs = to_addrs

        if self.alias is None:
            self.alias = self.from_addr
        else:
            self.alias = self.alias + ' <' + self.from_addr + '>'

        if self.to_addrs is None:
            self.to_addrs = self.from_addr

    def send(self, subject, plain, html=None):
        try:
            mail = multipart.MIMEMultipart('alternative')
            mail['From'] = self.alias
            mail['To'] = self.to_addrs
            mail['Subject'] = subject
            mail.attach(text.MIMEText(plain, 'plain'))

            if html is not None:
                mail.attach(text.MIMEText(html, 'html'))

            client = smtplib.SMTP(host=self.host, port=self.port)
            client.starttls()
            client.login(user=self.from_addr, password=self.password)
            client.sendmail(from_addr=self.from_addr, to_addrs=self.to_addrs.split(','), msg=mail.as_string())
            client.quit()
        except Exception:
            print("Failed to send mail")
            return False
        
        return True
