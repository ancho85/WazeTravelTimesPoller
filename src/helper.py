from __future__ import with_statement
from __future__ import division
from __future__ import absolute_import
import io
import json
import ConfigParser
import logging
import os
import sys
from datetime import datetime
from io import open

config_file = u'config.ini'


def is_frozen():
    # determine if application is a script file or frozen exe
    if getattr(sys, u'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.abspath(u'..')

    return application_path


def get_config_path():
    return os.path.join(is_frozen(), u'configs' + os.sep + config_file)


def get_config_folder_path():
    return os.path.join(is_frozen(), u'configs')


def get_log_config_path():
    return os.path.join(is_frozen(), u'configs' + os.sep + u'log_config.json')


def get_persistence_path():
    return os.path.join(is_frozen(), u'persistence' + os.sep + u'persistence.json')


def get_route_errors_path():
    return os.path.join(is_frozen(), u'persistence' + os.sep + u'route_errors.json')


def get_db_path():
    return os.path.join(is_frozen(), u'database')


def get_logging_filename():
    log_filename = os.path.join(is_frozen(), u'logs' + os.sep + u'waze.log')
    log_error_filename = os.path.join(is_frozen(), u'logs' + os.sep + u'waze_errors.log')
    return log_filename, log_error_filename


def timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp/1000.0).strftime(u"%Y-%m-%d %H:%M:%S.%f")[:-3]


def time_to_minutes(time_now):
    return round((time_now / 60), 3)


def check_for_data_integrity(data):
    if any([data[u'updateTime'] == 0, data[u'updateTime'] == u'']):
        raise Exception(u'Data did not pass the integrity check, cannot proceed')


def get_omit_routes_list():
    omit_list = []
    omit_routes = []  # config[u'OmitRoutes']
    for x in omit_routes:
        omit_list.append(int(x))

    return omit_list

def get_omit_feed_list():
    omit_list = []
    omit_routes = []  # config[u'OmitUids']
    for x in omit_routes:
        omit_list.append(x)

    return omit_list


def check_congestion(time_now, time_historic, congested_percent):
    congestion_threshold = time_historic * (int(congested_percent) / 100)
    logging.debug(u'time_now: %s, time_historic: %s' % (str(time_now), str(time_historic)))
    logging.debug(u'congestion_threshold %s' % str(congestion_threshold))

    if time_now > congestion_threshold:
        congested = True
    else:
        congested = False

    return congested


def read_json(file=None):
    if file is None:
        with open(get_persistence_path(), 'r') as f:
            json_file = json.load(f)
    else:
        with open(file, 'r') as f:
            json_file = json.load(f)

    return json_file


def counter_reset():
    # reset json counter
    logging.debug(u'Reset json counter')
    persistence_update(u'counter', 0, u'equals')


def persistence_update(key, value, operator):
    json_file = read_json()

    if operator == u'add':
        json_file[key] += value
    elif operator == u'equals':
        json_file[key] = value

    #with open(get_persistence_path(), u'w') as f:
    #    json.dump(json_file, f, indent=2)
    with io.open(get_persistence_path(), 'w',encoding="utf-8") as f:
      f.write(unicode(json.dumps(json_file, ensure_ascii=False)))

    return json_file


config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(get_config_path())


def sql_format(sql):
    use_postgres = config.getboolean(u'Postgres', u'use_postgres')
    if use_postgres:
        sql = sql.replace(u"?", u"%s")
        sql = sql.replace(u"0", u"false")
        sql = sql.replace(u"1", u"true")

    return sql


if __name__ == u'__main__':
    pass
