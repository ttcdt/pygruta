#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   HTTP services

import pygruta
import urllib3

# PoolManager
pm = urllib3.PoolManager(retries=urllib3.Retry(total=0, connect=0))

def request(method, url, headers={}, fields=None, body=None):
    """ Does an HTTP request """

    # add the User Agent
    headers["User-Agent"] = "pygruta %s" % pygruta.__version__

    status, data = 500, None

    try:
        # why this?
        # request() barfs if both fields and body are set,
        # even if they are set to None (WTF?)
        if fields is not None:
            rq = pygruta.http.pm.request(method, url,
                headers=headers, fields=fields)
        else:
            rq = pygruta.http.pm.request(method, url,
                headers=headers, body=body)

        status, data = rq.status, rq.data
    except:
        pass

    return status, data
