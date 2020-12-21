from __future__ import with_statement
from __future__ import absolute_import
import ConfigParser
import json
import logging

import helper
import send_email
from io import open
import io

config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(helper.get_config_path())

send_oath = config.getboolean(u"EmailSettings", u"SendWithOath")
if send_oath:
    import send_email_oath


def check_persistence_for_buids(buid):
    exists = False
    persistence_json = helper.read_json()
    for uid in persistence_json[u'buids']:
        if uid[u'buid'] == buid:
            exists = True

    if not exists:
        persistence_json[u'buids'].append({
            u"buid": buid,
            u"counter": 0,
            u"last_update": 0
        })

        #with open(helper.get_persistence_path(), 'w') as f:
        #    json.dump(persistence_json, f, indent=2)
        with io.open(helper.get_persistence_path(), 'w',encoding="utf-8") as f:
          f.write(unicode(json.dumps(persistence_json, ensure_ascii=False)))


def check_update_time(uid, timestamp):
    read_json = helper.read_json()

    for buid in read_json[u"buids"]:
        if buid[u"buid"] == uid:
            json_counter = buid[u"counter"]
            json_last_update = buid[u"last_update"]
            time_counter = int(json_counter)
            poll_interval = config.getint(u'Settings', u'FeedError')

            if json_last_update == timestamp:
                # feed has not updated
                if time_counter != 0 and (time_counter % poll_interval) == 0:
                    text = u"It has been %s polls since the last Waze feed update to %s" % (unicode(time_counter), unicode(uid))
                    logging.error(text)

                    try:
                        subject = u'Feed Error'
                        attachment = u'../logs/waze_errors.log'

                        if send_oath:
                            logging.info(u'Sending with oauth email')
                            send_email_oath.send_message(subject, text, attach=attachment)
                        else:
                            logging.info(u'Sending with regular email')
                            send_email.run(subject, text, attach=attachment)

                    except Exception, e:
                        logging.exception(e)

                buid[u"counter"] += 1
                #with open(helper.get_persistence_path(), u'w') as f:
                #    json.dump(read_json, f, indent=2)
                with io.open(helper.get_persistence_path(), 'w',encoding="utf-8") as f:
                  f.write(unicode(json.dumps(read_json, ensure_ascii=False)))

                raise Exception(u"Data already exists in database")
            else:
                # feed has updated
                time_since_update = timestamp - json_last_update
                logging.debug(u"Time since last update %s" % unicode(time_since_update))
                buid[u"counter"] = 0
                buid[u"last_update"] = timestamp
                # with open(helper.get_persistence_path(), u'w') as f:
                #     json.dump(read_json, f, indent=2)
                with io.open(helper.get_persistence_path(), 'w',encoding="utf-8") as f:
                  f.write(unicode(json.dumps(read_json, ensure_ascii=False)))


if __name__ == u'__main__':
    pass
