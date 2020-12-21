#!/usr/bin/python2.7
from __future__ import with_statement
from __future__ import absolute_import
import ConfigParser
import json
import logging
import logging.config

import db_conn
import download_data
import helper
import persistence
import route_errors
import send_email
import deleted_routes
from io import open

# use config file, not database
config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(helper.get_config_path())

CONGESTED_PERCENT = config.getint(u'Settings', u'CongestionPercent')
CONGESTION_EMAIL = False

# add logging
with open(helper.get_log_config_path(), u"r", encoding=u"utf-8") as f:
    x = json.load(f)
    log_filename = helper.get_logging_filename()[0]
    log_error_filename = helper.get_logging_filename()[1]
    x[u'handlers'][u'file'][u'filename'] = log_filename
    x[u'handlers'][u'file_error'][u'filename'] = log_error_filename

logging.config.dictConfig(x)

logging.debug(u"<-------- Start -------->")

logging.debug(u"Config path: %s" % helper.get_config_path())
logging.debug(u"Log config path: %s" % helper.get_log_config_path())
logging.debug(u"Persistence path: %s" % helper.get_persistence_path())

# SQL
sql_routes_check = u"""SELECT route_id, feed_id, feed_name, deleted FROM routes WHERE route_id = ?"""
sql_routes_insert = u"""INSERT INTO routes VALUES (?,?,?,?,?,?,?,?,?)"""
sql_route_update = u"""UPDATE routes SET feed_id = ?, feed_name = ? WHERE route_id = ?"""
sql_delete_update = u"""UPDATE routes SET deleted = ? WHERE route_id = ?"""

sql_write_tt = u"""INSERT INTO travel_times (route_id, current_tt, historical_tt, current_tt_min, historical_tt_min,
                   congested_bool, congested_percent, jam_level, tt_date_time) VALUES (?,?,?,?,?,?,?,?,?)"""

sql_congested_check = u"""SELECT route_id FROM routes_congested WHERE route_id = ?"""
sql_congested_insert = u"""INSERT INTO routes_congested (route_id, congested_date_time,
                        current_tt_min, historical_tt_min) VALUES (?,?,?,?)"""
sql_congested_update = u"""UPDATE routes_congested SET current_tt_min = ?, historical_tt_min = ? WHERE route_id = ?"""
sql_congested_remove = u"""DELETE FROM routes_congested WHERE route_id = ?"""
sql_congested_counter = u"""SELECT route_id FROM routes_congested"""


def write_routes(route_details, db):
    c = db.cursor()
    # insert route data
    try:
        c.execute(helper.sql_format(sql_routes_check), (route_details[0],))
        r = c.fetchone()

        if r is None:
            logging.debug(route_details)
            c.execute(helper.sql_format(sql_routes_insert), route_details)

        else:
            # update deleted column
            if r[3] or r[3] is None:
                c.execute(helper.sql_format(sql_delete_update), (route_details[8], route_details[0]))

            # add feed id and name if they don't exist
            if r[1] is None or r[2] is None:
                logging.debug(u'updating route to include feed id and name')
                route_update = (route_details[6], route_details[7], route_details[0])
                c.execute(helper.sql_format(sql_route_update), route_update)

    except Exception, e:
        logging.exception(e)
        pass


def write_data(travel_time, db):
    c = db.cursor()
    # insert travel time data
    try:
        logging.info(travel_time)
        c.execute(helper.sql_format(sql_write_tt), travel_time)
    except Exception, e:
        logging.exception(e)
        pass


def congestion_table(congested, route_id, congested_date_time, current_tt_min, historical_tt_min, omit, db):
    c = db.cursor()
    c.execute(helper.sql_format(sql_congested_check), (route_id,))
    one = c.fetchone()

    # remove routes in table if omit
    if omit:
        logging.debug(u"Omitting routes from congestion alerting: %s" % route_id)
        if one is not None:
            logging.debug(u"Removing omitted from congestion table: %s" % route_id)
            c.execute(helper.sql_format(sql_congested_remove), (route_id,))
    else:
        if one is None:
            if congested:
                c.execute(helper.sql_format(sql_congested_insert),
                          (route_id, congested_date_time, current_tt_min, historical_tt_min))
        else:
            logging.debug(u'exists in congestion db: %s' % route_id)
            if congested:
                logging.debug(u'continues to be congested: %s' % route_id)
                c.execute(helper.sql_format(sql_congested_update),
                          (current_tt_min, historical_tt_min, route_id))
            else:
                c.execute(helper.sql_format(sql_congested_remove), (route_id,))


def congestion_counter(db):
    c = db.cursor()
    c.execute(helper.sql_format(sql_congested_counter))
    one = c.fetchone()

    if one is None:
        helper.persistence_update(u'congestion_counter', 0, u'equals')
    else:
        helper.persistence_update(u'congestion_counter', 1, u'add')

    json = helper.read_json()
    logging.info(u"congestion_counter = %s" % json[u"congestion_counter"])

    congestion_summary_poll = config.getint(u'Settings', u'CongestionSummaryPoll')
    if json[u'congestion_counter'] >= congestion_summary_poll:
        global CONGESTION_EMAIL
        CONGESTION_EMAIL = True
        helper.persistence_update(u'congestion_counter', 0, u'equals')


def process_data(uid, data, db):
    counter = 0

    tt_date_time = helper.timestamp_to_datetime(data[u'updateTime'])

    # parse out only routes
    routes = data[u'routes']

    # get the feed name
    feed_name = data[u'name']

    # get current route errors
    err_list = route_errors.get_route_errors()

    # run through the routes for data
    for route in routes:
        counter += 1
        route_id = route[u'id']
        route_name = route[u'name']
        route_from = route[u'fromName']
        route_to = route[u'toName']
        route_type = route[u'type']
        length = route[u'length']

        current_tt = route[u'time']
        historical_tt = route[u'historicTime']
        jam_level = route[u'jamLevel']

        route_list.append(route_id)

        if current_tt == -1:
            logging.warning(u"Route %s is showing -1, skipping for now" % route_id)
            route_errors.set_route_errors(route_id, route_name, add=True)
            continue # move to next route, do not archive
        elif route_id in err_list:
            route_errors.set_route_errors(route_id, route_name, add=False)

        omit = False
        if route_id in omit_routes or uid in omit_feeds:
            omit = True

        current_tt_min = helper.time_to_minutes(current_tt)
        historical_tt_min = helper.time_to_minutes(historical_tt)

        congested_bool = helper.check_congestion(current_tt, historical_tt, CONGESTED_PERCENT)
        congestion_table(congested_bool, route_id, tt_date_time, current_tt_min, historical_tt_min, omit, db)

        route_details = (route_id, route_name, route_from, route_to, route_type, length, uid, feed_name, False)

        travel_time = (route_id, current_tt, historical_tt, current_tt_min, historical_tt_min,
                       congested_bool, CONGESTED_PERCENT, jam_level, tt_date_time)

        # write data
        try:
            write_routes(route_details, db)
            write_data(travel_time, db)
        except Exception, e:
            logging.exception(e)

    logging.info(u"Route counter: %i" % counter)


def run(url, uid, db):
    # get data from website
    data = download_data.get_data_from_website(url)
    timestamp = int(data[u'updateTime'])
    tt_date_time = helper.timestamp_to_datetime(timestamp)

    logging.info(u"Waze feed Epoch Time: %s" % timestamp)
    logging.info(u'Waze feed Date/Time : %s' % tt_date_time)

    # check to make sure data is good before proceeding
    try:
        helper.check_for_data_integrity(data)
        logging.debug(u'data pass integrity check')
    except Exception, e:
        logging.exception(e)
        raise

    # check for existing pull #
    persistence.check_update_time(uid, timestamp)

    # run main
    process_data(uid, data, db)


if __name__ == u'__main__':

    logging.info(u'Congested percent: %s' % unicode(CONGESTED_PERCENT))

    waze_url_uids = str(config.get(u"WazeUIDS", u"uid1")).split(",")
    waze_url_prefix = config.get(u'Settings', u'WazeURLPrefix')

    omit_routes = helper.get_omit_routes_list()
    logging.info(u"Omit these routes from congestion alerting: %s" % unicode(omit_routes))

    omit_feeds = helper.get_omit_feed_list()
    logging.info(u"Omit these feeds from congestion alerting: %s" % unicode(omit_feeds))

    route_list = []

    with db_conn.DatabaseConnection() as db:
        for uid in waze_url_uids:
            uid = unicode(uid)
            full_url = u"%s%s" % (waze_url_prefix, uid)
            logging.info(u'Waze URL: %s' % full_url)

            try:
                persistence.check_persistence_for_buids(uid)
                run(full_url, uid, db)
            except Exception, e:
                logging.exception(e)
                continue

        # run congestion counter check after processing the data
        congestion_counter(db)

        # run route error counter check after processing the data
        route_errors.route_error_counter()

        try:
            # check for deleted routes
            # deleted_routes.set_route_list(route_list)
            del_routes = deleted_routes.DeletedRoutes(db, route_list)
            del_routes.run()

            # remove deleted routes from persistence
            route_errors.remove_deleted_routes(del_routes.get_deleted_routes())
        except Exception, e:
            logging.exception(e)

        # commit all changes
        db.commit()

        # send email
        bool_email = config.getboolean(u'EmailSettings', u'SendEmailAlerts')
        if send_email.get_email_users() is None:
            bool_email = False

        if bool_email is False:
            logging.info(u'Not sending emails')
        else:
            if CONGESTION_EMAIL:
                try:
                    send_email.build_email(db)
                except Exception, e:
                    logging.error(e)

    logging.debug(u"<-------- End -------->")
