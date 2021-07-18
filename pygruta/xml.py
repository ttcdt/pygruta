#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   XML generator

import pygruta
import re

def sitemap(gruta):
    """ Google-style sitemap """

    page = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    page += "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    page += "<url><loc>%s</loc></url>\n" % gruta.aurl()

    for s in gruta.story_set():
        page += "<url><loc>%s</loc></url>\n" % gruta.aurl(s[0] + "/" + s[1] + ".html")

    for t in gruta.topics():
        page += "<url><loc>%s</loc></url>\n" % gruta.aurl(t + "/")

    page += "</urlset>\n"

    return page


def atom(gruta, story_set, subtitle=None, rel=None, with_content=True):
    """ ATOM feed """

    if subtitle is None:
        subtitle = gruta.template("cfg_slogan")

    if rel is None:
        rel = gruta.aurl("atom.xml")
    else:
        rel = gruta.aurl(rel)

    page = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    page += "<feed xmlns=\"http://www.w3.org/2005/Atom\">\n"
    page += "<title>%s</title>\n" % gruta.template("cfg_site_name")
    page += "<subtitle>%s</subtitle>\n" % subtitle
    page += "<link href=\"%s\"/>\n" % gruta.aurl()
    page += "<link rel=\"self\" type=\"application/atom+xml\" href=\"%s\"/>\n" % rel
    page += "<id>%s</id>\n" % gruta.aurl()

    feed_datetime = False

    for s in story_set:
        story    = gruta.story(s[0], s[1])
        user     = gruta.user(story.get("userid") or gruta.template("cfg_main_user"))
        datetime = gruta.date_to_datetime(story.get("date"))
        abstract = pygruta.special_uris(gruta, story.get("abstract"), absolute=True)

        if not feed_datetime:
            feed_datetime = True
            page += "<updated>%s</updated>\n" % datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

        page += "<entry>\n"
        page += "<title>%s</title>\n" % story.get("title")
        page += "<link href=\"%s\"/>\n" % gruta.aurl(story)
        page += "<id>%s</id>\n" % gruta.aurl(story)
        page += "<updated>%s</updated>\n" % datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        page += "<author>\n"
        page += "<name>%s</name>\n" % user.get("username")
        page += "<email>%s</email>\n" % user.get("email")
        page += "</author>\n"

        # categories

        # only generate a topic category if there is more than one topic
        if len(list(gruta.topics())) > 1:
            page += "<category term=\"%s\"/>\n" % s[0]

        for t in story.get("tags"):
            page += "<category term=\"%s\"/>\n" % t

        if with_content:
            page += "<content type=\"html\" xml:lang=\"%s\">" % story.get("lang")

            # escape html
            abstract_esc = re.sub("&", "&amp;", abstract)
            abstract_esc = re.sub("<", "&lt;", abstract_esc)
            abstract_esc = re.sub(">", "&gt;", abstract_esc)
            page += abstract_esc

            page += "</content>\n"

        page += "</entry>\n"

    page += "</feed>\n"

    return page


def rss(gruta, story_set, title=None, rel=None):
    """ RSS 2.0 feed """

    if title is None:
        title = gruta.template("cfg_slogan")

    if rel is None:
        rel = gruta.aurl("rss.xml")
    else:
        rel = gruta.aurl(rel)

    page = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    page += "<rss xmlns:content=\"http://purl.org/rss/1.0/modules/content/\" version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\">\n"
    page += "<channel>\n<title>%s: %s</title>\n" % (
        gruta.template("cfg_site_name"), title)
    page += "<link>%s</link>\n" % gruta.aurl()
    page += "<description></description>\n"
    page += "<atom:link href=\"%s\" rel=\"self\" type=\"application/rss+xml\"/>\n" % rel

    feed_datetime = False

    for s in story_set:
        story    = gruta.story(s[0], s[1])
        user     = gruta.user(story.get("userid") or gruta.template("cfg_main_user"))
        datetime = gruta.date_to_datetime(story.get("date"))
        abstract = pygruta.special_uris(gruta, story.get("abstract"), absolute=True)

        if not feed_datetime:
            feed_datetime = True
            page += "<pubDate>%s</pubDate>\n" % datetime.strftime("%a, %d %b %Y %T +0200")

        page += "<item>\n"
        page += "<title>%s</title>\n" % story.get("title")
        page += "<link>%s</link>\n" % gruta.aurl(story)
        page += "<guid>%s</guid>\n" % gruta.aurl(story)
        page += "<pubDate>%s</pubDate>\n" % datetime.strftime("%a, %d %b %Y %T +0200")
        page += "<author>%s (%s)</author>\n" % (user.get("email"), user.get("username"))

        # only generate a topic category if there is more than one topic
        if len(list(gruta.topics())) > 1:
            page += "<category domain=\"topic\">%s</category>\n" % s[0]

        for t in story.get("tags"):
            page += "<category domain=\"tags\">%s</category>\n" % t

        page += "<description>\n"
        page += "<![CDATA[\n"
        page += abstract
        page += "\n]]>\n"
        page += "</description>\n"
        page += "</item>\n"

    page += "</channel>\n"
    page += "</rss>\n"

    return page


def get_handler(gruta, q_path, q_vars):
    """ GET handler for XML files """

    status, body = 0, None

    if q_path == "/sitemap.xml":
        status = 200
        body   = sitemap(gruta)

    elif q_path == "/atom.xml":
        status = 200
        body   = atom(gruta, gruta.feed())

    elif q_path == "/rss.xml":
        status = 200
        body   = rss(gruta, gruta.feed())

    elif re.search("^/[^/]+/atom\.xml$", q_path):
        # an ATOM feed for a topic
        topic_id = q_path.split("/")[1]
        topic = gruta.topic(topic_id)

        if topic is not None:
            num    = int(gruta.template("cfg_index_num"))
            status = 200
            body   = atom(gruta, gruta.story_set(topics=[topic_id], num=num),
                        subtitle=topic.get("description") or topic.get("name"),
                        rel="%s/atom.xml" % topic_id)
        else:
            status = 404

    elif re.search("^/tag/[^/]+\.xml$", q_path):
        # an ATOM feed for a tag
        tag    = q_path.replace("/tag/", "").replace(".xml", "")
        num    = int(gruta.template("cfg_rss_num"))
        status = 200
        body   = atom(gruta, gruta.story_set(tags=[tag], num=num),
                    subtitle=tag, rel="tag/%s.xml" % tag)

    return status, body, "text/xml; charset=utf-8"
