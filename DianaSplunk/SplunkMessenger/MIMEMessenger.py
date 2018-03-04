from SplunkXML2PDF import splunk_xml2pdf
import logging

fn = "cirr_dose.xml"

logging.basicConfig(level=logging.DEBUG)

tokens = {'field1.earliest': '-7d',
          'field1.latest': 'now'}

# splunk_xml2pdf(fn, splunkhost, splunkuser, splunkpword, tokens)

# Import smtplib for the actual sending function
import smtplib

# For guessing MIME type
import mimetypes

# Import the email modules we'll need
import email
import email.mime.application

# Create a text/plain message
msg = email.mime.Multipart.MIMEMultipart()
msg['Subject'] = 'CIRR Weekly Dose Report'
msg['From'] = send_as
msg['To'] = ','.join(to)

# The main body is just another attachment
body = email.mime.Text.MIMEText("""Automatically generated PDF report attached""")
msg.attach(body)

# PDF attachment
filename='cirr_dose.pdf'
fp=open(filename,'rb')
att = email.mime.application.MIMEApplication(fp.read(),_subtype="pdf")
fp.close()
att.add_header('Content-Disposition','attachment',filename=filename)
msg.attach(att)

# send via Gmail server
s = smtplib.SMTP(mailhost, port)
s.ehlo()
s.starttls()
s.login(sender,pword)
s.sendmail(sender, to, msg.as_string())
s.quit()