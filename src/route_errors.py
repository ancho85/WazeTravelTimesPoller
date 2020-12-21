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

route_errors_json = helper.get_route_errors_path()


def get_route_errors():
    err_json = helper.read_json(route_errors_json)
    err_route = err_json[u'routes']
    err_list = []
    for err in err_route:
        err_list.append(err[u'route_id'])

    return err_list


def set_route_errors(route_id, route_name, add):
    err_json = helper.read_json(route_errors_json)
    err_dict = dict()

    err_list = get_route_errors()

    if add:
        if route_id not in err_list:
            err_dict[u'route_id'] = route_id
            err_dict[u'route_name'] = route_name
            err_json[u'routes'].append(err_dict)
    else:
        if route_id in err_list:
            for d in err_json[u'routes']:
                if d[u'route_id'] == route_id:
                    err_json[u'routes'].remove(d)


            # err_json['routes'].remove(route_id)

    #with open(route_errors_json, u'w') as f:
    #    json.dump(err_json, f, indent=2)
    with io.open(route_errors_json, 'w',encoding="utf-8") as f:
      f.write(unicode(json.dumps(err_json, ensure_ascii=False)))


def route_error_counter():
    err_json = helper.read_json(route_errors_json)

    route_count = len(err_json[u'routes'])
    if route_count == 0:
        err_json[u'counter'] = 0
    else:
        err_json[u'counter'] += 1

    if err_json[u'counter'] == 15:
        err_json[u'counter'] = 0
        alert_bad_routes(json.dumps(err_json))

    #with open(route_errors_json, u'w') as f:
    #    json.dump(err_json, f, indent=2)
    with io.open(route_errors_json, 'w',encoding="utf-8") as f:
      f.write(unicode(json.dumps(err_json, ensure_ascii=False)))


def alert_bad_routes(text):
    try:
        subject = u'Routes Error'

        if send_oath:
            logging.info(u'Sending with oauth email')
            send_email_oath.send_message(subject, text, attach=None)
        else:
            logging.info(u'Sending with regular email')
            send_email.run(subject, text, attach=None)

    except Exception, e:
        logging.exception(e)


def remove_deleted_routes(routes):
    update = False
    err_json = helper.read_json(route_errors_json)

    for err in err_json[u'routes']:
        if err[u'route_id'] in routes:
            update = True
            logging.info(u"Removing route %s from route errors persistence" % unicode(err[u'route_id']))
            err_json[u'routes'].remove(err)

    if update:
        #with open(route_errors_json, u'w') as f:
        #    json.dump(err_json, f, indent=2)
        with io.open(route_errors_json, 'w',encoding="utf-8") as f:
          f.write(unicode(json.dumps(err_json, ensure_ascii=False)))


if __name__ == u'__main__':
    pass