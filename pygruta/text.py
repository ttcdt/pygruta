#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   text generator

import re
import pygruta

def get_handler(gruta, q_path, q_vars):
    """ GET handler for .txt files """

    status, body, ctype = 0, None, "text/plain; charset=utf-8"

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

    elif q_path == "/twtxt.txt":
        status = 200
        body   = twtxt(gruta, gruta.feed())

    elif q_path == "/style.css":
        status = 200
        body   = gruta.template("css_compact")
        ctype  = "text/css"

    return status, body, ctype


def twtxt(gruta, story_set):
    """ twtxt.txt feed """

    page = "#\n# nick: %s\n# site: %s - %s\n# url : %s\n#\n" % (
        gruta.template("cfg_main_user"),
        gruta.template("cfg_site_name"),
        gruta.template("cfg_slogan"),
        gruta.aurl()
    )

    for s in reversed(list(story_set)):
        story = gruta.story(s[0], s[1])
        date  = gruta.date_format(story.get("date"), "%FT%TZ")

        page += "%s\t%s (%s)\n" % (
            date, story.get("title"), gruta.aurl(story)
        )

    return page


def to_html(content):
    """ converts to HTML """

    # pick title from first line
    title = content.split("\n")[0]
    title = title.replace("\n", "")

    # fix problematic chars
    content = re.sub("&", "&amp;", content)
    content = re.sub("<", "&lt;", content)
    content = re.sub(">", "&gt;", content)

    # wrap body as preformatted
    body = "<pre>\n" + content + "</pre>\n"
    abstract = body

    return title, abstract, body
