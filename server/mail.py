import os
import smtplib

from email.mime import multipart, text

class SMTP:

    def new(self):
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = os.getenv('SMTP_PORT')
        self.smtp_from = os.getenv('SMTP_FROM')
        self.smtp_as = os.getenv('SMTP_AS')
        self.smtp_key = os.getenv('SMTP_KEY')
        self.smtp_to = os.getenv('SMTP_TO')

        if (self.smtp_host is None 
            or self.smtp_port is None
            or self.smtp_from is None 
            or self.smtp_key is None):

            print("Required SMTP variables not set")
            return None
        
        self.smtp_port = int(self.smtp_port)

        if self.smtp_as is None:
            self.smtp_as = self.smtp_from
        else:
            self.smtp_as = self.smtp_as + ' <' + self.smtp_from + '>'

        if self.smtp_to is None:
            self.smtp_to = self.smtp_from
        
        return self

    def send(self, subject, message):
        try:
            mail = multipart.MIMEMultipart()
            mail['From'] = self.smtp_as
            mail['To'] = self.smtp_to
            mail['Subject'] = subject
            mail.attach(text.MIMEText(message))

            client = smtplib.SMTP(host=self.smtp_host, port=self.smtp_port)
            client.starttls()
            client.login(user=self.smtp_from, password=self.smtp_key)
            client.sendmail(from_addr=self.smtp_from, to_addrs=self.smtp_to.split(','), msg=mail.as_string())
            client.quit()
        except Exception:
            print("Failed to send mail")
            return False
        
        return True
