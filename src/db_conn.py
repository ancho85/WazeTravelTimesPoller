from __future__ import absolute_import
import logging
import ConfigParser
import sqlite3
import os

import helper

config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(helper.get_config_path())

USE_POSTGRES = config.getboolean(u'Postgres', u'use_postgres')
if USE_POSTGRES:
    import psycopg2


class DatabaseConnection(object):
    def __init__(self):
        self.dbconn = None

    def __enter__(self):
        if USE_POSTGRES:
            db_string = using_postgres()
            self.dbconn = psycopg2.connect(**db_string)
        else:
            db_string = using_sqlite()
            self.dbconn = sqlite3.connect(db_string)
        logging.debug(u'Database open')
        return self.dbconn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dbconn.close()
        logging.debug(u'Database closed')


def using_postgres():
    host = unicode(config.get(u'Postgres', u'host'))
    database = unicode(config.get(u'Postgres', u'database'))
    user = unicode(config.get(u'Postgres', u'user'))
    password = unicode(config.get(u'Postgres', u'password'))
    database_string = {u'host': host, u'database': database, u'user': user, u'password': password}
    return database_string


def using_sqlite():
    return os.path.join(helper.get_db_path(), config.get(u'Settings', u'DatabaseURL'))