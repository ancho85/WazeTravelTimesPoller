from __future__ import absolute_import
import ConfigParser
import logging
import os
import smtplib
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import helper
from io import open

config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(helper.get_config_path())

send_oath = config.getboolean(u"EmailSettings", u"SendWithOath")
if send_oath:
    import send_email_oath

EMAIL_USER = config.get(u"EmailSettings", u"Username")
EMAIL_PWD = config.get(u"EmailSettings", u"Password")


def get_email_users():
    targets = []
    for user in unicode(config.get(u"Emails", u"email1")).split(","):
        targets.append(user)

    if not targets:
        return None
    else:
        email_addresses = u','.join(unicode(x) for x in targets)
        return email_addresses


def build_email(db):
    string = u'<html><head><style>table, th, td {border: 1px solid black;}</style></head><body>'
    string += u'<table width="100%">'
    string += u'<tr><th>RID</th><th>Road</th><th>To/From</th><th>Current Time</th><th>Historic Time</th><th>Since</th></tr>'

    c = db.cursor()
    c.execute(u'''SELECT routes_congested.route_id, current_tt_min, historical_tt_min,
                    route_name, route_from, route_to, congested_date_time
                    FROM routes_congested
                    INNER JOIN routes ON routes_congested.route_id=routes.route_id''')
    all = c.fetchall()

    for each in all:
        rid = each[0]
        c_min = each[1]
        h_min = each[2]
        route_name = each[3]
        route_from = each[4]
        route_to = each[5]
        ddate = each[6]

        string += u'<tr>'
        string += u'<td>%s</td>' % unicode(rid)
        string += u'<td>%s</td>' % unicode(route_name)
        string += u'<td>%s to %s</td>' % (unicode(route_from), unicode(route_to))
        string += u'<td>%s</td>' % unicode(c_min)
        string += u'<td>%s</td>' % unicode(h_min)
        string += u'<td>%s</td>' % unicode(ddate)
        string += u'</tr>'

    string += u"</table>"
    string += u'</body></html>'

    try:
        subject = u'Congestion Summary'

        if send_oath:
            logging.info(u'Sending with oauth email')
            send_email_oath.send_message(subject, string)
        else:
            logging.info(u'Sending with regular email')
            run(u'Congestion Summary', string, attach=None, type=u'html')

    except Exception, e:
        logging.exception(e)


def run(subject, body, attach=None, type=None):
    if EMAIL_USER == u'' or EMAIL_PWD == u'':
        raise Exception(u"You are missing email username or password")

    logging.info(u'Attempting to send email')

    smtp_ssl_host = u'smtp.gmail.com'
    smtp_ssl_port = 465
    sender = u'Waze Travel Times'
    targets = get_email_users()

    msg = MIMEMultipart()

    msg[u'Subject'] = subject
    msg[u'From'] = sender
    msg[u'To'] = get_email_users()

    if type == u'html':
        msg.attach(MIMEText(body, u'html'))
    else:
        msg.attach(MIMEText(body, u'plain'))

    if attach is not None:
        attachment = open(attach, u"rb")

        part = MIMEBase(u'application', u'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(u'Content-Disposition', u'attachment', filename=os.path.basename(attach))

        msg.attach(part)

    server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
    server.login(EMAIL_USER, EMAIL_PWD)
    server.sendmail(sender, targets, msg.as_string())
    server.quit()
    logging.info(u'Email sent')


if __name__ == u'__main__':
    # test email by running this file
    string = u'<html><head><style>table, th, td {border: 1px solid black;}</style></head><body>'
    string += u'<table width="50%">'
    string += u'<tr><th>RID</th><th>Road</th><th>To/From</th><th>Current Time</th><th>Historic Time</th><th>Since</th></tr>'
    string += u'</table></body></html>'

    error = u'Travel Times'
    subject = u'Alert: TEST (%s) ' % time.time()
    run(subject, string, attach=None, type=u'html')
