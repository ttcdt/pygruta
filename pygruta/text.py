#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   text generator

import pygruta

def get_handler(gruta, q_path, q_vars):
    """ GET handler for .txt files """

    status, body = 0, None

    if q_path == "/admin/status.txt":
        status = 202
        body   = ""

        body += "version: %s\n" % pygruta.__version__
        body += "id: %s\n" % gruta.id()
        body += "html-cache-entries: %d\n" % len(gruta.html_cache.data)
        body += "page-cache-entries: %d\n" % len(gruta.page_cache.data)

    elif q_path == "/robots.txt":
        status = 200
        body   = gruta.template("robots_txt")


    return status, body, "text/plain; charset=utf-8"
