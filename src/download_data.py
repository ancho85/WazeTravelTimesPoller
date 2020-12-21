from __future__ import absolute_import
import ConfigParser
import json
import logging
import urllib2, urllib

import helper

config = ConfigParser.ConfigParser(allow_no_value=True)
config.read(helper.get_config_path())


def get_data_from_website(url):
    logging.info(u'try get info from website')
    try:
        response = urllib2.urlopen(url, timeout=5).read().decode(u'utf-8')
        j = json.loads(response)
        return j

    except Exception, e:
        logging.exception(e)
        raise


if __name__ == u'__main__':
    pass
