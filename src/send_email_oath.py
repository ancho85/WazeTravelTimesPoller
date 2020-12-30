from __future__ import absolute_import
import base64
import ConfigParser
import os
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httplib2
import oauth2client
from apiclient import errors, discovery
from oauth2client import client, tools, file

import helper
from io import open

config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(helper.get_config_path())

SCOPES = u'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = os.path.join(helper.get_config_folder_path(), ur'client_secret.json')
APPLICATION_NAME = u'Gmail API Python Send Email'
FROM_EMAIL = u'Waze Travel Times <email@email.com>'


def get_email_users():
    targets = []
    for user in unicode(config.get(u"Emails", u"email1")).split(","):
        targets.append(user)

    if not targets:
        return None
    else:
        email_addresses = u','.join(unicode(x) for x in targets)
        return email_addresses


def get_credentials():
    home_dir = os.path.expanduser(u'~')
    credential_dir = os.path.join(home_dir, u'.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, u'gmail-python-email-send.json')
    store = oauth2client.file.Storage(credential_path)

    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print u'Storing credentials to ' + credential_path
    return credentials


def send_message(subject, body, attach=None, type=None):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build(u'gmail', u'v1', http=http, cache_discovery=False)
    message = create_message(subject, body, attach)
    send_message_internal(service, u"me", message)


def send_message_internal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print u'Message Id: %s' % message[u'id']
        return message
    except errors.HttpError, error:
        print u'An error occurred: %s' % error


def create_message(subject, body, attach=None, type=None):
    message = MIMEMultipart()
    message[u'to'] = get_email_users()
    message[u'from'] = FROM_EMAIL
    message[u'subject'] = subject
    mime_body = MIMEText(body.encode('utf-8'), u'html', 'utf-8')

    message.attach(mime_body)

    if attach is not None:
        fp = open(attach)
        msg = MIMEBase(u'application', u'octet-stream')
        msg.set_payload(fp.read())
        encoders.encode_base64(msg)
        filename = os.path.basename(attach)
        msg.add_header(u'Content-Disposition', u'attachment', filename=filename)
        message.attach(msg)

    raw = base64.urlsafe_b64encode(message.as_string()).decode()
    return {u'raw': raw}


if __name__ == u'__main__':
    # test email by running this file
    string = u'<html><head><style>table, th, td {border: 1px solid black;}</style></head><body>'
    string += u'<table width="50%">'
    string += u'<tr><th>RID</th><th>Road</th><th>To/From</th><th>Current Time</th><th>Historic Time</th><th>Since</th></tr>'
    string += u'</table></body></html>'

    error = u'Travel Times'
    subject = u'Alert: TEST (%s) ' % time.time()

    # send_message("Test", string, attach='../logs/waze_errors.log')
    send_message(u"Congestion Summary", string)
